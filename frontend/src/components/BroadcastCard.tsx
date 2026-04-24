import type { BroadcastInfo, BroadcastRecipient } from '../types'

const TIER_LABEL: Record<string, string> = {
  supervisor: 'Shift Supervisor',
  operations: 'Operations',
  safety:     'HSE Safety',
  executive:  'Executive',
  emergency:  'Emergency',
}

const TIER_ORDER: BroadcastRecipient['tier'][] = ['supervisor', 'operations', 'safety', 'executive', 'emergency']

const TIER_STYLE: Record<string, { color: string; bg: string }> = {
  supervisor: { color: '#4c8dff', bg: 'rgba(76,141,255,0.12)' },
  operations: { color: '#22d3ee', bg: 'rgba(34,211,238,0.12)' },
  safety:     { color: '#f7b500', bg: 'rgba(247,181,0,0.12)' },
  executive:  { color: '#b36cff', bg: 'rgba(179,108,255,0.12)' },
  emergency:  { color: '#ff5864', bg: 'rgba(255,88,100,0.14)' },
}

function ChannelChip({ c }: { c: string }) {
  const icon: Record<string, string> = {
    radio: '📻',   // semantic text only — no emoji rendering issues
    sat_phone: 'SAT',
    email: '@',
    pager: 'PGR',
    emergency_broadcast: 'EBS',
  }
  const label = icon[c] ?? c
  return <span className="broadcast-channel mono">{label === '📻' ? 'RADIO' : label}</span>
}

export function BroadcastCard({ broadcast }: { broadcast?: BroadcastInfo | null }) {
  if (!broadcast) return null   // guard against stale backend without broadcast data

  const recipients = broadcast.recipients ?? []
  const bySeverity: Record<string, BroadcastRecipient[]> = {}
  for (const r of recipients) {
    (bySeverity[r.tier] ??= []).push(r)
  }
  const tiersShown = TIER_ORDER.filter(t => bySeverity[t]?.length > 0)

  if ((broadcast.recipient_count ?? recipients.length) === 0) {
    return (
      <div className="card">
        <div className="bc-head">
          <h3>Escalation Chain</h3>
          <span className="pill ok">technician-only · no broadcast</span>
        </div>
        <p style={{ margin: 0, fontSize: 13, color: 'var(--text-dim)' }}>
          Maintenance-severity faults are dispatched to the assigned technician.
          No supervisors or executives are paged.
        </p>
      </div>
    )
  }

  return (
    <div className="card broadcast-card">
      <div className="bc-head">
        <h3>Escalation Broadcast Chain</h3>
        <div className="bc-meta">
          <span className="pill mono">{broadcast.recipient_count} recipients</span>
          <span className="pill mono">shift {broadcast.current_shift}</span>
        </div>
      </div>

      <div className="bc-tiers">
        {tiersShown.map((t, idx) => {
          const st = TIER_STYLE[t]
          const recs = bySeverity[t]
          return (
            <div key={t} className="bc-tier" style={{ borderLeft: `3px solid ${st.color}` }}>
              <div className="bc-tier-head" style={{ color: st.color }}>
                <span className="bc-tier-num">{idx + 1}</span>
                <span className="bc-tier-label">{TIER_LABEL[t]}</span>
                <span className="bc-tier-count">· {recs.length}</span>
              </div>
              <div className="bc-recipients">
                {recs.map(r => (
                  <div key={r.recipient_id} className="bc-recipient" style={{ background: st.bg }}>
                    <div className="bc-recipient-top">
                      <div>
                        <div className="bc-name">{r.name}</div>
                        <div className="bc-title">{r.title}{r.shift ? ` · Shift ${r.shift}` : ''}</div>
                      </div>
                      <div className="bc-delivered">
                        {r.delivered ? <span className="pill ok">✓ delivered</span> : <span className="pill warn">pending</span>}
                      </div>
                    </div>
                    <div className="bc-contact mono">
                      {r.contact_phone && <span>{r.contact_phone}</span>}
                      {r.contact_email && <span>·  {r.contact_email}</span>}
                      {r.radio_channel && <span>·  {r.radio_channel}</span>}
                    </div>
                    <div className="bc-channels">
                      {r.channels.map(c => <ChannelChip key={c} c={c} />)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
