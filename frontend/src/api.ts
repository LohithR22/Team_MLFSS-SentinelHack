import type { Incident, Scenario, SolveResponse } from './types'

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init)
  if (!r.ok) {
    const body = await r.text()
    throw new Error(`${r.status} ${path} — ${body}`)
  }
  return r.json() as Promise<T>
}

export const api = {
  scenarios: () =>
    j<{ count: number; scenarios: Scenario[] }>('/api/problem/scenarios/'),

  solve: (scenario: string) =>
    j<SolveResponse>(`/api/solve/?scenario=${encodeURIComponent(scenario)}`),

  incidents: () =>
    j<{ count: number; incidents: Incident[] }>('/api/incidents/'),

  incident: (id: string) =>
    j<Incident>(`/api/incidents/${id}/`),

  telemetry: (scenario: string, limit = 120) =>
    j<{ scenario: string; count: number; rows: Array<Record<string, unknown>> }>(
      `/api/problem/telemetry/?scenario=${encodeURIComponent(scenario)}&limit=${limit}`,
    ),

  replayAudio: (filename: string) =>
    fetch(`/api/alert/replay/${encodeURIComponent(filename)}/`, { method: 'POST' }),
}
