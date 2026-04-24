"""
Solution Agent — the planner + orchestrator.

Flow for a single fault event:
  1. Route KB by code prefix:  01→engines.json, 02→pumps.json, 03→pipelines.json
  2. Load ONLY the matching entry into the SLM context (~800 tokens, not 12k)
  3. Deterministically extract: part_code, required_tools, quick_fix, steps
  4. Call Llama-3.2-1B for natural-language outputs only:
       - narrative:    2-3 sentence technician brief
       - spoken_alert: 1 short sentence for the PA
  5. Fan out to downstream agents:
       Parts → Tools → Technician → Alert
  6. Return the full bundle (plus logs every call under the current incident)
"""
from __future__ import annotations

import json
import re

from django.conf import settings

from agents.black_box import black_box


# ---------------------------------------------------------------------------
# KB cache (all 3 files, keyed by code — still only the matching entry
# goes into the SLM prompt)
# ---------------------------------------------------------------------------

_KB_BY_CODE: dict[str, dict] | None = None


def _warmup_kb() -> None:
    global _KB_BY_CODE
    if _KB_BY_CODE is not None:
        return
    cache: dict[str, dict] = {}
    for fname in ('engines.json', 'pumps.json', 'pipelines.json'):
        with open(settings.KB_DIR / fname) as f:
            cache.update(json.load(f))
    _KB_BY_CODE = cache


def _kb_file_for(code: str) -> str:
    """Per user's context-engineering instruction — surface which file the
    code routes to (used for logging + demo visibility)."""
    prefix = code.split('-')[0]
    return {'01': 'engines.json', '02': 'pumps.json', '03': 'pipelines.json'}.get(prefix, 'unknown.json')


def _load_kb_entry(code: str) -> dict:
    _warmup_kb()
    hyph = code.replace('/', '-')
    entry = _KB_BY_CODE.get(hyph)
    if entry is None:
        raise ValueError(f'No KB entry for code={code!r}')
    return entry


# ---------------------------------------------------------------------------
# SLM prompt — strict JSON output, tiny context
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    'You are a maintenance planner for an offshore oil rig. '
    'Output ONLY a single valid JSON object matching this schema:\n'
    '{\n'
    '  "narrative": "<2-3 sentence technician brief describing the fault and repair>",\n'
    '  "spoken_alert": "<1 short sentence suitable for a PA announcement>"\n'
    '}\n'
    'Do not include any text, markdown, or code fences outside the JSON.'
)


def _build_user_prompt(code: str, severity: str, machine_id: str,
                       kb_entry: dict, telemetry: dict) -> str:
    return (
        f'Fault code: {code}\n'
        f'Severity: {severity}\n'
        f'Affected machine: {machine_id}\n'
        f"Telemetry: Pressure={telemetry.get('pressure_psi')}psi "
        f"Temp={telemetry.get('temp_c')}C "
        f"Vibration={telemetry.get('vibration_hz')}Hz\n\n"
        f'Knowledge base entry:\n'
        f"- Fault: {kb_entry.get('fault')}\n"
        f"- Description: {kb_entry.get('description')}\n"
        f"- Quick fix: {kb_entry.get('quick_fix')}\n\n"
        'Produce the JSON now.'
    )


def _extract_json(text: str) -> dict | None:
    """Best-effort JSON parsing — 1B models occasionally wrap in prose."""
    s = text.strip()
    # strip ```json fences
    if s.startswith('```'):
        s = re.sub(r'^```(?:json)?\s*', '', s)
        s = re.sub(r'\s*```$', '', s)
    try:
        return json.loads(s)
    except Exception:
        pass
    # Find the first {...} block greedily
    m = re.search(r'\{.*\}', s, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def _fallback_nl(code: str, severity: str, machine_id: str, kb_entry: dict) -> dict:
    """Deterministic fallback if the SLM can't produce valid JSON."""
    return {
        'narrative': (
            f"{kb_entry.get('fault')} detected on {machine_id}. "
            f"Severity: {severity}. Quick fix: {kb_entry.get('quick_fix')}."
        ),
        'spoken_alert': (
            f"Attention. {severity} fault on {machine_id}. "
            f"Fault code {code.replace('-', ' dash ')}. "
            f"Maintenance response required."
        ),
    }


@black_box(phase='plan')
def call_slm(code: str, severity: str, machine_id: str,
             kb_entry: dict, telemetry: dict) -> dict:
    """Run Llama-3.2-1B to produce narrative + spoken_alert.
    Falls back to a deterministic template if the model output can't be parsed."""
    from llm import loader

    reply = loader.generate(
        [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user',   'content': _build_user_prompt(code, severity, machine_id, kb_entry, telemetry)},
        ],
        max_new_tokens=256,
    )
    parsed = _extract_json(reply)
    if not parsed or 'narrative' not in parsed or 'spoken_alert' not in parsed:
        return {**_fallback_nl(code, severity, machine_id, kb_entry),
                'slm_raw': reply,
                'slm_parsed': False}
    return {'narrative': parsed['narrative'],
            'spoken_alert': parsed['spoken_alert'],
            'slm_raw': reply,
            'slm_parsed': True}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

@black_box(phase='plan')
def solve(code: str, machine_id: str, severity: str,
          telemetry_snapshot: dict) -> dict:
    """
    Full Solution Agent pipeline for one fault event.

    Assumes an incident is already open (Problem Generator does that).
    Calls every downstream agent, returning a complete bundle for the UI.
    """
    from agents import alert as alert_agent
    from agents import broadcast as broadcast_agent
    from agents import parts as parts_agent
    from agents import technician as tech_agent
    from agents import tools as tools_agent

    hyph = code.replace('/', '-')
    kb_file = _kb_file_for(hyph)
    kb_entry = _load_kb_entry(hyph)

    # --- SLM: narrative + spoken_alert only ---
    slm_out = call_slm(hyph, severity, machine_id, kb_entry, telemetry_snapshot)

    # --- Downstream agents ---
    part_info = parts_agent.get_part_for_code(hyph)
    part_available = part_info.get('availability', 'unknown') == 'Yes'

    tools_info = tools_agent.get_tools_for_code(hyph)

    assigned_tech = tech_agent.assign_technician(
        hyph, severity, part_available=part_available,
    )

    alert_info = alert_agent.trigger(
        code=hyph,
        severity=severity,
        spoken_alert=slm_out['spoken_alert'],
        machine_id=machine_id,
        narrative=slm_out['narrative'],
        part=part_info,
        tools=tools_info,
        technician=assigned_tech,
        quick_fix=kb_entry.get('quick_fix'),
    )

    broadcast_info = broadcast_agent.dispatch(
        severity=severity,
        code=hyph,
        machine_id=machine_id,
        summary=slm_out.get('spoken_alert') or kb_entry.get('fault', 'Fault detected'),
    )

    return {
        'code': hyph,
        'machine_id': machine_id,
        'severity': severity,
        'kb': {
            'routed_file': kb_file,
            'fault': kb_entry.get('fault'),
            'description': kb_entry.get('description'),
            'quick_fix': kb_entry.get('quick_fix'),
            'detailed_steps': kb_entry.get('detailed_steps'),
        },
        'slm': slm_out,
        'part': part_info,
        'tools': tools_info,
        'technician': assigned_tech,
        'alert': alert_info,
        'broadcast': broadcast_info,
    }
