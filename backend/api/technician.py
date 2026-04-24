from rest_framework.decorators import api_view
from rest_framework.response import Response

from agents import technician as tech_agent


@api_view(['GET'])
def assign(request):
    """GET /api/technicians/assign/?code=01-02-99&severity=99&part_available=true"""
    code = request.query_params.get('code')
    severity = request.query_params.get('severity')
    if not code or not severity:
        return Response({'error': 'code and severity query params required'}, status=400)
    part_available = request.query_params.get('part_available', 'true').lower() != 'false'
    try:
        return Response(tech_agent.assign_technician(code, severity, part_available))
    except ValueError as e:
        return Response({'error': str(e)}, status=404)


@api_view(['GET'])
def on_shift(request):
    shift = request.query_params.get('shift')
    try:
        rows = tech_agent.list_on_shift(shift)
    except ValueError as e:
        return Response({'error': str(e)}, status=400)
    return Response({'count': len(rows), 'technicians': rows})


@api_view(['GET'])
def detail(_request, technician_id: str):
    try:
        return Response(tech_agent.get_technician(technician_id))
    except ValueError as e:
        return Response({'error': str(e)}, status=404)
