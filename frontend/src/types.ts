export type Severity = 'Maintenance' | 'Serious' | 'Catastrophic' | string

export interface Scenario {
  scenario: string
  table: string
  code: string
  machine_id: string
  severity: Severity
}

export interface Part {
  code: string
  part_code: string
  part_name: string
  location: string | null
  availability: 'Yes' | 'No' | string
  machine: string
  severity: Severity
}

export interface ToolInfo {
  found_in_room_8: boolean
  uid?: number
  tool_name: string
  type?: string
  location: string | null
  primary_use?: string
  image_path?: string
  image_basename?: string
  visual_description?: string | null
}

export interface Technician {
  technician_id: string
  name: string
  role: 'Generalist' | 'Specialist'
  specialization: string
  shift: string
  shift_hours: string
  radio_channel: string
  quarters: string
  years_experience: number
}

export interface AlertPayload {
  incident_id: string | null
  code: string
  machine_id: string | null
  severity: Severity
  base_spoken_alert: string
  spoken_alert: string
  narrative: string | null
  alert_audio_url: string | null
  part: Part | null
  tools: ToolInfo[] | null
  technician: Technician | null
  quick_fix: string | null
  server_played: boolean
  ws_pushed?: boolean
}

export interface SolvePlan {
  code: string
  machine_id: string
  severity: Severity
  kb: {
    routed_file: string
    fault: string
    description: string
    quick_fix: string
    detailed_steps: string[]
  }
  slm: {
    narrative: string
    spoken_alert: string
    slm_parsed: boolean
    slm_raw?: string
  }
  part: Part
  tools: ToolInfo[]
  technician: Technician & { _routing?: Record<string, unknown> }
  alert: AlertPayload
}

export interface SolveResponse {
  incident_id: string
  event: {
    incident_id: string
    scenario: string
    code: string
    machine_id: string
    severity: Severity
    detected_ts: string
    first_drift_ts: string | null
    telemetry_snapshot: Record<string, unknown>
  }
  plan: SolvePlan
}

export interface IncidentLog {
  id: number
  ts: string
  phase: string
  agent: string
  action: string
  inputs_json: string
  outputs_json: string | null
  duration_ms: number
  status: 'ok' | 'error' | string
  error_msg: string | null
}

export interface Incident {
  incident_id: string
  opened_at: string
  closed_at: string | null
  code: string
  machine_id: string
  severity: Severity
  first_drift_ts: string | null
  detected_ts: string
  status: string
  assigned_tech: string | null
  resolution_note: string | null
  log?: IncidentLog[]
}
