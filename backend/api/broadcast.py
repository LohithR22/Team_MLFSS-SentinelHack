from rest_framework.decorators import api_view
from rest_framework.response import Response

from agents import broadcast as broadcast_agent


@api_view(['GET'])
def recipients(request):
    sev = request.query_params.get('severity', 'Catastrophic')
    return Response({
        'severity': sev,
        'recipients': broadcast_agent.get_recipients(sev),
    })


@api_view(['POST', 'GET'])
def dispatch(request):
    data = request.data if request.method == 'POST' else request.query_params
    required = ('severity', 'code', 'machine_id', 'summary')
    missing = [k for k in required if not data.get(k)]
    if missing:
        return Response({'error': f'missing fields: {missing}'}, status=400)
    return Response(broadcast_agent.dispatch(
        severity=data['severity'],
        code=data['code'],
        machine_id=data['machine_id'],
        summary=data['summary'],
    ))
