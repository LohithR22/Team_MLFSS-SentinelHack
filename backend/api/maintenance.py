from rest_framework.decorators import api_view
from rest_framework.response import Response

from agents import maintenance as maint_agent


@api_view(['GET'])
def schedule(request):
    code = request.query_params.get('code')
    machine_id = request.query_params.get('machine_id')
    if not code or not machine_id:
        return Response({'error': 'code and machine_id required'}, status=400)
    fault_name = request.query_params.get('fault_name')
    include_current = request.query_params.get('include_current', 'true').lower() != 'false'
    return Response(maint_agent.analyze_recurrence(
        code=code, machine_id=machine_id,
        fault_name=fault_name, include_current=include_current,
    ))
