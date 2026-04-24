"""
Django ORM for SentinelHack runtime state.

Lives in the default database (runtime_state.db). Team DBs (fault_codes,
sensor_data, technicians) are read-only and accessed via raw queries — no
models here mirror them.
"""
from django.db import models


class BlackBoxIncident(models.Model):
    """
    One row per fault incident. Opened by Problem Generator, closed by
    Technician Agent (or admin) when the repair is verified.
    """
    incident_id     = models.CharField(max_length=32, primary_key=True)
    opened_at       = models.CharField(max_length=32)
    closed_at       = models.CharField(max_length=32, null=True, blank=True)

    code            = models.CharField(max_length=16)
    machine_id      = models.CharField(max_length=32)
    severity        = models.CharField(max_length=16)

    first_drift_ts  = models.CharField(max_length=32, null=True, blank=True)
    detected_ts     = models.CharField(max_length=32)

    status          = models.CharField(max_length=16, default='open')
    assigned_tech   = models.CharField(max_length=32, null=True, blank=True)
    resolution_note = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'black_box_incidents'
        ordering = ['-opened_at']


class BlackBoxLog(models.Model):
    """
    Append-only log of every agent call tied to an incident. Written by the
    @black_box decorator in agents.black_box.
    """
    incident = models.ForeignKey(
        BlackBoxIncident,
        on_delete=models.CASCADE,
        db_column='incident_id',
        related_name='log_entries',
    )
    ts           = models.CharField(max_length=32)
    phase        = models.CharField(max_length=32)
    agent        = models.CharField(max_length=64)
    action       = models.CharField(max_length=128)
    inputs_json  = models.TextField()
    outputs_json = models.TextField(null=True, blank=True)
    duration_ms  = models.IntegerField()
    status       = models.CharField(max_length=16)
    error_msg    = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'black_box_log'
        ordering = ['id']
