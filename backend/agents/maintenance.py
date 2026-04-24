"""
Maintenance Agent — recurring-fault detection + preventive schedule.

Reads BlackBoxIncident history for (code, machine_id) and, if the same fault
keeps coming back, produces a preventive-maintenance recommendation with a
priority and next-service date.

Priority rules (tunable, current values balance demo + realism):
    count == 1             -> 'normal'  (no recommendation)
    count == 2             -> 'routine'  next_service = +7 days
    count == 3             -> 'urgent'   next_service = +48 hours
    count >= 4             -> 'critical' next_service = +24 hours

An extra escalation kicks in if the AVERAGE interval between incidents is
below 6 hours (a sign the fault is cascading), bumping priority one level.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from agents.black_box import black_box


PRIORITY_ORDER = ['normal', 'routine', 'urgent', 'critical']


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except Exception:
        return None


def _bump(priority: str) -> str:
    i = PRIORITY_ORDER.index(priority) if priority in PRIORITY_ORDER else 0
    return PRIORITY_ORDER[min(i + 1, len(PRIORITY_ORDER) - 1)]


def _action_for(priority: str, fault_name: str) -> str:
    base = fault_name or 'Issue'
    return {
        'normal':   f'No recurring pattern yet for {base}. Continue routine monitoring.',
        'routine':  f'Pattern emerging for {base}. Schedule preventive inspection.',
        'urgent':   f'Recurring {base}. Schedule overhaul and replace wear parts.',
        'critical': f'{base} is a persistent failure. Take machine offline for full overhaul within 24 hours.',
    }.get(priority, f'Review {base}.')


@black_box(phase='maintenance')
def analyze_recurrence(code: str, machine_id: str,
                       fault_name: str | None = None,
                       include_current: bool = True) -> dict[str, Any]:
    """
    Look at past Black Box incidents for this (code, machine_id).

    Returns a dict with:
        machine_id, code, fault_name
        occurrence_count, first_seen, last_seen, avg_interval_hours
        priority          ('normal' | 'routine' | 'urgent' | 'critical')
        next_service_at   (ISO timestamp, UTC)
        recommendation    (human-readable action)
        recurring         (bool — convenience: count >= 2)
        history           (list of {incident_id, opened_at, severity, status})
    """
    from core.models import BlackBoxIncident

    qs = BlackBoxIncident.objects.filter(
        code=code, machine_id=machine_id,
    ).order_by('opened_at')

    history = [
        {
            'incident_id': i.incident_id,
            'opened_at':   i.opened_at,
            'severity':    i.severity,
            'status':      i.status,
        }
        for i in qs
    ]

    count = len(history)
    if not include_current and count > 0:
        count -= 1   # exclude the one we just opened

    if count <= 0:
        now = datetime.now(timezone.utc)
        return {
            'machine_id': machine_id,
            'code': code,
            'fault_name': fault_name,
            'occurrence_count': 0,
            'first_seen': None,
            'last_seen': None,
            'avg_interval_hours': None,
            'priority': 'normal',
            'next_service_at': None,
            'recommendation': _action_for('normal', fault_name or 'fault'),
            'recurring': False,
            'history': [],
        }

    # Compute interval stats between consecutive incidents.
    opened_dts = [dt for i in history if (dt := _parse_iso(i['opened_at']))]
    avg_interval_h: float | None = None
    if len(opened_dts) >= 2:
        deltas = [
            (opened_dts[k] - opened_dts[k - 1]).total_seconds() / 3600
            for k in range(1, len(opened_dts))
        ]
        avg_interval_h = round(mean(deltas), 2)

    # Base priority from count.
    if count == 1:
        priority = 'normal'
    elif count == 2:
        priority = 'routine'
    elif count == 3:
        priority = 'urgent'
    else:
        priority = 'critical'

    # Frequency escalation: cascading failures bump the priority.
    if avg_interval_h is not None and avg_interval_h < 6:
        priority = _bump(priority)

    # Next service window.
    now = datetime.now(timezone.utc)
    if priority == 'normal':
        next_service_at = None
    elif priority == 'routine':
        next_service_at = now + timedelta(days=7)
    elif priority == 'urgent':
        next_service_at = now + timedelta(hours=48)
    else:  # critical
        next_service_at = now + timedelta(hours=24)

    return {
        'machine_id': machine_id,
        'code': code,
        'fault_name': fault_name,
        'occurrence_count': count,
        'first_seen': history[0]['opened_at'] if history else None,
        'last_seen':  history[-1]['opened_at'] if history else None,
        'avg_interval_hours': avg_interval_h,
        'priority': priority,
        'next_service_at': next_service_at.isoformat(timespec='seconds') if next_service_at else None,
        'recommendation': _action_for(priority, fault_name or 'fault'),
        'recurring': count >= 2,
        'history': history[-10:],   # cap for payload size
    }
