"""
FTP Delivery Agent — pushes the Black Box PDF to devices on the local network.

Config lives in backend/ftp_targets.json (re-read on every dispatch so you
can edit IPs/credentials without restarting Django):
    [
      { "label": "Primary Device",
        "host": "192.168.45.61", "port": 21,
        "username": "anonymous", "password": "",
        "remote_dir": "/",
        "notify_on": ["maintenance", "serious", "catastrophic"] }
    ]

Severity → target routing is via each target's `notify_on` list. Add more
targets with tighter lists later (e.g. CEO laptop with `['catastrophic']`).
"""
from __future__ import annotations

import json
from ftplib import FTP, error_perm, error_reply, error_temp
from io import BytesIO
from pathlib import Path

from django.conf import settings

from agents.black_box import black_box, get_current_incident


def _config_path() -> Path:
    return Path(settings.BASE_DIR) / 'ftp_targets.json'


def _normalize_severity(severity: str) -> str:
    s = severity.strip().lower()
    return {'07': 'maintenance', '05': 'serious', '99': 'catastrophic'}.get(s, s)


def _load_targets() -> list[dict]:
    p = _config_path()
    if not p.exists():
        return []
    try:
        with open(p) as f:
            return json.load(f) or []
    except Exception:
        return []


@black_box(phase='ftp')
def get_targets(severity: str) -> list[dict]:
    """Targets whose `notify_on` list includes this severity."""
    sev = _normalize_severity(severity)
    out: list[dict] = []
    for t in _load_targets():
        notify_on = [v.strip().lower() for v in (t.get('notify_on') or [])]
        if sev in notify_on:
            # Echo a safe subset (never echo password to logs)
            out.append({
                'label': t.get('label', t.get('host', 'unknown')),
                'host':  t.get('host'),
                'port':  int(t.get('port', 21)),
                'remote_dir': t.get('remote_dir', '/'),
                'notify_on': notify_on,
            })
    return out


def _upload(target: dict, full: dict, pdf_bytes: bytes, remote_name: str) -> dict:
    """Blocking FTP upload with a tight timeout. Returns per-target status."""
    host = full.get('host')
    port = int(full.get('port', 21))
    username = full.get('username') or 'anonymous'
    password = full.get('password', '')
    remote_dir = full.get('remote_dir') or '/'

    result = {
        'label': target['label'],
        'host': host,
        'port': port,
        'remote_path': f"{remote_dir.rstrip('/')}/{remote_name}",
        'ok': False,
        'error': None,
        'bytes': len(pdf_bytes),
    }
    try:
        ftp = FTP()
        ftp.connect(host=host, port=port, timeout=8)
        ftp.login(user=username, passwd=password)
        # cwd to remote_dir; if it doesn't exist, fail cleanly.
        if remote_dir and remote_dir != '/':
            try:
                ftp.cwd(remote_dir)
            except (error_perm, error_reply, error_temp) as e:
                raise RuntimeError(f'cwd {remote_dir!r} failed: {e}') from e
        ftp.storbinary(f'STOR {remote_name}', BytesIO(pdf_bytes))
        ftp.quit()
        result['ok'] = True
    except Exception as e:
        result['error'] = f'{type(e).__name__}: {e}'
    return result


@black_box(phase='ftp')
def dispatch(*, severity: str, pdf_bytes: bytes, filename: str,
             code: str | None = None, machine_id: str | None = None) -> dict:
    """
    Send the PDF to all targets that match this severity.

    `pdf_bytes` is the raw report bytes; `filename` is the suggested remote
    filename (agent will use it verbatim). Returns aggregated per-target
    results. Does NOT raise — individual failures are reported.
    """
    targets_full = _load_targets()
    sev = _normalize_severity(severity)
    matches = [t for t in targets_full
               if sev in [v.strip().lower() for v in (t.get('notify_on') or [])]]

    if not matches:
        return {
            'incident_id': get_current_incident(),
            'severity': severity,
            'target_count': 0,
            'delivered': 0,
            'failed': 0,
            'results': [],
            'note': 'no FTP targets configured for this severity',
        }

    results = []
    for full in matches:
        # Strip password from the 'target' echo passed to _upload
        public = {k: v for k, v in full.items() if k != 'password'}
        results.append(_upload(public, full, pdf_bytes, filename))

    delivered = sum(1 for r in results if r['ok'])
    failed = len(results) - delivered
    return {
        'incident_id': get_current_incident(),
        'severity': severity,
        'code': code,
        'machine_id': machine_id,
        'filename': filename,
        'target_count': len(matches),
        'delivered': delivered,
        'failed': failed,
        'results': results,
    }
