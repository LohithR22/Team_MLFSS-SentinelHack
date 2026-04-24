from rest_framework.decorators import api_view
from rest_framework.response import Response

from agents import problem_generator as pg


@api_view(['GET'])
def scenarios(_request):
    rows = pg.list_scenarios()
    return Response({'count': len(rows), 'scenarios': rows})


@api_view(['POST', 'GET'])
def simulate(request):
    scenario = request.query_params.get('scenario') or (request.data or {}).get('scenario')
    if not scenario:
        return Response({'error': 'scenario query param or body field required'}, status=400)
    try:
        return Response(pg.simulate_scenario(scenario))
    except ValueError as e:
        return Response({'error': str(e)}, status=404)


@api_view(['GET'])
def telemetry(request):
    scenario = request.query_params.get('scenario')
    if not scenario:
        return Response({'error': 'scenario query param required'}, status=400)
    limit = int(request.query_params.get('limit', 100))
    try:
        rows = pg.recent_telemetry(scenario, limit)
    except ValueError as e:
        return Response({'error': str(e)}, status=404)
    return Response({'scenario': scenario, 'count': len(rows), 'rows': rows})
