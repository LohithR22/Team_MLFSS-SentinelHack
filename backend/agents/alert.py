"""
Alert Agent — live voice alert generation + WebSocket push.

Produces ONE artifact per trigger, generated on the spot by offline TTS:
    alert_audio: path to a freshly synthesized audio file for this alert

Does NOT use any pre-rendered mp3s from the /alerts folder — every alert
is generated live by say (macOS) or pyttsx3 (Linux on-rig). This keeps
the pipeline demonstrably live and the audio always reflects the current
SLM-generated spoken_alert text.

No audio is played server-side. The frontend fetches the URL and plays it
in the browser.
"""
from __future__ import annotations

import hashlib
import platform
import re
import subprocess
import time
from pathlib import Path

from django.conf import settings

from agents.black_box import black_box, get_current_incident


_AUDIO_DIR = Path(settings.BASE_DIR) / 'runtime_audio'
_AUDIO_DIR.mkdir(exist_ok=True)


def _normalize_code(code: str) -> str:
    return code.replace('/', '-')


def _tts_ready(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def _synthesize(text: str, code: str) -> Path | None:
    """Generate audio on the spot from `text`. Returns None on failure.

    Primary path: macOS `say` command (sync, reliable).
    Fallback:     pyttsx3 (Linux on-rig via espeak).

    Deterministic sha1 filename from (text + code) — cached per identical input
    so replays stay fast.
    """
    if not text or not text.strip():
        return None

    digest = hashlib.sha1(f'{code}|{text}'.encode()).hexdigest()[:12]
    out_path = _AUDIO_DIR / f'alert_{digest}.aiff'
    if _tts_ready(out_path):
        return out_path  # cached

    # --- macOS primary path ---
    if platform.system() == 'Darwin':
        try:
            subprocess.run(
                ['say', '-o', str(out_path), text],
                check=True, timeout=15, capture_output=True,
            )
            if _tts_ready(out_path):
                return out_path
        except Exception:
            pass

    # --- pyttsx3 fallback (Linux / cross-platform) ---
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 165)
        engine.save_to_file(text, str(out_path))
        engine.runAndWait()
        engine.stop()
        for _ in range(30):
            if _tts_ready(out_path):
                return out_path
            time.sleep(0.1)
    except Exception:
        pass

    return out_path if _tts_ready(out_path) else None


def _build_default_text(code: str, severity: str, machine_id: str | None) -> str:
    """If caller didn't provide a spoken_alert, fall back to a sensible default."""
    machine = machine_id or 'an unknown machine'
    return (
        f'Alert. {severity} fault detected on {machine}. '
        f'Fault code {code.replace("-", " dash ")}. Maintenance response required.'
    )


def _abbreviate_quick_fix(qf: str, max_steps: int = 3) -> str:
    """Shorten 'LOCKOUT -> REMOVE HOUSING -> ... -> TEST PRESSURE' for a PA line."""
    steps = [s.strip() for s in qf.split('->') if s.strip()]
    if not steps:
        return ''
    if len(steps) <= max_steps:
        return ' then '.join(steps).rstrip('.')
    head = ' then '.join(steps[:max_steps])
    return f'{head} plus {len(steps) - max_steps} more'


def _build_structured_alert(
    severity: str,
    machine_id: str | None,
    part: dict | None,
    tools: list | None,
    technician: dict | None,
    quick_fix: str | None,
) -> str:
    """Build the announcement in a deterministic, audit-friendly order:
        1. Severity of failure
        2. Location of failure (which machine)
        3. Technician assignment
        4. Fixing procedure (abbreviated quick fix)
        5. Replacement part details
        6. Tools required
    """
    pieces: list[str] = []

    # 1. Severity + 2. Location of failure
    machine = machine_id or 'an unknown machine'
    sev_phrase = {
        'Catastrophic': 'Catastrophic failure',
        'Serious':      'Serious fault',
        'Maintenance':  'Maintenance required',
    }.get(severity, f'{severity} fault')
    pieces.append(f'{sev_phrase} on {machine}.')

    # 3. Technician
    if technician:
        name = technician.get('name', 'technician')
        role = technician.get('role', '').lower() or 'technician'
        radio = technician.get('radio_channel')
        piece = f'Assigned to {role} {name}'
        if radio:
            piece += f', radio {radio}'
        pieces.append(piece + '.')

    # 4. Fixing procedure (said once here as part of the alert flow)
    if quick_fix:
        abbrev = _abbreviate_quick_fix(quick_fix)
        if abbrev:
            pieces.append(f'Procedure: {abbrev}. Full steps on screen.')

    # 5. Replacement part
    if part:
        avail = part.get('availability')
        pname = part.get('part_name') or part.get('part_code')
        loc = part.get('location') or 'storage'
        if avail == 'Yes':
            pieces.append(f'Replacement part {pname} available at {loc}.')
        elif avail == 'No':
            pieces.append(f'Replacement part {pname} is out of stock; escalation required.')
        else:
            pieces.append(f'Replacement part {pname} at {loc}.')

    # 6. Tools
    if tools:
        found = [t for t in tools if t.get('found_in_room_8')]
        missing = [t for t in tools if not t.get('found_in_room_8')]
        if found:
            names = [t.get('tool_name') for t in found if t.get('tool_name')]
            rooms: set[str] = set()
            for t in found:
                m = re.search(r'Room\s*\d+', t.get('location') or '')
                if m:
                    rooms.add(m.group(0).replace('  ', ' '))
            names_part = ', '.join(names) if names else ''
            rooms_part = (' — ' + ', '.join(sorted(rooms))) if rooms else ''
            if names_part:
                pieces.append(f'Tools needed: {names_part}{rooms_part}.')
        if missing:
            miss_names = ', '.join(t.get('tool_name', '?') for t in missing)
            pieces.append(f'Also procure: {miss_names}.')

    # End-of-alert tail: repeat the procedure 3 more times for emphasis,
    # only after the full alert has played once.
    if quick_fix:
        abbrev = _abbreviate_quick_fix(quick_fix)
        if abbrev:
            tail = f'Procedure: {abbrev}.'
            for _ in range(3):
                pieces.append(tail)

    return ' '.join(pieces)


def _push_to_websocket(payload: dict) -> bool:
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        layer = get_channel_layer()
        if layer is None:
            return False
        async_to_sync(layer.group_send)(
            'alerts',
            {'type': 'alert.event', 'payload': payload},
        )
        return True
    except Exception:
        return False


def _play_on_server(audio_path: Path) -> bool:
    """Fire-and-forget playback through the machine's default audio output.

    macOS: afplay. Linux: aplay (ALSA) with a paplay fallback.
    Non-blocking — spawns the player and returns immediately so we never
    hold up the request thread.
    """
    system = platform.system()
    candidates: list[list[str]] = []
    if system == 'Darwin':
        candidates = [['afplay', str(audio_path)]]
    elif system == 'Linux':
        candidates = [['aplay', '-q', str(audio_path)], ['paplay', str(audio_path)]]
    else:
        return False

    for cmd in candidates:
        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except FileNotFoundError:
            continue
        except Exception:
            return False
    return False


def play_file(filename: str) -> bool:
    """Replay a previously-generated alert audio file by filename (no path)."""
    if '/' in filename or '\\' in filename or filename.startswith('.'):
        return False
    path = _AUDIO_DIR / filename
    if not path.exists():
        return False
    return _play_on_server(path)


@black_box(phase='alert')
def trigger(
    *,
    code: str,
    severity: str,
    spoken_alert: str | None = None,
    machine_id: str | None = None,
    narrative: str | None = None,
    part: dict | None = None,
    tools: list | None = None,
    technician: dict | None = None,
    quick_fix: str | None = None,
    autoplay: bool | None = None,
) -> dict:
    """
    Fire a voice alert for this fault.

    Generates the alert audio on the spot via TTS, pushes to the 'alerts'
    WebSocket group, and returns URLs for the frontend to play back.

    When `part`, `tools`, and/or `technician` are provided, the spoken
    announcement is enriched with part availability + location, tool
    staging rooms, and the assigned technician's name + radio channel.
    The WebSocket payload also carries these as structured fields so the
    frontend can render full detail.
    """
    hyph = _normalize_code(code)
    base_text = spoken_alert or _build_default_text(hyph, severity, machine_id)

    # If we have ANY structured context, build the announcement deterministically
    # in the required order (severity -> location -> tech -> procedure -> part -> tools).
    # Otherwise fall back to the SLM's raw text.
    if part or tools or technician or quick_fix:
        enriched_text = _build_structured_alert(
            severity, machine_id, part, tools, technician, quick_fix,
        )
    else:
        enriched_text = base_text

    audio = _synthesize(enriched_text, hyph)
    audio_url = f'/api/audio/narration/{audio.name}' if audio else None

    # Trim technician payload to the fields the frontend needs (no emergency
    # contact, no nationality — keep the WS payload focused).
    tech_summary = None
    if technician:
        tech_summary = {k: technician.get(k) for k in (
            'technician_id', 'name', 'role', 'specialization',
            'shift', 'shift_hours', 'radio_channel', 'quarters',
            'years_experience',
        )}

    # Server-side playback — fire-and-forget, non-blocking.
    if autoplay is None:
        autoplay = getattr(settings, 'SENTINEL_SERVER_AUTOPLAY', True)
    server_played = False
    if autoplay and audio is not None:
        server_played = _play_on_server(audio)

    payload = {
        'incident_id':    get_current_incident(),
        'code':           hyph,
        'machine_id':     machine_id,
        'severity':       severity,
        'base_spoken_alert': base_text,
        'spoken_alert':   enriched_text,
        'narrative':      narrative,
        'alert_audio_url': audio_url,
        'part':           part,
        'tools':          tools,
        'technician':     tech_summary,
        'quick_fix':      quick_fix,
        'server_played':  server_played,
    }
    pushed = _push_to_websocket(payload)

    return {
        **payload,
        'alert_audio_path': str(audio) if audio else None,
        'ws_pushed': pushed,
    }
