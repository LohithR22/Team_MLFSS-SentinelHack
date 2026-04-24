"""
Black Box Agent — the flight recorder.

Every other agent wraps its public functions with @black_box(phase=...).
The decorator captures inputs, outputs, timing, and errors, then appends
a row to black_box_log tied to the currently-open incident.

Lifecycle:
    open_incident(event)        -> incident_id  (sets the context var)
    ... downstream agents run, their @black_box calls auto-log ...
    close_incident(incident_id, resolution)

The context var means agents never need to pass incident_id through their
signatures. If no incident is open, calls still run but are not logged.
"""
from __future__ import annotations

import functools
import json
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Callable

_current_incident: ContextVar[str | None] = ContextVar(
    'sentinel_current_incident', default=None
)

# Max chars stored per JSON blob — keeps the log table slim.
_MAX_JSON_LEN = 10_000


# ---------------------------------------------------------------------------
# Context management
# ---------------------------------------------------------------------------

def set_current_incident(incident_id: str | None) -> None:
    _current_incident.set(incident_id)


def get_current_incident() -> str | None:
    return _current_incident.get()


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _safe_json(obj: Any) -> str:
    try:
        blob = json.dumps(obj, default=str, ensure_ascii=False)
    except Exception:
        blob = json.dumps({'_unserializable_repr': repr(obj)[:500]})
    if len(blob) > _MAX_JSON_LEN:
        blob = blob[: _MAX_JSON_LEN - 3] + '...'
    return blob


def _next_incident_id() -> str:
    """Generate INC-YYYYMMDD-NNNN, where NNNN is today's sequence."""
    from core.models import BlackBoxIncident

    today = datetime.now(timezone.utc).strftime('%Y%m%d')
    prefix = f'INC-{today}-'
    last = (
        BlackBoxIncident.objects
        .filter(incident_id__startswith=prefix)
        .order_by('-incident_id')
        .values_list('incident_id', flat=True)
        .first()
    )
    seq = int(last.rsplit('-', 1)[-1]) + 1 if last else 1
    return f'{prefix}{seq:04d}'


# ---------------------------------------------------------------------------
# Incident lifecycle
# ---------------------------------------------------------------------------

def open_incident(
    *,
    code: str,
    machine_id: str,
    severity: str,
    detected_ts: str | None = None,
    first_drift_ts: str | None = None,
) -> str:
    """Open a new incident and set it as the current context.

    Returns the generated incident_id. Subsequent @black_box calls on the
    same thread/async task will log against this incident.
    """
    from core.models import BlackBoxIncident

    incident_id = _next_incident_id()
    BlackBoxIncident.objects.create(
        incident_id=incident_id,
        opened_at=_utcnow(),
        code=code,
        machine_id=machine_id,
        severity=severity,
        detected_ts=detected_ts or _utcnow(),
        first_drift_ts=first_drift_ts,
        status='open',
    )
    set_current_incident(incident_id)
    return incident_id


def close_incident(
    incident_id: str,
    *,
    status: str = 'resolved',
    resolution_note: str | None = None,
    assigned_tech: str | None = None,
) -> None:
    """Mark the incident closed. Does not clear the context var — caller should."""
    from core.models import BlackBoxIncident

    fields = {'closed_at': _utcnow(), 'status': status}
    if resolution_note is not None:
        fields['resolution_note'] = resolution_note
    if assigned_tech is not None:
        fields['assigned_tech'] = assigned_tech
    BlackBoxIncident.objects.filter(incident_id=incident_id).update(**fields)


def record(
    *,
    phase: str,
    agent: str,
    action: str,
    inputs: Any,
    outputs: Any = None,
    duration_ms: int = 0,
    status: str = 'ok',
    error_msg: str | None = None,
    incident_id: str | None = None,
) -> None:
    """Write a manual log entry (for code paths that can't use the decorator)."""
    from core.models import BlackBoxLog

    iid = incident_id or get_current_incident()
    if iid is None:
        return  # no incident open — drop silently
    try:
        BlackBoxLog.objects.create(
            incident_id=iid,
            ts=_utcnow(),
            phase=phase,
            agent=agent,
            action=action,
            inputs_json=_safe_json(inputs),
            outputs_json=_safe_json(outputs) if outputs is not None else None,
            duration_ms=duration_ms,
            status=status,
            error_msg=error_msg,
        )
    except Exception:
        # Logging must never break the real call.
        pass


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

def black_box(phase: str) -> Callable:
    """
    Decorator for agent functions.

    Usage:
        @black_box(phase='parts')
        def get_part_for_code(code: str) -> dict: ...

    Captures args/kwargs as inputs_json, return value as outputs_json,
    wall-clock time as duration_ms, exceptions as status='error'.
    """
    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.monotonic()
            output: Any = None
            status = 'ok'
            err: str | None = None
            try:
                output = fn(*args, **kwargs)
                return output
            except Exception as e:
                status = 'error'
                err = f'{type(e).__name__}: {e}'
                raise
            finally:
                duration_ms = int((time.monotonic() - start) * 1000)
                record(
                    phase=phase,
                    agent=fn.__module__.rsplit('.', 1)[-1],
                    action=fn.__name__,
                    inputs={'args': list(args), 'kwargs': kwargs},
                    outputs=output if status == 'ok' else None,
                    duration_ms=duration_ms,
                    status=status,
                    error_msg=err,
                )
        return wrapper
    return deco
