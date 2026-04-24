"""
Problem Generator Agent — reads sensor_data.db telemetry, detects a fault,
opens a Black Box incident, and emits a structured problem event.

On-demand only (no polling loop for demo reliability). Callers pick a
scenario (e.g. "engine_catastrophic_failure") and this agent:
  1. replays the telemetry "slow-burn" narrative for context
  2. finds the first row where Error_Code appears
  3. opens a Black Box incident keyed on (code, machine, severity)
  4. returns the event + telemetry snapshot
"""
from __future__ import annotations

import sqlite3

from django.conf import settings

from agents.black_box import black_box, open_incident


SEVERITY_SUFFIX_TO_NAME = {
    '07': 'Maintenance',
    '05': 'Serious',
    '99': 'Catastrophic',
}

# Prefix -> machine-id prefix in telemetry. Engines=ENG, Pumps=PUM, Pipelines=PL.
MACHINE_PREFIX = {'01': 'ENG', '02': 'PUM', '03': 'PL'}

# Normal-operation envelopes (from the team's telemetry generator script).
# Any row outside these is considered "drifting."
NORMAL_PRESSURE = (100.0, 110.0)
NORMAL_TEMP     = (60.0, 70.0)
NORMAL_VIB      = (22.0, 30.0)


def _db_path():
    return settings.DATABASES['sensor_data']['NAME']


def _severity_from_code(code: str) -> str:
    suffix = code.split('-')[-1] if code else ''
    return SEVERITY_SUFFIX_TO_NAME.get(suffix, 'Unknown')


def _canonical_machine(code: str) -> str | None:
    """01-02-99 -> ENG-02  (derives affected machine from the code structure)."""
    parts = code.split('-')
    if len(parts) < 2:
        return None
    prefix = MACHINE_PREFIX.get(parts[0])
    return f'{prefix}-{parts[1]}' if prefix else None


def _table_to_scenario(table: str) -> str:
    """oil_rig_telemetry_engine_engine_catastrophic_failure -> engine_catastrophic_failure"""
    s = table.replace('oil_rig_telemetry_', '', 1)
    parts = s.split('_')
    if len(parts) >= 2 and parts[0] == parts[1]:
        parts = parts[1:]
    return '_'.join(parts)


def _scenario_to_table(scenario: str) -> str:
    parts = scenario.split('_', 1)
    if len(parts) < 2:
        raise ValueError(f'Invalid scenario {scenario!r}')
    machine = parts[0]
    return f'oil_rig_telemetry_{machine}_{scenario}'


def _resolve_table(scenario: str) -> str:
    """Validate scenario against actual tables (guards against SQL injection)."""
    table = _scenario_to_table(scenario)
    with sqlite3.connect(_db_path()) as con:
        exists = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
    if not exists:
        raise ValueError(f'Unknown scenario {scenario!r} (table {table!r} not found)')
    return table


# ---------------------------------------------------------------------------
# Public agent functions
# ---------------------------------------------------------------------------

@black_box(phase='detect')
def list_scenarios() -> list[dict]:
    """Enumerate all 15 telemetry scenarios with their headline fault code."""
    with sqlite3.connect(_db_path()) as con:
        tables = [
            r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name LIKE 'oil_rig_telemetry_%' ORDER BY name"
            ).fetchall()
        ]

        out: list[dict] = []
        for t in tables:
            row = con.execute(
                f'SELECT Error_Code, Machine_ID FROM "{t}" '
                "WHERE Error_Code IS NOT NULL AND Error_Code != '' LIMIT 1"
            ).fetchone()
            out.append({
                'scenario': _table_to_scenario(t),
                'table': t,
                'code': row[0] if row else None,
                'machine_id': row[1] if row else None,
                'severity': _severity_from_code(row[0]) if row else None,
            })
    return out


@black_box(phase='detect')
def simulate_scenario(scenario: str) -> dict:
    """Replay a telemetry scenario -> detect fault -> open incident -> emit event.

    Returns: {incident_id, scenario, code, machine_id, severity,
              detected_ts, first_drift_ts, telemetry_snapshot}
    """
    table = _resolve_table(scenario)

    with sqlite3.connect(_db_path()) as con:
        con.row_factory = sqlite3.Row
        first_err = con.execute(
            f'SELECT * FROM "{table}" '
            "WHERE Error_Code IS NOT NULL AND Error_Code != '' "
            'ORDER BY Timestamp ASC LIMIT 1'
        ).fetchone()
        if first_err is None:
            raise ValueError(f'Scenario {scenario!r} has no error rows')

        # Last telemetry row for the AFFECTED machine (not whatever the
        # rotation happened to land on) — derived from the code's middle digit.
        affected = _canonical_machine(first_err['Error_Code'])
        last_row = None
        if affected is not None:
            last_row = con.execute(
                f'SELECT * FROM "{table}" WHERE Machine_ID=? ORDER BY Timestamp DESC LIMIT 1',
                (affected,),
            ).fetchone()
        if last_row is None:  # fallback
            last_row = con.execute(
                f'SELECT * FROM "{table}" ORDER BY Timestamp DESC LIMIT 1'
            ).fetchone()

        drift = con.execute(
            f'SELECT * FROM "{table}" WHERE ('
            f'Pressure_PSI < {NORMAL_PRESSURE[0]} OR Pressure_PSI > {NORMAL_PRESSURE[1]} '
            f'OR Temp_C > {NORMAL_TEMP[1]} OR Temp_C < {NORMAL_TEMP[0]} '
            f'OR Vibration_Hz > {NORMAL_VIB[1]} OR Vibration_Hz < {NORMAL_VIB[0]}) '
            'ORDER BY Timestamp ASC LIMIT 1'
        ).fetchone()

    code = first_err['Error_Code']
    machine_id = _canonical_machine(code) or first_err['Machine_ID']
    severity = _severity_from_code(code)
    detected_ts = first_err['Timestamp']
    first_drift_ts = drift['Timestamp'] if drift else None

    incident_id = open_incident(
        code=code,
        machine_id=machine_id,
        severity=severity,
        detected_ts=detected_ts,
        first_drift_ts=first_drift_ts,
    )

    return {
        'incident_id': incident_id,
        'scenario': scenario,
        'code': code,
        'machine_id': machine_id,
        'severity': severity,
        'detected_ts': detected_ts,
        'first_drift_ts': first_drift_ts,
        'telemetry_snapshot': {
            'timestamp':    last_row['Timestamp'],
            'machine_id':   last_row['Machine_ID'],
            'pressure_psi': last_row['Pressure_PSI'],
            'temp_c':       last_row['Temp_C'],
            'vibration_hz': last_row['Vibration_Hz'],
            'error_code':   last_row['Error_Code'],
        },
    }


@black_box(phase='detect')
def recent_telemetry(scenario: str, limit: int = 100) -> list[dict]:
    """Last N telemetry rows for a scenario, ascending by timestamp. Used
    by the dashboard to chart the slow-burn ramp."""
    table = _resolve_table(scenario)
    limit = max(1, min(int(limit), 500))
    with sqlite3.connect(_db_path()) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            f'SELECT * FROM "{table}" ORDER BY Timestamp DESC LIMIT ?',
            (limit,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]
