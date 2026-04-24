from rest_framework.decorators import api_view
from rest_framework.response import Response

from agents import alert as alert_agent


@api_view(['POST'])
def trigger(request):
    """
    POST /api/alert/trigger/
    body: {code, severity, spoken_alert, machine_id?, narrative?, autoplay?}
    """
    data = request.data or {}
    required = ('code', 'severity', 'spoken_alert')
    missing = [k for k in required if not data.get(k)]
    if missing:
        return Response({'error': f'missing fields: {missing}'}, status=400)
    return Response(
        alert_agent.trigger(
            code=data['code'],
            severity=data['severity'],
            spoken_alert=data['spoken_alert'],
            machine_id=data.get('machine_id'),
            narrative=data.get('narrative'),
            autoplay=data.get('autoplay'),
        )
    )


@api_view(['POST'])
def replay(_request, filename: str):
    """POST /api/alert/replay/<filename>/ — play a previous alert again."""
    ok = alert_agent.play_file(filename)
    return Response({'filename': filename, 'played': ok},
                    status=200 if ok else 404)
