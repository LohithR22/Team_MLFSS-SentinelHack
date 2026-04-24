import { Fragment, useEffect, useRef, useState } from 'react'

interface Stage {
  phase: string
  label: string
  hint: string
  /** Approx duration for the loading animation (ms) — mirrors typical warm-run timings. */
  ms: number
}

const STAGES: Stage[] = [
  { phase: 'detect',     label: 'Detect',      hint: 'reading sensor_data.db · finding fault',           ms: 250 },
  { phase: 'plan',       label: 'Plan · SLM',  hint: 'KB prefix routing → Llama-3.2-1B inference',       ms: 4500 },
  { phase: 'parts',      label: 'Parts',       hint: 'fault_codes.db → parts · availability + location', ms: 200 },
  { phase: 'tools',      label: 'Tools',       hint: '77 tools × Florence descriptions · room mapping',  ms: 200 },
  { phase: 'technician', label: 'Technician',  hint: 'technicians.db · severity + shift rule',           ms: 200 },
  { phase: 'alert',      label: 'Alert',       hint: 'live TTS (say / pyttsx3) · PA broadcast + WS',     ms: 1500 },
]

interface Props {
  running: boolean
  /** When provided, overrides the loading animation with real Black Box timings. */
  actualTimings?: Record<string, number>
}

export function PipelineProgress({ running, actualTimings }: Props) {
  const [currentIdx, setCurrentIdx] = useState(-1)
  const [elapsed, setElapsed] = useState(0)
  const startedAt = useRef<number | null>(null)

  // Drive the stage animation while loading
  useEffect(() => {
    if (!running) {
      setCurrentIdx(-1)
      setElapsed(0)
      startedAt.current = null
      return
    }

    startedAt.current = Date.now()
    let cancelled = false
    const timers: ReturnType<typeof setTimeout>[] = []

    let acc = 0
    for (let i = 0; i < STAGES.length; i++) {
      const t = setTimeout(() => {
        if (!cancelled) setCurrentIdx(i)
      }, acc)
      timers.push(t)
      acc += STAGES[i].ms
    }

    const ticker = setInterval(() => {
      if (startedAt.current != null) setElapsed(Date.now() - startedAt.current)
    }, 100)

    return () => {
      cancelled = true
      timers.forEach(clearTimeout)
      clearInterval(ticker)
    }
  }, [running])

  const showingActuals = !!actualTimings
  const doneIdx = showingActuals ? STAGES.length : currentIdx

  return (
    <div className="pipeline-wrap">
      <div className="pipeline-head">
        <div className="pipeline-title">
          <span className="pipeline-label">Agent Pipeline</span>
          {running && !showingActuals && (
            <span className="pipeline-elapsed mono">
              {(elapsed / 1000).toFixed(1)}s
            </span>
          )}
          {showingActuals && (
            <span className="pipeline-elapsed mono done">
              completed
            </span>
          )}
        </div>
        <div className="pipeline-sub">
          {running && !showingActuals && STAGES[Math.max(0, currentIdx)]
            ? STAGES[Math.max(0, currentIdx)].hint
            : 'Problem Generator → Solution → Parts → Tools → Technician → Alert'}
        </div>
      </div>

      <div className="pipeline">
        {STAGES.map((s, i) => {
          const state =
            showingActuals
              ? 'done'
              : i < doneIdx ? 'done' : i === doneIdx ? 'active' : 'pending'
          const ms = actualTimings?.[s.phase]
          return (
            <Fragment key={s.phase}>
              <div className={`stage stage-${state}`}>
                <div className="stage-node">
                  <div className="stage-ring" />
                  <div className="stage-core">
                    {state === 'done' ? (
                      <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden>
                        <path
                          d="M3 8.5l3.2 3.2L13 5"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.3"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    ) : (
                      <span className="stage-num">{i + 1}</span>
                    )}
                  </div>
                </div>
                <div className="stage-meta">
                  <div className="stage-label-text">{s.label}</div>
                  <div className="stage-time mono">
                    {ms != null ? `${ms}ms` : state === 'active' ? 'running…' : state === 'done' ? '' : '—'}
                  </div>
                </div>
              </div>
              {i < STAGES.length - 1 && (
                <div className={`stage-link link-${state === 'done' || (i + 1 <= doneIdx) ? 'filled' : state === 'active' ? 'flowing' : 'pending'}`}>
                  <div className="link-fill" />
                  <div className="link-dots" />
                </div>
              )}
            </Fragment>
          )
        })}
      </div>

      {running && !showingActuals && currentIdx >= 0 && (
        <div className="pipeline-hint">{STAGES[currentIdx]?.hint}</div>
      )}
    </div>
  )
}
