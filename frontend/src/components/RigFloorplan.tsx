import { useMemo } from 'react'

export interface ToolEntry {
  name: string
  location: string | null
  found: boolean
}

interface Props {
  machineId: string                      // ENG-02 / PUM-01 / PL-03
  severity: string                       // Maintenance / Serious / Catastrophic
  part: {
    name: string | null
    code: string | null
    location: string | null
    availability: string                 // 'Yes' | 'No' | other
  }
  tools: ToolEntry[]
}

// Machine layout in the SVG (x, y, w, h). Positioned relative to each room
// so gaps are equal and all rows are centered.
//
//   Engine Room  {x:20,  w:260}  center=150   ENG-01/02 pair (78w, 14gap), ENG-03 centered below
//   Pump Room    {x:285, w:210}  center=390   PUM-01/02 pair, PUM-03 below
//   Pipeline     {x:530, w:250}  center=655   PL-01/02/03 in a row (70w, 14gap)
const MACHINES: Record<string, { x: number; y: number; w: number; h: number }> = {
  'ENG-01': { x:  65, y:  72, w: 78, h: 52 },
  'ENG-02': { x: 157, y:  72, w: 78, h: 52 },
  'ENG-03': { x: 111, y: 138, w: 78, h: 52 },
  'PUM-01': { x: 305, y:  72, w: 78, h: 52 },
  'PUM-02': { x: 397, y:  72, w: 78, h: 52 },
  'PUM-03': { x: 351, y: 138, w: 78, h: 52 },
  'PL-01':  { x: 536, y:  72, w: 70, h: 52 },
  'PL-02':  { x: 620, y:  72, w: 70, h: 52 },
  'PL-03':  { x: 704, y:  72, w: 70, h: 52 },
}

const ROOMS = {
  engine:   { x:  20, y:  30, w: 260, h: 180, label: 'Engine Room'     },
  pump:     { x: 285, y:  30, w: 210, h: 180, label: 'Pump Room'       },
  pipeline: { x: 530, y:  30, w: 250, h: 180, label: 'Pipeline Section'},
  room4:    { x:  20, y: 260, w: 220, h: 170, label: 'Room 4 · Parts'  },
  room7:    { x: 260, y: 260, w: 240, h: 170, label: 'Room 7 · Tools'  },
  room8:    { x: 520, y: 260, w: 260, h: 170, label: 'Room 8 · Tools'  },
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + '…' : s
}

type StorageKey = 'room4' | 'room7' | 'room8'

function rooms4_7_8_from(location: string | null): StorageKey | null {
  if (!location) return null
  if (/Room\s*-?\s*4/.test(location)) return 'room4'
  if (/Room\s*-?\s*7/.test(location)) return 'room7'
  if (/Room\s*-?\s*8/.test(location)) return 'room8'
  return null
}

function toolRoomsInUse(locs: (string | null)[]): Set<StorageKey> {
  const out = new Set<StorageKey>()
  for (const l of locs) {
    const r = rooms4_7_8_from(l)
    if (r === 'room7' || r === 'room8') out.add(r)
  }
  return out
}

function parentRoomOf(machineId: string): 'engine' | 'pump' | 'pipeline' | null {
  if (machineId.startsWith('ENG-')) return 'engine'
  if (machineId.startsWith('PUM-')) return 'pump'
  if (machineId.startsWith('PL-'))  return 'pipeline'
  return null
}

export function RigFloorplan({ machineId, severity, part, tools }: Props) {
  const fault = MACHINES[machineId]
  const faultRoom = parentRoomOf(machineId)
  const partRoom = rooms4_7_8_from(part.location)
  const partAvailable = part.availability === 'Yes'
  const toolLocations = useMemo(() => tools.map(t => t.location), [tools])
  const activeToolRooms = useMemo(() => toolRoomsInUse(toolLocations), [toolLocations])
  const toolsByRoom = useMemo(() => {
    const map: Record<StorageKey, ToolEntry[]> = { room4: [], room7: [], room8: [] }
    for (const t of tools) {
      const r = rooms4_7_8_from(t.location)
      if (r) map[r].push(t)
    }
    return map
  }, [tools])

  const severityColor =
    severity === 'Catastrophic' ? '#ff5864'
    : severity === 'Serious'    ? '#f7b500'
    : severity === 'Maintenance'? '#39d38c'
    : '#4c8dff'

  // Center of a room by key
  const center = (key: keyof typeof ROOMS) => {
    const r = ROOMS[key]; return { x: r.x + r.w / 2, y: r.y + r.h / 2 }
  }
  // Terminate routes at the TOP edge of the machine box (a few px above it)
  // so arrowheads don't overlap the machine's label text.
  const faultCenter = fault ? { x: fault.x + fault.w / 2, y: fault.y - 8 } : null

  return (
    <div className="card rig-card">
      <h3>Rig Floor Plan · Live Routing</h3>

      <svg
        viewBox="0 0 800 450"
        className="rig-svg"
        role="img"
        aria-label="Oil rig schematic with fault and supply routing"
      >
        <defs>
          {/* Glows */}
          <filter id="glow-red" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="glow-blue" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="glow-green" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>

          {/* Fill patterns */}
          <linearGradient id="room-bg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#1c2340" stopOpacity="0.85" />
            <stop offset="1" stopColor="#141833" stopOpacity="0.85" />
          </linearGradient>
          <linearGradient id="fault-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={severityColor} stopOpacity="0.3" />
            <stop offset="1" stopColor={severityColor} stopOpacity="0.05" />
          </linearGradient>
          <linearGradient id="part-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={partAvailable === false ? '#ff5864' : '#39d38c'} stopOpacity="0.25" />
            <stop offset="1" stopColor={partAvailable === false ? '#ff5864' : '#39d38c'} stopOpacity="0.05" />
          </linearGradient>
          <linearGradient id="tool-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#4c8dff" stopOpacity="0.22" />
            <stop offset="1" stopColor="#4c8dff" stopOpacity="0.05" />
          </linearGradient>

          {/* Arrowheads */}
          <marker id="arrow-part" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 Z" fill={partAvailable === false ? '#ff5864' : '#39d38c'} />
          </marker>
          <marker id="arrow-tool" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 Z" fill="#4c8dff" />
          </marker>
        </defs>

        {/* Background grid */}
        <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
          <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(100,120,200,0.07)" strokeWidth="0.5" />
        </pattern>
        <rect x="0" y="0" width="800" height="450" fill="url(#grid)" />

        {/* Corridor */}
        <rect x="20" y="220" width="760" height="30" rx="4" fill="rgba(76,141,255,0.04)" stroke="rgba(76,141,255,0.15)" strokeDasharray="4 6" />
        <text x="400" y="239" textAnchor="middle" fontSize="9" fill="rgba(166,176,212,0.55)" letterSpacing="2" fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace">CORRIDOR</text>

        {/* ───────── Rooms ───────── */}
        {(Object.entries(ROOMS) as [keyof typeof ROOMS, typeof ROOMS['engine']][]).map(([key, r]) => {
          const isFault = key === faultRoom
          const isPart = key === partRoom
          const isTool = (key === 'room7' || key === 'room8') && activeToolRooms.has(key)
          let fill = 'url(#room-bg)'
          let stroke = 'rgba(100,120,200,0.28)'
          let filter: string | undefined
          let className = 'rig-room'
          if (isFault) {
            fill = 'url(#fault-fill)'
            stroke = severityColor
            filter = 'url(#glow-red)'
            className += ' rig-room-fault'
          } else if (isPart) {
            fill = 'url(#part-fill)'
            stroke = partAvailable === false ? '#ff5864' : '#39d38c'
            filter = 'url(#glow-green)'
            className += partAvailable === false ? ' rig-room-part-missing' : ' rig-room-part'
          } else if (isTool) {
            fill = 'url(#tool-fill)'
            stroke = '#4c8dff'
            filter = 'url(#glow-blue)'
            className += ' rig-room-tool'
          }
          return (
            <g key={key} className={className}>
              <rect
                x={r.x} y={r.y} width={r.w} height={r.h}
                rx={8} ry={8}
                fill={fill}
                stroke={stroke}
                strokeWidth={isFault || isPart || isTool ? 1.8 : 1}
                filter={filter}
              />
              <text
                x={r.x + 10} y={r.y + 16}
                fontSize="10"
                fill="rgba(233,238,255,0.72)"
                letterSpacing="1.5"
                fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace"
              >
                {r.label.toUpperCase()}
              </text>

              {/* Part details inside Room 4 when it's the active part room */}
              {key === 'room4' && isPart && (
                <g fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace">
                  <text x={r.x + 10} y={r.y + 40} fontSize="11" fill="#fff" fontWeight="600">
                    ● {truncate(part.name ?? '—', 26)}
                  </text>
                  <text x={r.x + 10} y={r.y + 58} fontSize="10" fill="rgba(233,238,255,0.72)">
                    {part.code ?? ''}
                  </text>
                  <text
                    x={r.x + 10} y={r.y + 78} fontSize="10"
                    fill={partAvailable ? '#8eeaa8' : '#ff9aa4'}
                    fontWeight="700"
                    letterSpacing="1"
                  >
                    {partAvailable ? '◉ IN STOCK' : '⚠ OUT OF STOCK · ESCALATE'}
                  </text>
                  {part.location && (
                    <text x={r.x + 10} y={r.y + 96} fontSize="9" fill="rgba(166,176,212,0.72)">
                      {truncate(part.location, 30)}
                    </text>
                  )}
                </g>
              )}

              {/* Tool list inside Room 7 / Room 8 when they're active */}
              {(key === 'room7' || key === 'room8') && isTool && (
                <g fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace">
                  {toolsByRoom[key].slice(0, 8).map((t, i) => (
                    <text
                      key={i}
                      x={r.x + 10}
                      y={r.y + 38 + i * 14}
                      fontSize="10"
                      fill={t.found ? 'rgba(233,238,255,0.9)' : 'rgba(255,154,164,0.9)'}
                    >
                      {t.found ? '•' : '⚠'} {truncate(t.name, key === 'room8' ? 30 : 26)}
                    </text>
                  ))}
                  {toolsByRoom[key].length > 8 && (
                    <text
                      x={r.x + 10}
                      y={r.y + 38 + 8 * 14}
                      fontSize="9"
                      fill="rgba(166,176,212,0.65)"
                    >
                      + {toolsByRoom[key].length - 8} more
                    </text>
                  )}
                </g>
              )}
            </g>
          )
        })}

        {/* ───────── Machine boxes ───────── */}
        {Object.entries(MACHINES).map(([mid, m]) => {
          const isFault = mid === machineId
          return (
            <g key={mid} className={`rig-machine ${isFault ? 'rig-machine-fault' : ''}`}>
              <rect
                x={m.x} y={m.y} width={m.w} height={m.h}
                rx={6} ry={6}
                fill={isFault ? severityColor : 'rgba(36,44,82,0.85)'}
                fillOpacity={isFault ? 0.85 : 1}
                stroke={isFault ? severityColor : 'rgba(100,120,200,0.4)'}
                strokeWidth={isFault ? 2 : 1}
                filter={isFault ? 'url(#glow-red)' : undefined}
              />
              <text
                x={m.x + m.w / 2} y={m.y + m.h / 2 + 4}
                textAnchor="middle"
                fontSize="12"
                fontWeight={isFault ? 700 : 500}
                fill={isFault ? '#fff' : 'rgba(233,238,255,0.82)'}
                fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace"
              >
                {mid}
              </text>
              {isFault && (
                <>
                  <circle cx={m.x + m.w - 10} cy={m.y + 10} r="4" fill="#fff">
                    <animate attributeName="opacity" values="1;0.2;1" dur="1s" repeatCount="indefinite" />
                  </circle>
                  <circle cx={m.x + m.w - 10} cy={m.y + 10} r="10" fill={severityColor} fillOpacity="0.6">
                    <animate attributeName="r" values="4;14;4" dur="1.8s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.6;0;0.6" dur="1.8s" repeatCount="indefinite" />
                  </circle>
                </>
              )}
            </g>
          )
        })}

        {/* ───────── Routing arrows (parts + tools → fault machine) ───────── */}
        {faultCenter && partRoom && (
          <RouteLine
            from={center(partRoom)}
            to={faultCenter}
            color={partAvailable === false ? '#ff5864' : '#39d38c'}
            markerId="arrow-part"
            speed={1.2}
          />
        )}
        {faultCenter && [...activeToolRooms].map((rk, i) => (
          <RouteLine
            key={rk}
            from={center(rk)}
            to={faultCenter}
            color="#4c8dff"
            markerId="arrow-tool"
            speed={1.6}
            stagger={i * 0.4}
          />
        ))}
      </svg>

      {/* Legend */}
      <div className="rig-legend">
        <span className="legend-item">
          <span className="legend-swatch" style={{ background: severityColor }} />
          Fault · {machineId}
        </span>
        <span className="legend-item">
          <span className="legend-swatch" style={{ background: partAvailable === false ? '#ff5864' : '#39d38c' }} />
          Parts · {partRoom ? ROOMS[partRoom].label : '—'}
          {partAvailable === false && <em style={{ color: '#ff5864', marginLeft: 6 }}>(OOS)</em>}
        </span>
        <span className="legend-item">
          <span className="legend-swatch" style={{ background: '#4c8dff' }} />
          Tools · {[...activeToolRooms].map(r => ROOMS[r].label).join(' + ') || '—'}
        </span>
      </div>
    </div>
  )
}

// ----- Helper: animated flowing route line -----

interface RouteProps {
  from: { x: number; y: number }
  to: { x: number; y: number }
  color: string
  markerId: string
  speed: number    // seconds per cycle
  stagger?: number // delay offset in seconds
}

function RouteLine({ from, to, color, markerId, speed, stagger = 0 }: RouteProps) {
  // Curve the path — higher control point for natural look
  const midX = (from.x + to.x) / 2
  const midY = Math.min(from.y, to.y) - 40
  const d = `M ${from.x} ${from.y} Q ${midX} ${midY} ${to.x} ${to.y}`

  return (
    <g className="rig-route">
      {/* Static faint background path */}
      <path d={d} fill="none" stroke={color} strokeOpacity="0.25" strokeWidth="2" />
      {/* Animated dashed flow */}
      <path
        d={d} fill="none" stroke={color} strokeWidth="2.2"
        strokeLinecap="round"
        strokeDasharray="5 9"
        markerEnd={`url(#${markerId})`}
        filter="url(#glow-blue)"
      >
        <animate
          attributeName="stroke-dashoffset"
          from="0" to="-56"
          dur={`${speed}s`}
          begin={`${stagger}s`}
          repeatCount="indefinite"
        />
      </path>
    </g>
  )
}
