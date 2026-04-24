from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from agents import ftp_delivery as ftp_agent


@api_view(['GET'])
def targets(request):
    sev = request.query_params.get('severity', 'Catastrophic')
    return Response({'severity': sev, 'targets': ftp_agent.get_targets(sev)})


@api_view(['POST'])
@parser_classes([MultiPartParser])
def send_report(request):
    """
    POST multipart:
      - file: the PDF (binary)
      - severity: 'Maintenance' | 'Serious' | 'Catastrophic'  (or 07/05/99)
      - incident_id: optional (used as filename if no filename provided)
      - code, machine_id: optional, for logging
    """
    f = request.FILES.get('file')
    if not f:
        return Response({'error': 'missing "file" (multipart PDF)'}, status=400)
    severity = request.data.get('severity')
    if not severity:
        return Response({'error': 'missing "severity"'}, status=400)

    pdf_bytes = f.read()
    filename = f.name or (request.data.get('incident_id') or 'report') + '.pdf'

    result = ftp_agent.dispatch(
        severity=severity,
        pdf_bytes=pdf_bytes,
        filename=filename,
        code=request.data.get('code'),
        machine_id=request.data.get('machine_id'),
    )
    return Response(result)
