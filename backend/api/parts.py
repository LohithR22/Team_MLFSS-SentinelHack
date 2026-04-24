from rest_framework.decorators import api_view
from rest_framework.response import Response

from agents import parts as parts_agent


@api_view(['GET'])
def part_for_code(_request, code: str):
    try:
        return Response(parts_agent.get_part_for_code(code))
    except ValueError as e:
        return Response({'error': str(e)}, status=404)


@api_view(['GET'])
def part_availability(_request, part_number: str):
    try:
        return Response(parts_agent.check_availability(part_number))
    except ValueError as e:
        return Response({'error': str(e)}, status=404)


@api_view(['GET'])
def parts_unavailable(_request):
    rows = parts_agent.list_unavailable()
    return Response({'count': len(rows), 'parts': rows})
