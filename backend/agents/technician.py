"""
Technician Agent — picks the right technician for a fault.

Routing rule:
    severity 99 (Catastrophic) -> domain specialist on current shift
    severity 05 (Serious)      -> generalist (specialist if part out of stock)
    severity 07 (Maintenance)  -> generalist on current shift

Domain is derived from the first two digits of the fault code:
    01 -> Engine     02 -> Pump     03 -> Pipeline

Also tags the current Black Box incident with the chosen technician.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, time as dtime

from django.conf import settings

from agents.black_box import black_box, get_current_incident


DOMAIN_BY_PREFIX = {'01': 'Engine', '02': 'Pump', '03': 'Pipeline'}

SEVERITY_SUFFIX_TO_NAME = {
    '07': 'Maintenance',
    '05': 'Serious',
    '99': 'Catastrophic',
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db_path():
    return settings.DATABASES['technicians']['NAME']


def _normalize_code(code: str) -> str:
    return code.replace('/', '-')


def _normalize_severity(severity: str) -> str:
    """Accept '99' / '05' / '07' or 'Catastrophic' / 'Serious' / 'Maintenance'."""
    s = severity.strip()
    if s in SEVERITY_SUFFIX_TO_NAME:
        return SEVERITY_SUFFIX_TO_NAME[s]
    s_title = s.title()
    if s_title in {'Maintenance', 'Serious', 'Catastrophic'}:
        return s_title
    raise ValueError(f'Unknown severity: {severity!r}')


def _current_shift() -> str:
    """Local time against A(06-14), B(14-22), C(22-06)."""
    now = datetime.now().time()
    if dtime(6, 0) <= now < dtime(14, 0):
        return 'A'
    if dtime(14, 0) <= now < dtime(22, 0):
        return 'B'
    return 'C'


def _apply_rule(severity_name: str, part_available: bool, domain: str) -> tuple[str, str]:
    """Returns (role, specialization)."""
    if severity_name == 'Catastrophic':
        return 'Specialist', domain
    if severity_name == 'Serious':
        if not part_available:
            return 'Specialist', domain   # escalate
        return 'Generalist', 'General'
    # Maintenance
    return 'Generalist', 'General'


def _tag_incident(technician_id: str) -> None:
    """If an incident is open, stamp this technician onto it."""
    iid = get_current_incident()
    if not iid:
        return
    from core.models import BlackBoxIncident  # lazy to avoid app-ready issues
    (BlackBoxIncident.objects
     .filter(incident_id=iid, assigned_tech__isnull=True)
     .update(assigned_tech=technician_id))


# ---------------------------------------------------------------------------
# Public agent functions
# ---------------------------------------------------------------------------

@black_box(phase='technician')
def assign_technician(code: str, severity: str, part_available: bool = True) -> dict:
    """
    Pick the best-fit technician for this fault on the current shift.
    Picks the most experienced qualifying technician if multiple match.
    Tags the current incident with the chosen technician_id.
    """
    hyph = _normalize_code(code)
    prefix = hyph.split('-')[0]
    domain = DOMAIN_BY_PREFIX.get(prefix)
    if domain is None:
        raise ValueError(f'Unknown code prefix {prefix!r} in code {code!r}')

    sev_name = _normalize_severity(severity)
    shift = _current_shift()
    role, specialization = _apply_rule(sev_name, part_available, domain)

    with sqlite3.connect(_db_path()) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            'SELECT * FROM technicians '
            'WHERE shift=? AND role=? AND specialization=? AND status="active" '
            'ORDER BY years_experience DESC',
            (shift, role, specialization),
        ).fetchall()

    if not rows:
        raise ValueError(
            f'No active technician matches shift={shift} role={role} '
            f'specialization={specialization}'
        )

    chosen = dict(rows[0])
    chosen['_routing'] = {
        'code': hyph,
        'severity': sev_name,
        'part_available': part_available,
        'current_shift': shift,
        'role_required': role,
        'specialization_required': specialization,
        'candidates_considered': len(rows),
    }

    _tag_incident(chosen['technician_id'])
    return chosen


@black_box(phase='technician')
def list_on_shift(shift: str | None = None) -> list[dict]:
    """All active technicians on a given shift (defaults to current)."""
    shift = shift or _current_shift()
    if shift not in {'A', 'B', 'C'}:
        raise ValueError(f'Invalid shift: {shift!r}')

    with sqlite3.connect(_db_path()) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            'SELECT * FROM technicians WHERE shift=? AND status="active" '
            'ORDER BY role, specialization, years_experience DESC',
            (shift,),
        ).fetchall()
    return [dict(r) for r in rows]


@black_box(phase='technician')
def get_technician(technician_id: str) -> dict:
    with sqlite3.connect(_db_path()) as con:
        con.row_factory = sqlite3.Row
        row = con.execute(
            'SELECT * FROM technicians WHERE technician_id=?',
            (technician_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f'Unknown technician_id={technician_id!r}')
    return dict(row)
