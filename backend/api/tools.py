from rest_framework.decorators import api_view
from rest_framework.response import Response

from agents import tools as tools_agent


@api_view(['GET'])
def tool_by_name(_request, name: str):
    return Response(tools_agent.get_tool(name))


@api_view(['GET'])
def tools_by_code(_request, code: str):
    try:
        rows = tools_agent.get_tools_for_code(code)
    except ValueError as e:
        return Response({'error': str(e)}, status=404)
    found = sum(1 for t in rows if t['found_in_room_8'])
    return Response({
        'code': code,
        'count': len(rows),
        'found_in_room_8': found,
        'procurement_needed': len(rows) - found,
        'tools': rows,
    })


@api_view(['GET'])
def tools_list(_request):
    rows = tools_agent.list_all_tools()
    return Response({'count': len(rows), 'tools': rows})
