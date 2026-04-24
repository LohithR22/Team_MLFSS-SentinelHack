import { useEffect, useState } from 'react'
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend,
} from 'recharts'
import { api } from '../api'

interface Row {
  Timestamp: string
  Machine_ID: string
  Pressure_PSI: number
  Temp_C: number
  Vibration_Hz: number
  Error_Code: string
}

interface Props {
  scenario: string
  machineId: string
  faultTs?: string | null
}

export function TelemetryChart({ scenario, machineId, faultTs }: Props) {
  const [rows, setRows] = useState<Row[] | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    setRows(null); setErr(null)
    api.telemetry(scenario, 500)
      .then(r => {
        const filtered = (r.rows as unknown as Row[])
          .filter(row => row.Machine_ID === machineId)
          .map(row => ({
            ...row,
            tick: row.Timestamp.slice(11, 16),  // HH:MM
          }))
        setRows(filtered as any)
      })
      .catch(e => setErr(String(e)))
  }, [scenario, machineId])

  if (err) return <div className="error">{err}</div>
  if (!rows) return <div className="loading">Loading telemetry…</div>

  const faultIdx = rows.findIndex(r => r.Error_Code && r.Error_Code !== '')
  const ramp = rows.slice(Math.max(0, faultIdx - 40))   // zoom on the slow burn

  return (
    <div className="card telemetry-card">
      <div className="telemetry-head">
        <h3>Telemetry · {machineId}</h3>
        <div className="telemetry-meta">
          <span className="pill mono">{rows.length} rows</span>
          {faultIdx >= 0 && <span className="pill no mono">fault @ row {faultIdx}</span>}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={ramp as any} margin={{ top: 8, right: 14, left: -10, bottom: 0 }}>
          <CartesianGrid stroke="#2a325b" strokeDasharray="2 4" />
          <XAxis dataKey="tick" tick={{ fill: '#8b93b5', fontSize: 11 }} axisLine={{ stroke: '#2a325b' }} />
          <YAxis tick={{ fill: '#8b93b5', fontSize: 11 }} axisLine={{ stroke: '#2a325b' }} />
          <Tooltip
            contentStyle={{ background: '#151a2e', border: '1px solid #2a325b', borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: '#8b93b5' }}
          />
          <Legend wrapperStyle={{ fontSize: 11, color: '#8b93b5' }} />
          <Line type="monotone" dataKey="Pressure_PSI" stroke="#4c8dff" strokeWidth={1.5} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="Temp_C"       stroke="#f7b500" strokeWidth={1.5} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="Vibration_Hz" stroke="#ff5f5f" strokeWidth={1.5} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
      {faultTs && (
        <div className="telemetry-footnote">
          Slow-burn window shown. Fault code fired at{' '}
          <span className="mono">{faultTs}</span> after sensors drifted out of normal range.
        </div>
      )}
    </div>
  )
}
