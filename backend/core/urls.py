from django.urls import path

from . import views

urlpatterns = [
    path('health/', views.health, name='health'),
    path('status/', views.status, name='status'),
    path('incidents/', views.incidents_list, name='incidents_list'),
    path('incidents/<str:incident_id>/', views.incident_detail, name='incident_detail'),

    # Live-generated alert audio
    path('audio/narration/<str:filename>', views.serve_narration, name='serve_narration'),
]
