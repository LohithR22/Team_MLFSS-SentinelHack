from rest_framework.decorators import api_view
from rest_framework.response import Response

from agents import problem_generator as pg
from agents import solution as solution_agent
from agents.black_box import close_incident, set_current_incident


@api_view(['POST', 'GET'])
def solve(request):
    """
    End-to-end demo: simulate a scenario + run the solution pipeline.
    GET/POST /api/solve/?scenario=engine_catastrophic_failure

    Returns the full bundle: problem event + SLM plan + parts + tools +
    technician + alert + incident_id for replay via /api/incidents/.
    """
    scenario = request.query_params.get('scenario') or (request.data or {}).get('scenario')
    if not scenario:
        return Response({'error': 'scenario query param required'}, status=400)

    try:
        event = pg.simulate_scenario(scenario)
    except ValueError as e:
        return Response({'error': str(e)}, status=404)

    try:
        bundle = solution_agent.solve(
            code=event['code'],
            machine_id=event['machine_id'],
            severity=event['severity'],
            telemetry_snapshot=event['telemetry_snapshot'],
        )
    except Exception as e:
        # Close the incident as error so the Black Box captures the failure.
        iid = event.get('incident_id')
        if iid:
            close_incident(iid, status='error', resolution_note=f'{type(e).__name__}: {e}')
            set_current_incident(None)
        raise

    # Mark the incident open->resolved once the plan has been dispatched.
    close_incident(event['incident_id'], status='dispatched',
                   resolution_note='Plan produced and alert fired.')
    set_current_incident(None)

    return Response({
        'incident_id': event['incident_id'],
        'event': event,
        'plan': bundle,
    })
