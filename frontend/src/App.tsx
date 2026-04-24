import { useEffect, useState } from 'react'
import { api } from './api'
import { useAlertStream } from './hooks/useAlertStream'
import type { AlertPayload, Incident, Scenario, SolveResponse } from './types'

function sevClass(s: string) {
  return `sev-badge ${s}`
}

function Topbar({ connected }: { connected: boolean }) {
  return (
    <div className="topbar">
      <div className="brand">
        <h1>SentinelHack</h1>
        <small>Oil Rig Maintenance AI — on-rig edge</small>
      </div>
      <div className="status">
        <span className={`dot ${connected ? 'ok' : 'off'}`} />
        {connected ? 'WS connected' : 'WS offline'}
      </div>
    </div>
  )
}

function ScenarioSidebar({
  scenarios,
  onPick,
  busy,
}: {
  scenarios: Scenario[]
  onPick: (s: string) => void
  busy: boolean
}) {
  return (
    <div className="sidebar">
      <h2>Scenarios</h2>
      <div className="scenario-list">
        {scenarios.map(s => (
          <button
            key={s.scenario}
            className="scenario-row"
            onClick={() => onPick(s.scenario)}
            disabled={busy}
          >
            <span className="title">{s.scenario.replace(/_/g, ' ')}</span>
            <span className="meta">
              <span>{s.code}</span>
              <span>{s.machine_id}</span>
              <span className={sevClass(s.severity)}>{s.severity}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}

function PlanView({ data }: { data: SolveResponse }) {
  const { plan, event, incident_id } = data
  const { part, tools, technician, alert, kb, slm } = plan

  return (
    <div className="grid" style={{ gap: 14 }}>
      <div className="card">
        <h3>Incident</h3>
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'center' }}>
          <div><div className="k">Incident ID</div><div className="big">{incident_id}</div></div>
          <div><div className="k">Code</div><div className="big">{plan.code}</div></div>
          <div><div className="k">Machine</div><div className="big">{plan.machine_id}</div></div>
          <div><div className="k">Severity</div><div><span className={sevClass(plan.severity)}>{plan.severity}</span></div></div>
          <div><div className="k">KB file</div><div className="v">{kb.routed_file}</div></div>
          <div><div className="k">First drift</div><div className="v">{event.first_drift_ts ?? '—'}</div></div>
          <div><div className="k">Detected</div><div className="v">{event.detected_ts}</div></div>
        </div>
      </div>

      <div className="card" style={{ borderColor: '#7a1e1e' }}>
        <h3>Voice Alert</h3>
        <p style={{ marginTop: 0, fontSize: 15 }}>{alert.spoken_alert}</p>
        {alert.alert_audio_url && (
          <audio controls src={alert.alert_audio_url} style={{ width: '100%', marginTop: 8 }} />
        )}
        <div className="kv" style={{ marginTop: 10 }}>
          <div className="k">Server autoplay</div>
          <div>{alert.server_played ? <span className="pill ok">played</span> : <span className="pill">muted</span>}</div>
          <div className="k">Base SLM</div>
          <div>{alert.base_spoken_alert}</div>
        </div>
      </div>

      <div className="card">
        <h3>Fault — {kb.fault}</h3>
        <p style={{ color: 'var(--muted)', marginTop: 0 }}>{kb.description}</p>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h3>Replacement Part</h3>
          <div className="big">{part.part_name}</div>
          <div className="k" style={{ marginTop: 4 }}>{part.part_code}</div>
          <div className="kv" style={{ marginTop: 10 }}>
            <div className="k">Location</div><div>{part.location ?? '—'}</div>
            <div className="k">Availability</div>
            <div>
              {part.availability === 'Yes' ? (
                <span className="pill ok">In stock</span>
              ) : part.availability === 'No' ? (
                <span className="pill no">Out of stock — escalate</span>
              ) : (
                <span className="pill warn">{part.availability}</span>
              )}
            </div>
          </div>
        </div>

        <div className="card">
          <h3>Assigned Technician</h3>
          <div className="big">{technician.name}</div>
          <div className="k" style={{ marginTop: 4 }}>
            {technician.role} — {technician.specialization} · {technician.years_experience}y
          </div>
          <div className="kv" style={{ marginTop: 10 }}>
            <div className="k">ID</div><div>{technician.technician_id}</div>
            <div className="k">Shift</div><div>{technician.shift} ({technician.shift_hours})</div>
            <div className="k">Radio</div><div>{technician.radio_channel}</div>
            <div className="k">Quarters</div><div>{technician.quarters}</div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Tools Needed — {tools.length}</h3>
        {tools.map((t, i) => (
          <div className="tool-row" key={i}>
            <div
              style={{
                width: 48, height: 48, borderRadius: 6, border: '1px solid var(--border)',
                background: 'var(--panel-2)', display: 'flex', alignItems: 'center',
                justifyContent: 'center', fontSize: 10, color: 'var(--muted)', flexShrink: 0,
              }}
            >
              {t.type ?? '—'}
            </div>
            <div className="tool-main">
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <span className="tool-name">{t.tool_name}</span>
                {t.found_in_room_8 ? (
                  <span className="pill ok">in inventory</span>
                ) : (
                  <span className="pill no">procure</span>
                )}
              </div>
              <div className="tool-loc">
                {t.location ?? 'Not in inventory'}
                {t.primary_use && <> · <em>{t.primary_use}</em></>}
              </div>
              {t.visual_description && (
                <div className="tool-desc">{t.visual_description}</div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <h3>Quick Fix</h3>
        <div style={{ fontWeight: 500, marginBottom: 10 }}>{kb.quick_fix}</div>
        <h3 style={{ marginTop: 14 }}>Detailed Steps</h3>
        <ol className="steps">
          {kb.detailed_steps.map((s, i) => <li key={i}>{s}</li>)}
        </ol>
      </div>

      <div className="card">
        <h3>SLM Narrative (Llama-3.2-1B)</h3>
        <p style={{ marginTop: 0 }}>{slm.narrative}</p>
        <div className="k" style={{ marginTop: 8 }}>
          Parsed as JSON:{' '}
          {slm.slm_parsed ? <span className="pill ok">yes</span> : <span className="pill warn">fallback</span>}
        </div>
      </div>
    </div>
  )
}

function IncidentReplay({ id }: { id: string }) {
  const [inc, setInc] = useState<Incident | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api.incident(id).then(setInc).catch(e => setErr(String(e)))
  }, [id])

  if (err) return <div className="error">{err}</div>
  if (!inc) return <div className="loading">Loading replay…</div>

  return (
    <div className="card">
      <h3>Black Box Replay · {inc.incident_id}</h3>
      <div className="kv">
        <div className="k">Status</div><div>{inc.status}</div>
        <div className="k">Opened</div><div>{inc.opened_at}</div>
        <div className="k">Closed</div><div>{inc.closed_at ?? '—'}</div>
        <div className="k">Tech</div><div>{inc.assigned_tech ?? '—'}</div>
      </div>
      <div style={{ marginTop: 12 }}>
        {inc.log?.map(l => (
          <div className="log-row" key={l.id}>
            <span className="phase">{l.phase}</span>
            <span className="agent">{l.agent}</span>
            <span className="action">{l.action}</span>
            <span className={l.status === 'ok' ? '' : 'pill no'}>{l.status}</span>
            <span className="ms">{l.duration_ms}ms</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function AlertToast({ last }: { last: AlertPayload | null }) {
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    if (!last) return
    setVisible(true)
    const t = setTimeout(() => setVisible(false), 8000)
    return () => clearTimeout(t)
  }, [last])
  if (!visible || !last) return null
  return (
    <div className="toast">
      <h4>{last.severity} · {last.machine_id}</h4>
      <div className="sub">{last.code} · incident {last.incident_id}</div>
      <p>{last.spoken_alert.slice(0, 180)}{last.spoken_alert.length > 180 ? '…' : ''}</p>
    </div>
  )
}

export default function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [plan, setPlan] = useState<SolveResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const stream = useAlertStream()

  useEffect(() => {
    api.scenarios().then(r => setScenarios(r.scenarios)).catch(e => setErr(String(e)))
  }, [])

  const onPick = async (s: string) => {
    setBusy(true); setErr(null); setPlan(null)
    try {
      const res = await api.solve(s)
      setPlan(res)
    } catch (e) {
      setErr(String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="app">
      <Topbar connected={stream.connected} />
      <ScenarioSidebar scenarios={scenarios} onPick={onPick} busy={busy} />
      <div className="main">
        {err && <div className="error">{err}</div>}
        {busy && <div className="loading">Running scenario through the full agent pipeline… (SLM + TTS can take 4–8s)</div>}
        {!busy && !plan && !err && (
          <div className="hero">
            <h2>Pick a scenario to run</h2>
            <p>
              Each scenario replays telemetry from the sensor DB → detects the fault → runs the
              Solution Agent (KB routing + Llama-3.2-1B) → queries Parts, Tools, Technician →
              fires the Alert. Server-side audio plays the PA.
            </p>
          </div>
        )}
        {plan && (
          <div className="grid">
            <PlanView data={plan} />
            <IncidentReplay id={plan.incident_id} />
          </div>
        )}
      </div>
      <AlertToast last={stream.last} />
    </div>
  )
}
