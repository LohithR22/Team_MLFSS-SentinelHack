import { useEffect, useState } from 'react'
import { api } from './api'
import { BroadcastCard } from './components/BroadcastCard'
import { PipelineProgress } from './components/PipelineProgress'
import { RigFloorplan } from './components/RigFloorplan'
import { TelemetryChart } from './components/TelemetryChart'
import { useAlertStream } from './hooks/useAlertStream'
import { downloadIncidentPDF } from './lib/incidentPdf'
import type { AlertPayload, Incident, IncidentLog, Scenario, SolveResponse } from './types'

function sevClass(s: string) {
  return `sev-badge ${s}`
}

function Topbar({ connected }: { connected: boolean }) {
  return (
    <div className="topbar">
      <div className="brand">
        <div className="logo-mark"><span>SH</span></div>
        <div className="brand-text">
          <h1>SentinelHack</h1>
          <small>Oil Rig Maintenance AI · On-Rig Edge</small>
        </div>
      </div>
      <div className="status">
        <span className={`dot ${connected ? 'ok' : 'off'}`} />
        {connected ? 'WS Connected' : 'WS Offline'}
      </div>
    </div>
  )
}

function ScenarioSidebar({
  scenarios,
  onPick,
  busy,
  activeScenario,
}: {
  scenarios: Scenario[]
  onPick: (s: string) => void
  busy: boolean
  activeScenario: string | null
}) {
  return (
    <div className="sidebar">
      <h2>Scenarios</h2>
      <div className="scenario-list">
        {scenarios.map(s => (
          <button
            key={s.scenario}
            className={`scenario-row sev-${s.severity}`}
            onClick={() => onPick(s.scenario)}
            disabled={busy}
            style={
              activeScenario === s.scenario
                ? { borderColor: 'var(--accent)', background: 'rgba(76, 141, 255, 0.1)' }
                : undefined
            }
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

function Hero() {
  return (
    <div className="hero">
      <div className="hero-inner">
        <div className="radar" />
        <h2>Awaiting scenario</h2>
        <p>
          Pick any scenario on the left to replay live telemetry through the full agent pipeline.
          Problem Generator detects the fault → Solution Agent routes to the right KB and runs the SLM →
          Parts, Tools, Technician lookups → Alert Agent broadcasts voice over the rig PA.
        </p>
      </div>
    </div>
  )
}

function IncidentReplayActuals({ inc }: { inc: Incident | null }) {
  if (!inc?.log) return null
  const out: Record<string, number> = {}
  for (const row of inc.log) {
    // Keep the LAST duration per phase (solution.solve wraps everything so
    // there can be a final 'plan' row that represents total — we want per-phase).
    if (row.agent !== 'solution' || row.action !== 'solve') {
      out[row.phase] = (out[row.phase] ?? 0) + row.duration_ms
    }
  }
  return null // placeholder — consumed via hook below
}

void IncidentReplayActuals  // hush unused

function IncidentHeader({ data }: { data: SolveResponse }) {
  const { plan, event, incident_id } = data
  return (
    <div className={`card sev-${plan.severity}`}>
      <h3>Incident</h3>
      <div className="incident-strip">
        <div>
          <div className="k">Incident ID</div>
          <div className="big mono">{incident_id}</div>
        </div>
        <div>
          <div className="k">Code</div>
          <div className="big mono">{plan.code}</div>
        </div>
        <div>
          <div className="k">Machine</div>
          <div className="big mono">{plan.machine_id}</div>
        </div>
        <div>
          <div className="k">Severity</div>
          <div><span className={sevClass(plan.severity)}>{plan.severity}</span></div>
        </div>
        <div>
          <div className="k">KB File</div>
          <div className="v mono" style={{ fontSize: 13 }}>{plan.kb.routed_file}</div>
        </div>
        <div>
          <div className="k">First Drift</div>
          <div className="v mono" style={{ fontSize: 12 }}>{event.first_drift_ts ?? '—'}</div>
        </div>
        <div>
          <div className="k">Detected</div>
          <div className="v mono" style={{ fontSize: 12 }}>{event.detected_ts}</div>
        </div>
      </div>
    </div>
  )
}

function AlertCard({ alert }: { alert: AlertPayload }) {
  return (
    <div className="card alert-card">
      <h3>Voice Alert · Live PA</h3>
      <p className="spoken-text">{alert.spoken_alert}</p>
      {alert.alert_audio_url && (
        <div className="audio-wrap">
          <audio controls src={alert.alert_audio_url} />
        </div>
      )}
      <div className="kv" style={{ marginTop: 14 }}>
        <div className="k">Server played</div>
        <div>
          {alert.server_played
            ? <span className="pill ok">▶ played on rig speakers</span>
            : <span className="pill">muted</span>}
        </div>
        <div className="k">SLM headline</div>
        <div style={{ color: 'var(--text-dim)' }}>{alert.base_spoken_alert}</div>
      </div>
    </div>
  )
}

function PartCard({ part }: { part: SolveResponse['plan']['part'] }) {
  return (
    <div className="card">
      <h3>Replacement Part</h3>
      <div className="big">{part.part_name}</div>
      <div className="k mono" style={{ marginTop: 6, fontSize: 12 }}>{part.part_code}</div>
      <div className="kv" style={{ marginTop: 14 }}>
        <div className="k">Location</div>
        <div className="mono" style={{ fontSize: 12 }}>{part.location ?? '—'}</div>
        <div className="k">Availability</div>
        <div>
          {part.availability === 'Yes' ? (
            <span className="pill ok">In stock</span>
          ) : part.availability === 'No' ? (
            <span className="pill no">Out of stock · escalate</span>
          ) : (
            <span className="pill warn">{part.availability}</span>
          )}
        </div>
      </div>
    </div>
  )
}

function TechnicianCard({ technician }: { technician: SolveResponse['plan']['technician'] }) {
  return (
    <div className="card">
      <h3>Assigned Technician</h3>
      <div className="big">{technician.name}</div>
      <div className="k" style={{ marginTop: 6, fontSize: 11 }}>
        {technician.role} · {technician.specialization} · {technician.years_experience}y experience
      </div>
      <div className="kv" style={{ marginTop: 14 }}>
        <div className="k">ID</div>
        <div className="mono" style={{ fontSize: 12 }}>{technician.technician_id}</div>
        <div className="k">Shift</div>
        <div>{technician.shift} <span style={{ color: 'var(--muted)' }}>({technician.shift_hours})</span></div>
        <div className="k">Radio</div>
        <div className="mono" style={{ fontSize: 12 }}>{technician.radio_channel}</div>
        <div className="k">Quarters</div>
        <div style={{ fontSize: 12 }}>{technician.quarters}</div>
      </div>
    </div>
  )
}

function ToolsCard({ tools }: { tools: SolveResponse['plan']['tools'] }) {
  return (
    <div className="card">
      <h3>Tools Needed · {tools.length}</h3>
      {tools.map((t, i) => (
        <div className="tool-row" key={i}>
          <div className="tool-type-chip">{t.type ?? '—'}</div>
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
              {t.primary_use && (
                <>
                  {' · '}
                  <em style={{ color: 'var(--text-dim)' }}>{t.primary_use}</em>
                </>
              )}
            </div>
            {t.visual_description && (
              <div className="tool-desc">{t.visual_description}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function ProcedureCard({ kb }: { kb: SolveResponse['plan']['kb'] }) {
  return (
    <div className="card">
      <h3>Quick Fix</h3>
      <div className="quickfix-text">{kb.quick_fix}</div>
      <h3 style={{ marginTop: 18 }}>Detailed Steps</h3>
      <ol className="steps">
        {kb.detailed_steps.map((s, i) => <li key={i}>{s}</li>)}
      </ol>
    </div>
  )
}

function NarrativeCard({ kb, slm }: { kb: SolveResponse['plan']['kb']; slm: SolveResponse['plan']['slm'] }) {
  return (
    <div className="card">
      <h3>Fault · {kb.fault}</h3>
      <p style={{ color: 'var(--text-dim)', marginTop: 0, lineHeight: 1.65, fontSize: 13 }}>{kb.description}</p>
      <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px dashed var(--border)' }}>
        <h3 style={{ marginTop: 0 }}>SLM Narrative · Llama-3.2-1B</h3>
        <p style={{ marginTop: 0, color: 'var(--text)', fontSize: 13 }}>{slm.narrative}</p>
        <div className="k" style={{ marginTop: 10 }}>
          JSON parsed:{' '}
          {slm.slm_parsed ? <span className="pill ok">yes</span> : <span className="pill warn">fallback template</span>}
        </div>
      </div>
    </div>
  )
}

function useIncident(id: string | null) {
  const [inc, setInc] = useState<Incident | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    if (!id) return
    setInc(null); setErr(null)
    api.incident(id).then(setInc).catch(e => setErr(String(e)))
  }, [id])
  return { inc, err }
}

function prettyJson(s: string | null | undefined): string {
  if (!s) return '—'
  try { return JSON.stringify(JSON.parse(s), null, 2) } catch { return s }
}

function LogRow({ l }: { l: IncidentLog }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={`log-row-wrap ${open ? 'open' : ''}`}>
      <button className="log-row log-row-btn" onClick={() => setOpen(o => !o)}>
        <span className="phase">{l.phase}</span>
        <span className="agent">{l.agent}</span>
        <span className="action">{l.action}</span>
        <span className={l.status === 'ok' ? 'status-ok' : 'pill no'}>{l.status}</span>
        <span className="ms">{l.duration_ms}ms</span>
      </button>
      {open && (
        <div className="log-details">
          <div className="log-meta">
            <span className="k">Timestamp</span>
            <span className="mono">{l.ts}</span>
          </div>
          {l.error_msg && (
            <>
              <div className="log-label error-label">Error</div>
              <pre className="log-pre error-pre">{l.error_msg}</pre>
            </>
          )}
          <div className="log-label">Inputs</div>
          <pre className="log-pre">{prettyJson(l.inputs_json)}</pre>
          <div className="log-label">Outputs</div>
          <pre className="log-pre">{prettyJson(l.outputs_json)}</pre>
        </div>
      )}
    </div>
  )
}

function IncidentReplay({
  inc,
  err,
  plan,
}: {
  inc: Incident | null
  err: string | null
  plan: SolveResponse['plan'] | null
}) {
  if (err) return <div className="error">{err}</div>
  if (!inc) return null

  const rows = inc.log ?? []

  return (
    <div className="card">
      <div className="blackbox-head">
        <h3>Black Box Replay · {inc.incident_id}</h3>
        {plan && (
          <button
            className="primary"
            onClick={() => downloadIncidentPDF(inc, plan)}
            title="Download flight recorder report as PDF"
          >
            ↓ Download PDF
          </button>
        )}
      </div>

      <div className="kv" style={{ marginBottom: 14 }}>
        <div className="k">Status</div>
        <div><span className="pill">{inc.status}</span></div>
        <div className="k">Opened</div>
        <div className="mono" style={{ fontSize: 12 }}>{inc.opened_at}</div>
        <div className="k">Closed</div>
        <div className="mono" style={{ fontSize: 12 }}>{inc.closed_at ?? '—'}</div>
        <div className="k">Technician</div>
        <div className="mono" style={{ fontSize: 12 }}>{inc.assigned_tech ?? '—'}</div>
        <div className="k">Total calls</div>
        <div className="mono" style={{ fontSize: 12 }}>{rows.length}</div>
      </div>

      <div className="log-hint">Click any row to expand inputs · outputs · timestamp</div>

      {rows.map(l => <LogRow key={l.id} l={l} />)}
    </div>
  )
}

function phaseTimingsFromIncident(inc: Incident | null): Record<string, number> | undefined {
  if (!inc?.log) return undefined
  const out: Record<string, number> = {}
  for (const row of inc.log) {
    // Skip the outer 'solution.solve' wrapper — it double-counts everything.
    if (row.agent === 'solution' && row.action === 'solve') continue
    out[row.phase] = (out[row.phase] ?? 0) + row.duration_ms
  }
  return out
}

function AlertToast({ last }: { last: AlertPayload | null }) {
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    if (!last) return
    setVisible(true)
    const t = setTimeout(() => setVisible(false), 9000)
    return () => clearTimeout(t)
  }, [last])
  if (!visible || !last) return null
  return (
    <div className="toast">
      <h4>{last.severity} · {last.machine_id}</h4>
      <div className="sub">{last.code} · incident {last.incident_id}</div>
      <p>{last.spoken_alert.slice(0, 220)}{last.spoken_alert.length > 220 ? '…' : ''}</p>
    </div>
  )
}

export default function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [plan, setPlan] = useState<SolveResponse | null>(null)
  const [activeScenario, setActiveScenario] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const stream = useAlertStream()
  const { inc, err: incErr } = useIncident(plan?.incident_id ?? null)
  const actualTimings = phaseTimingsFromIncident(inc)

  useEffect(() => {
    api.scenarios().then(r => setScenarios(r.scenarios)).catch(e => setErr(String(e)))
  }, [])

  const onPick = async (s: string) => {
    setBusy(true); setErr(null); setPlan(null); setActiveScenario(s)
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
      <ScenarioSidebar
        scenarios={scenarios}
        onPick={onPick}
        busy={busy}
        activeScenario={activeScenario}
      />
      <div className="main">
        {err && <div className="error">{err}</div>}

        {/* Pipeline is visible while busy AND after completion (with real timings) */}
        {(busy || plan) && (
          <PipelineProgress
            running={busy}
            actualTimings={!busy && plan ? actualTimings : undefined}
          />
        )}

        {!busy && !plan && !err && (
          <div style={{ marginTop: 16 }}>
            <Hero />
          </div>
        )}

        {plan && (
          <div className="grid" style={{ marginTop: 16 }}>
            <IncidentHeader data={plan} />
            <RigFloorplan
              machineId={plan.plan.machine_id}
              severity={plan.plan.severity}
              part={{
                name: plan.plan.part.part_name,
                code: plan.plan.part.part_code,
                location: plan.plan.part.location,
                availability: plan.plan.part.availability,
              }}
              tools={plan.plan.tools.map(t => ({
                name: t.tool_name,
                location: t.location,
                found: t.found_in_room_8,
              }))}
            />
            <AlertCard alert={plan.plan.alert} />
            <TelemetryChart
              scenario={activeScenario ?? ''}
              machineId={plan.plan.machine_id}
              faultTs={plan.event.detected_ts}
            />
            <NarrativeCard kb={plan.plan.kb} slm={plan.plan.slm} />
            <div className="grid cols-2">
              <PartCard part={plan.plan.part} />
              <TechnicianCard technician={plan.plan.technician} />
            </div>
            <ToolsCard tools={plan.plan.tools} />
            {plan.plan.broadcast && <BroadcastCard broadcast={plan.plan.broadcast} />}
            <ProcedureCard kb={plan.plan.kb} />
            <IncidentReplay inc={inc} err={incErr} plan={plan.plan} />
          </div>
        )}
      </div>
      <AlertToast last={stream.last} />
    </div>
  )
}
