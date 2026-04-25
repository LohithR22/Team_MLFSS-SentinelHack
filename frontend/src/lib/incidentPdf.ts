import jsPDF from 'jspdf'
import autoTable from 'jspdf-autotable'
import type { Incident, SolveResponse } from '../types'

// ------------------------------ styling --------------------------------
const COL = {
  accent:    [76, 141, 255] as [number, number, number],
  magenta:   [179, 108, 255] as [number, number, number],
  ok:        [57, 171, 110] as [number, number, number],
  warn:      [198, 148, 20] as [number, number, number],
  danger:    [220, 70, 85] as [number, number, number],
  text:      [28, 34, 58] as [number, number, number],
  muted:     [110, 120, 150] as [number, number, number],
  dim:       [200, 204, 220] as [number, number, number],
  panel:     [247, 249, 253] as [number, number, number],
  headerBg:  [18, 24, 52] as [number, number, number],
}

function sevColor(severity: string): [number, number, number] {
  if (severity === 'Catastrophic') return COL.danger
  if (severity === 'Serious') return COL.warn
  if (severity === 'Maintenance') return COL.ok
  return COL.accent
}

function fmtTs(ts: string | null | undefined): string {
  if (!ts) return '—'
  return ts.replace('T', ' ').replace(/\+00:00$/, ' UTC').replace(/Z$/, ' UTC')
}

function truncate(s: string | null | undefined, n: number): string {
  if (!s) return '—'
  return s.length > n ? s.slice(0, n - 1) + '…' : s
}

// ------------------------------ builder --------------------------------

export function incidentPdfFilename(inc: Incident): string {
  return `${inc.incident_id}_flight_recorder.pdf`
}

export function downloadIncidentPDF(inc: Incident, plan: SolveResponse['plan']) {
  const doc = buildIncidentPDF(inc, plan)
  doc.save(incidentPdfFilename(inc))
}

export function buildIncidentPDFBlob(inc: Incident, plan: SolveResponse['plan']): Blob {
  const doc = buildIncidentPDF(inc, plan)
  return doc.output('blob')
}

function buildIncidentPDF(inc: Incident, plan: SolveResponse['plan']) {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' })
  const pageW = doc.internal.pageSize.getWidth()
  const pageH = doc.internal.pageSize.getHeight()
  const margin = 40
  const [sr, sg, sb] = sevColor(plan.severity)

  // ---------- Header band ----------
  doc.setFillColor(...COL.headerBg)
  doc.rect(0, 0, pageW, 80, 'F')

  // Accent strip
  doc.setFillColor(sr, sg, sb)
  doc.rect(0, 80, pageW, 4, 'F')

  // Brand mark (rounded square)
  doc.setFillColor(...COL.accent)
  doc.roundedRect(margin, 24, 32, 32, 6, 6, 'F')
  doc.setTextColor(255, 255, 255)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(13)
  doc.text('SH', margin + 16, 45, { align: 'center' })

  // Title
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(18)
  doc.setTextColor(255, 255, 255)
  doc.text('RigOrion', margin + 48, 38)

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(9)
  doc.setTextColor(180, 190, 220)
  doc.text('Oil Rig Maintenance AI · On-Rig Edge', margin + 48, 52)

  // Incident id + generated-at on right
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(11)
  doc.setTextColor(255, 255, 255)
  doc.text(inc.incident_id, pageW - margin, 38, { align: 'right' })
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(8)
  doc.setTextColor(180, 190, 220)
  doc.text(`Generated: ${new Date().toISOString().replace('T', ' ').slice(0, 19)} UTC`,
           pageW - margin, 52, { align: 'right' })

  // Severity chip
  let y = 108
  doc.setFillColor(sr, sg, sb)
  doc.roundedRect(margin, y - 14, 100, 20, 4, 4, 'F')
  doc.setTextColor(255, 255, 255)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(10)
  doc.text(plan.severity.toUpperCase(), margin + 50, y - 1, { align: 'center' })

  // Code + machine beside the chip
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(16)
  doc.setTextColor(...COL.text)
  doc.text(`${plan.code}  ·  ${plan.machine_id}`, margin + 112, y)

  y += 26

  // ---------- Summary panel ----------
  y = section(doc, y, margin, pageW, 'Incident Summary')

  const summaryRows: [string, string][] = [
    ['Fault code',    plan.code],
    ['Machine',       plan.machine_id],
    ['Severity',      plan.severity],
    ['KB file',       plan.kb.routed_file],
    ['Fault',         plan.kb.fault],
    ['First drift',   fmtTs(inc.first_drift_ts)],
    ['Detected',      fmtTs(inc.detected_ts)],
    ['Opened',        fmtTs(inc.opened_at)],
    ['Closed',        fmtTs(inc.closed_at)],
    ['Status',        inc.status],
  ]
  y = kvTable(doc, y, margin, pageW, summaryRows)

  // ---------- Dispatch panel ----------
  y = section(doc, y + 8, margin, pageW, 'Dispatch')

  const dispatchRows: [string, string][] = [
    ['Part',           `${plan.part.part_name} · ${plan.part.part_code}`],
    ['Availability',   plan.part.availability === 'Yes' ? 'In stock' :
                       plan.part.availability === 'No'  ? 'OUT OF STOCK · ESCALATE' :
                       plan.part.availability],
    ['Part location',  plan.part.location ?? '—'],
    ['Tools (count)',  `${plan.tools.length} required`],
    ['Tools in inv.',  `${plan.tools.filter(t => t.found_in_room_8).length} / ${plan.tools.length}`],
    ['Technician',     `${plan.technician.name}  ·  ${plan.technician.role} / ${plan.technician.specialization}`],
    ['Tech ID',        plan.technician.technician_id],
    ['Shift',          `${plan.technician.shift}  (${plan.technician.shift_hours})`],
    ['Radio',          plan.technician.radio_channel],
    ['Quarters',       plan.technician.quarters],
  ]
  y = kvTable(doc, y, margin, pageW, dispatchRows)

  // ---------- Voice alert ----------
  y = section(doc, y + 8, margin, pageW, 'Voice Alert · PA')
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(10)
  doc.setTextColor(...COL.text)
  y = wrapText(doc, plan.alert.spoken_alert, margin + 6, y + 6, pageW - 2 * margin - 12, 13)
  y += 6

  // ---------- SLM narrative ----------
  y = section(doc, y + 8, margin, pageW, 'SLM Narrative · Llama-3.2-1B')
  y = wrapText(doc, plan.slm.narrative, margin + 6, y + 6, pageW - 2 * margin - 12, 13)
  y += 6

  // ---------- Tools breakdown (as table) ----------
  y = section(doc, y + 8, margin, pageW, 'Tools Required')
  autoTable(doc, {
    startY: y + 4,
    head: [['Tool', 'Type', 'Location', 'Inventory']],
    body: plan.tools.map(t => [
      truncate(t.tool_name, 50),
      t.type ?? '—',
      truncate(t.location ?? '— (procure)', 38),
      t.found_in_room_8 ? 'YES' : 'PROCURE',
    ]),
    theme: 'grid',
    styles: { font: 'helvetica', fontSize: 8.5, cellPadding: 4, textColor: COL.text },
    headStyles: { fillColor: COL.accent, textColor: [255, 255, 255], fontStyle: 'bold' },
    alternateRowStyles: { fillColor: COL.panel },
    margin: { left: margin, right: margin },
  })
  y = (doc as any).lastAutoTable.finalY


  // ---------- Detailed steps ----------
  y = section(doc, y + 12, margin, pageW, 'Detailed Repair Steps')
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(9)
  doc.setTextColor(...COL.text)
  for (const [i, step] of plan.kb.detailed_steps.entries()) {
    if (y > pageH - margin - 60) { doc.addPage(); y = margin + 20 }
    const label = `${i + 1}.`
    doc.setFont('helvetica', 'bold')
    doc.text(label, margin + 6, y + 10)
    doc.setFont('helvetica', 'normal')
    y = wrapText(doc, step, margin + 28, y + 10, pageW - 2 * margin - 34, 11) + 4
  }

  // ---------- Agent pipeline timeline ----------
  // Force a new page so the wide timeline table has room — and so we never
  // collide with the tail of the detailed-steps section.
  doc.addPage()
  y = margin + 10
  y = section(doc, y, margin, pageW, 'Agent Pipeline Timeline')

  const logs = (inc.log ?? []).filter(l => !(l.agent === 'solution' && l.action === 'solve'))
  autoTable(doc, {
    startY: y + 4,
    head: [['#', 'Phase', 'Agent', 'Action', 'Status', 'Duration', 'Timestamp']],
    body: logs.map((l, i) => [
      String(i + 1),
      l.phase,
      l.agent,
      l.action,
      l.status,
      `${l.duration_ms} ms`,
      l.ts,
    ]),
    theme: 'grid',
    styles: { font: 'helvetica', fontSize: 8.5, cellPadding: 4, textColor: COL.text },
    headStyles: { fillColor: COL.headerBg, textColor: [255, 255, 255], fontStyle: 'bold' },
    alternateRowStyles: { fillColor: COL.panel },
    columnStyles: {
      0: { cellWidth: 22 },
      1: { cellWidth: 60, fontStyle: 'bold', textColor: COL.accent },
      4: { halign: 'center' },
      5: { halign: 'right', font: 'courier' },
      6: { font: 'courier', cellWidth: 120 },
    },
    didParseCell: (hook) => {
      if (hook.section === 'body' && hook.column.index === 4) {
        const v = String(hook.cell.raw)
        if (v === 'ok')    hook.cell.styles.textColor = COL.ok
        if (v === 'error') hook.cell.styles.textColor = COL.danger
      }
    },
    margin: { left: margin, right: margin },
  })
  y = (doc as any).lastAutoTable.finalY

  // ---------- Appendix: raw I/O ----------
  doc.addPage()
  let ay = margin + 10
  ay = section(doc, ay, margin, pageW, 'Appendix · Raw Agent I/O')

  for (const [i, l] of logs.entries()) {
    if (ay > pageH - margin - 80) { doc.addPage(); ay = margin + 20 }
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(10)
    doc.setTextColor(...COL.accent)
    doc.text(`#${i + 1}  [${l.phase}]  ${l.agent}.${l.action}`, margin + 6, ay + 12)
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(8)
    doc.setTextColor(...COL.muted)
    doc.text(`${l.duration_ms}ms · ${l.ts} · ${l.status}`, pageW - margin, ay + 12, { align: 'right' })
    ay += 22

    ay = codeBlock(doc, ay, margin, pageW, 'INPUTS',  l.inputs_json)
    ay = codeBlock(doc, ay, margin, pageW, 'OUTPUTS', l.outputs_json ?? '(none)')
    if (l.error_msg) ay = codeBlock(doc, ay, margin, pageW, 'ERROR', l.error_msg, true)
    ay += 10
  }

  // ---------- Footer on every page ----------
  const pageCount = doc.getNumberOfPages()
  for (let p = 1; p <= pageCount; p++) {
    doc.setPage(p)
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(8)
    doc.setTextColor(...COL.muted)
    doc.text('SentinelHack · Confidential · Generated on-rig', margin, pageH - 18)
    doc.text(`Page ${p} of ${pageCount}`, pageW - margin, pageH - 18, { align: 'right' })
  }

  return doc
}

// ---------------------------- helpers ------------------------------------

function section(doc: jsPDF, y: number, margin: number, pageW: number, title: string): number {
  // Title bar
  doc.setDrawColor(...COL.dim)
  doc.setLineWidth(0.5)
  doc.line(margin, y + 14, pageW - margin, y + 14)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(10)
  doc.setTextColor(...COL.accent)
  doc.text(title.toUpperCase(), margin, y + 10)
  return y + 22
}

function kvTable(doc: jsPDF, y: number, margin: number, pageW: number, rows: [string, string][]): number {
  autoTable(doc, {
    startY: y,
    body: rows,
    theme: 'plain',
    styles: { font: 'helvetica', fontSize: 9, cellPadding: 3, textColor: COL.text },
    columnStyles: {
      0: { cellWidth: 110, fontStyle: 'bold', textColor: COL.muted },
      1: { cellWidth: pageW - 2 * margin - 110, textColor: COL.text },
    },
    margin: { left: margin, right: margin },
  })
  return (doc as any).lastAutoTable.finalY
}

function wrapText(doc: jsPDF, text: string, x: number, y: number, maxW: number, lineH: number): number {
  const lines = doc.splitTextToSize(text, maxW)
  doc.text(lines, x, y)
  return y + lines.length * lineH
}

function codeBlock(doc: jsPDF, y: number, margin: number, pageW: number, label: string, body: string, danger = false): number {
  const pad = 6
  const maxW = pageW - 2 * margin - pad * 2
  doc.setFont('courier', 'normal')
  doc.setFontSize(7.5)
  const lines = doc.splitTextToSize(prettyJson(body), maxW)
  const h = lines.length * 9 + pad * 2 + 10
  const bg: [number, number, number] = danger ? [250, 236, 236] : [245, 247, 252]
  const border: [number, number, number] = danger ? COL.danger : COL.dim
  doc.setFillColor(bg[0], bg[1], bg[2])
  doc.setDrawColor(border[0], border[1], border[2])
  doc.roundedRect(margin, y, pageW - 2 * margin, h, 3, 3, 'FD')
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(7)
  doc.setTextColor(...(danger ? COL.danger : COL.muted))
  doc.text(label, margin + pad, y + 10)
  doc.setFont('courier', 'normal')
  doc.setFontSize(7.5)
  doc.setTextColor(...COL.text)
  doc.text(lines, margin + pad, y + 20)
  return y + h + 4
}

function prettyJson(s: string): string {
  try {
    const parsed = JSON.parse(s)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return s
  }
}
