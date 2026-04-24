"""
Broadcast Agent — severity-driven escalation fan-out.

Rule:
    Maintenance    -> assigned technician only (handled upstream; no fan-out)
    Serious        -> + shift supervisor + operations manager
    Catastrophic   -> + safety chief + executives (Regional Dir / COO / CEO)
                      + emergency hotline

Each recipient row carries notify_on (CSV of severities they care about);
we filter on that + current shift so Shift B supervisors don't get paged
at 3 AM during Shift C.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, time as dtime

from django.conf import settings

from agents.black_box import black_box, get_current_incident


TIER_ORDER = ['supervisor', 'operations', 'safety', 'executive', 'emergency']


def _db_path():
    return settings.DATABASES['broadcast']['NAME']


def _current_shift() -> str:
    now = datetime.now().time()
    if dtime(6, 0) <= now < dtime(14, 0): return 'A'
    if dtime(14, 0) <= now < dtime(22, 0): return 'B'
    return 'C'


def _normalize_severity(severity: str) -> str:
    s = severity.strip().lower()
    if s in ('07', 'maintenance'): return 'maintenance'
    if s in ('05', 'serious'):     return 'serious'
    if s in ('99', 'catastrophic'):return 'catastrophic'
    return s


@black_box(phase='broadcast')
def get_recipients(severity: str, current_shift: str | None = None) -> list[dict]:
    """Recipients who should be notified for this severity, filtered by shift
    where applicable. Sorted by tier precedence (supervisor first)."""
    sev = _normalize_severity(severity)
    shift = current_shift or _current_shift()

    with sqlite3.connect(_db_path()) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute('SELECT * FROM recipients').fetchall()

    matches: list[dict] = []
    for r in rows:
        notify_on = [v.strip() for v in (r['notify_on'] or '').split(',')]
        if sev not in notify_on:
            continue
        # Shift-scoped recipients only fire on their shift
        if r['shift'] and r['shift'] != shift:
            continue
        matches.append(dict(r))

    matches.sort(key=lambda x: (TIER_ORDER.index(x['tier']) if x['tier'] in TIER_ORDER else 99,
                                 x['recipient_id']))
    return matches


def _channels_for_tier(tier: str, severity: str) -> list[str]:
    if tier == 'supervisor':
        return ['radio', 'sat_phone']
    if tier == 'operations':
        return ['radio', 'sat_phone', 'email']
    if tier == 'safety':
        return ['sat_phone', 'email', 'pager']
    if tier == 'executive':
        return ['sat_phone', 'email']
    if tier == 'emergency':
        return ['emergency_broadcast', 'sat_phone']
    return ['email']


@black_box(phase='broadcast')
def dispatch(*, severity: str, code: str, machine_id: str,
             summary: str, current_shift: str | None = None) -> dict:
    """Produce the broadcast plan for a fault. Does not actually send messages
    (simulated), but records every recipient + channel to the Black Box so the
    chain is auditable in the PDF and the UI."""
    shift = current_shift or _current_shift()
    recipients = get_recipients(severity, shift)

    dispatched: list[dict] = []
    for r in recipients:
        channels = _channels_for_tier(r['tier'], severity)
        dispatched.append({
            'recipient_id':  r['recipient_id'],
            'name':          r['name'],
            'title':         r['title'],
            'tier':          r['tier'],
            'shift':         r['shift'],
            'contact_phone': r['contact_phone'],
            'contact_email': r['contact_email'],
            'radio_channel': r['radio_channel'],
            'channels':      channels,
            'delivered':     True,   # simulated — real backend would enqueue
        })

    return {
        'incident_id':  get_current_incident(),
        'severity':     severity,
        'code':         code,
        'machine_id':   machine_id,
        'current_shift': shift,
        'summary':      summary,
        'recipient_count': len(dispatched),
        'tier_counts': {
            t: sum(1 for d in dispatched if d['tier'] == t) for t in TIER_ORDER
        },
        'recipients':   dispatched,
    }
