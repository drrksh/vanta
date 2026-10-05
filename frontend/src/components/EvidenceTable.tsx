import type { Evidence } from '../types'

export function EvidenceTable({ evidence, max = 30 }: { evidence: Evidence; max?: number }) {
  const rows = evidence.rows.slice(0, max)
  const hidden = (evidence.total ?? evidence.rows.length) - rows.length
  return (
    <div className="overflow-x-auto rounded-md border" style={{ borderColor: 'var(--line)' }}>
      <table className="mono w-full border-collapse text-[11.5px]">
        <thead>
          <tr style={{ background: 'var(--panel-2)' }}>
            {evidence.columns.map((c) => (
              <th key={c} className="px-2.5 py-1.5 text-left font-normal uppercase"
                style={{ color: 'var(--ink-faint)', letterSpacing: '0.08em' }}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t" style={{ borderColor: 'var(--line)' }}>
              {r.map((cell, j) => (
                <td key={j} className="whitespace-nowrap px-2.5 py-1" style={{ color: cellTone(cell) }}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {hidden > 0 && (
        <div className="mono border-t px-2.5 py-1 text-[11px]"
          style={{ borderColor: 'var(--line)', color: 'var(--ink-faint)' }}>
          + {hidden} more rows
        </div>
      )}
    </div>
  )
}

function cellTone(cell: string | number): string {
  const s = String(cell)
  if (s === 'never started') return 'var(--signal)'
  return 'var(--ink-dim)'
}
