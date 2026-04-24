import type { MaintenanceInfo } from '../types'

const PRIORITY_STYLE: Record<string, { color: string; bg: string; label: string }> = {
  normal:   { color: '#8eeaa8', bg: 'rgba(57,211,140,0.12)',  label: 'NORMAL · monitor' },
  routine:  { color: '#4c8dff', bg: 'rgba(76,141,255,0.14)',  label: 'ROUTINE · schedule' },
  urgent:   { color: '#f7b500', bg: 'rgba(247,181,0,0.14)',   label: 'URGENT · plan overhaul' },
  critical: { color: '#ff5864', bg: 'rgba(255,88,100,0.16)',  label: 'CRITICAL · take offline' },
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return iso.replace('T', ' ').replace(/\+00:00$/, ' UTC').replace(/Z$/, ' UTC')
}

function fmtInterval(h: number | null): string {
  if (h == null) return '—'
  if (h < 1) return `${Math.round(h * 60)} min`
  if (h < 48) return `${h.toFixed(1)} h`
  return `${(h / 24).toFixed(1)} d`
}

export function MaintenanceCard({ maintenance }: { maintenance: MaintenanceInfo }) {
  const { occurrence_count, priority, recurring } = maintenance
  const style = PRIORITY_STYLE[priority] ?? PRIORITY_STYLE.normal

  return (
    <div className="card maint-card" style={{ borderColor: style.color }}>
      <div className="maint-head">
        <h3>Preventive Maintenance</h3>
        <span
          className="maint-priority mono"
          style={{ color: style.color, background: style.bg, borderColor: style.color }}
        >
          {style.label}
        </span>
      </div>

      {!recurring ? (
        <p style={{ margin: 0, fontSize: 13, color: 'var(--text-dim)' }}>
          First occurrence for this fault on {maintenance.machine_id}. No preventive
          schedule needed yet — the Maintenance Agent will watch for repeats.
        </p>
      ) : (
        <>
          <p style={{ margin: '0 0 14px', fontSize: 14, color: 'var(--text)' }}>
            {maintenance.recommendation}
          </p>
          <div className="maint-stats">
            <div>
              <div className="k">Occurrences</div>
              <div className="big mono" style={{ color: style.color }}>×{occurrence_count}</div>
            </div>
            <div>
              <div className="k">Avg interval</div>
              <div className="big mono">{fmtInterval(maintenance.avg_interval_hours)}</div>
            </div>
            <div>
              <div className="k">Next service by</div>
              <div className="big mono" style={{ fontSize: 14 }}>{fmtDate(maintenance.next_service_at)}</div>
            </div>
          </div>

          <div className="maint-hist-label">History · latest first</div>
          <div className="maint-hist">
            {[...maintenance.history].reverse().map((h, i) => (
              <div className="maint-hist-row" key={i}>
                <span className="mono" style={{ color: 'var(--accent)' }}>{h.incident_id}</span>
                <span className="mono" style={{ color: 'var(--muted)' }}>{fmtDate(h.opened_at)}</span>
                <span className={`sev-badge ${h.severity}`}>{h.severity}</span>
                <span className="pill mono">{h.status}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
