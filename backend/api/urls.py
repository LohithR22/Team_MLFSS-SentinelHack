from django.urls import path

from . import alert, llm, parts, problem, solution, technician, tools

urlpatterns = [
    # Parts Agent
    path('parts/unavailable/',                parts.parts_unavailable,  name='parts_unavailable'),
    path('parts/by-code/<str:code>/',         parts.part_for_code,      name='parts_by_code'),
    path('parts/by-number/<str:part_number>/', parts.part_availability, name='parts_by_number'),

    # Tools Agent
    path('tools/',                     tools.tools_list,    name='tools_list'),
    path('tools/by-code/<str:code>/',  tools.tools_by_code, name='tools_by_code'),
    path('tools/by-name/<str:name>/',  tools.tool_by_name,  name='tools_by_name'),

    # Technician Agent
    path('technicians/assign/',                      technician.assign,    name='technician_assign'),
    path('technicians/on-shift/',                    technician.on_shift,  name='technician_on_shift'),
    path('technicians/<str:technician_id>/',         technician.detail,    name='technician_detail'),

    # Alert Agent
    path('alert/trigger/',                           alert.trigger,        name='alert_trigger'),
    path('alert/replay/<str:filename>/',             alert.replay,         name='alert_replay'),

    # Problem Generator Agent
    path('problem/scenarios/',                       problem.scenarios,    name='problem_scenarios'),
    path('problem/simulate/',                        problem.simulate,     name='problem_simulate'),
    path('problem/telemetry/',                       problem.telemetry,    name='problem_telemetry'),

    # LLM (Llama-3.2-1B-Instruct)
    path('llm/status/',                              llm.status,           name='llm_status'),
    path('llm/test/',                                llm.test,             name='llm_test'),

    # Solution Agent — end-to-end orchestrator
    path('solve/',                                   solution.solve,       name='solve'),
]
