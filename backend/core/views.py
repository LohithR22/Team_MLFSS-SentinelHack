import sqlite3
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import BlackBoxIncident


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------

@api_view(['GET'])
def health(_request):
    return Response({'status': 'ok', 'service': 'sentinel-backend'})


@api_view(['GET'])
def status(_request):
    """Verify team DBs + artifacts reachable."""
    counts = {}
    for alias, table in [
        ('fault_codes', 'fault_codes'),
        ('fault_codes', 'tools'),
        ('fault_codes', 'parts'),
        ('technicians', 'technicians'),
    ]:
        db_path = settings.DATABASES[alias]['NAME']
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            counts[f'{alias}.{table}'] = cur.fetchone()[0]

    kb_files = sorted(p.name for p in settings.KB_DIR.glob('*.json'))
    tool_images = len(list(settings.TOOL_IMAGES_DIR.glob('*.jpg')))
    florence = settings.REPO_ROOT / 'tool_descriptions_florence.json'

    return Response({
        'db_row_counts': counts,
        'kb_files': kb_files,
        'tool_images': tool_images,
        'florence_descriptions_present': florence.exists(),
    })


# ---------------------------------------------------------------------------
# Black Box incident endpoints
# ---------------------------------------------------------------------------

def _incident_payload(inc: BlackBoxIncident, include_logs: bool = False) -> dict:
    data = {
        'incident_id': inc.incident_id,
        'opened_at': inc.opened_at,
        'closed_at': inc.closed_at,
        'code': inc.code,
        'machine_id': inc.machine_id,
        'severity': inc.severity,
        'first_drift_ts': inc.first_drift_ts,
        'detected_ts': inc.detected_ts,
        'status': inc.status,
        'assigned_tech': inc.assigned_tech,
        'resolution_note': inc.resolution_note,
    }
    if include_logs:
        data['log'] = [
            {
                'id': row.id,
                'ts': row.ts,
                'phase': row.phase,
                'agent': row.agent,
                'action': row.action,
                'inputs_json': row.inputs_json,
                'outputs_json': row.outputs_json,
                'duration_ms': row.duration_ms,
                'status': row.status,
                'error_msg': row.error_msg,
            }
            for row in inc.log_entries.all()
        ]
    return data


@api_view(['GET'])
def incidents_list(_request):
    qs = BlackBoxIncident.objects.all()[:200]
    return Response({'count': qs.count(), 'incidents': [_incident_payload(i) for i in qs]})


@api_view(['GET'])
def incident_detail(_request, incident_id: str):
    inc = get_object_or_404(BlackBoxIncident, incident_id=incident_id)
    return Response(_incident_payload(inc, include_logs=True))


# ---------------------------------------------------------------------------
# Audio file serving (live-generated alert audio from TTS)
# ---------------------------------------------------------------------------

def serve_narration(_request, filename: str):
    # Guard against path traversal.
    if '/' in filename or '\\' in filename or filename.startswith('.'):
        raise Http404
    path = Path(settings.BASE_DIR) / 'runtime_audio' / filename
    if not path.exists():
        raise Http404(f'No audio file {filename!r}')
    return FileResponse(open(path, 'rb'), content_type='audio/aiff')


# ---------------------------------------------------------------------------
# Tool image serving (RigTools_Images/*)
# ---------------------------------------------------------------------------

_TOOL_IMG_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.webp': 'image/webp',
}


def serve_tool_image(_request, filename: str):
    """Serve images from RigTools_Images/. Path-traversal safe."""
    if '/' in filename or '\\' in filename or filename.startswith('.'):
        raise Http404
    path = settings.TOOL_IMAGES_DIR / filename
    if not path.exists() or not path.is_file():
        raise Http404(f'No tool image {filename!r}')
    ctype = _TOOL_IMG_TYPES.get(path.suffix.lower(), 'application/octet-stream')
    return FileResponse(open(path, 'rb'), content_type=ctype)
