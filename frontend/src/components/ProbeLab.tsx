import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { userId } from '../lib/user'
import type { JobRow, JobTrace, PoolTrace, ProbeInfo, ProbeResult } from '../types'
import { Button, Label, Spinner } from './ui'

const PALETTE = ['#7fd1e8', '#58c7a6', '#b59cf0', '#e88fb0', '#9fb7d8', '#d9c36a', '#6fb3ff', '#c6a07a']

export function ProbeLab({ worldId, code, starter }: { worldId: string; code: string; starter: string }) {
  const [info, setInfo] = useState<ProbeInfo | null>(null)
  const [text, setText] = useState('')
  const [target, setTarget] = useState<'original' | 'yours'>('original')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [res, setRes] = useState<ProbeResult | null>(null)
  const [count, setCount] = useState(0)
  const edited = code.trim() !== starter.trim()

  useEffect(() => {
    api.probeInfo(worldId).then((i) => { setInfo(i); setText(JSON.stringify(i.template, null, 2)) })
      .catch((e) => setErr(String(e)))
  }, [worldId])

  async function run() {
    let scenario: unknown
    try { scenario = JSON.parse(text) } catch (e) {
      setErr(`That isn't valid JSON: ${e instanceof Error ? e.message : e}`); return
    }
    setBusy(true); setErr(null)
    try {
      const r = await api.probe(worldId, scenario, target === 'yours' && edited ? code : null, userId())
      setRes(r); setCount((c) => c + 1)
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)) }
    finally { setBusy(false) }
  }

  if (!info) return err ? <p style={{ color: 'var(--rejected)' }}>{err}</p>
    : <div className="flex items-center gap-2 text-[13px]" style={{ color: 'var(--ink-faint)' }}><Spinner /> Loading the lab…</div>

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-[1fr_300px]">
        <div>
          <Label>Experiment</Label>
          <textarea value={text} onChange={(e) => setText(e.target.value)} rows={12} spellCheck={false}
            className="vanta-focus mono w-full resize-y rounded-lg border p-3 text-[12.5px] leading-relaxed"
            style={{ borderColor: 'var(--line-bright)', background: 'var(--panel-2)', color: 'var(--ink)' }} />
        </div>
        <div className="space-y-4">
          <div>
            <Label>How to write one</Label>
            <p className="text-[13px] leading-relaxed" style={{ color: 'var(--ink-dim)' }}>{info.help}</p>
          </div>
          <div>
            <Label>Run it against</Label>
            <div className="inline-flex rounded-md border p-0.5" style={{ borderColor: 'var(--line-bright)' }}>
              {(['original', 'yours'] as const).map((t) => {
                const on = target === t
                const disabled = t === 'yours' && !edited
                return (
                  <button key={t} disabled={disabled} onClick={() => setTarget(t)}
                    className="vanta-focus rounded px-3 py-1 text-[12.5px] disabled:opacity-40"
                    style={{ background: on ? 'var(--panel-2)' : 'transparent',
                             color: on ? 'var(--structure)' : 'var(--ink-dim)' }}>
                    {t === 'original' ? 'the original system' : 'my edited code'}
                  </button>
                )
              })}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button onClick={run} disabled={busy}>
              {busy ? <><Spinner /> compiling &amp; running…</> : 'Run experiment'}
            </Button>
            <Button variant="ghost" onClick={() => setText(JSON.stringify(info.template, null, 2))}>Reset</Button>
          </div>
          {count > 0 && (
            <p className="mono text-[11px]" style={{ color: 'var(--ink-faint)' }}>
              {count} experiment{count === 1 ? '' : 's'} run in this session
            </p>
          )}
        </div>
      </div>

      {err && <p className="text-[13px]" style={{ color: 'var(--rejected)' }}>{err}</p>}

      {res && (
        <div className="space-y-4">
          <div className="mono text-[11px] uppercase" style={{ color: 'var(--ink-faint)', letterSpacing: '0.12em' }}>
            Result · ran {res.ran === 'original' ? 'the original system' : 'your code'}
          </div>
          {!res.ok && (
            <div className="rounded-md border p-3" style={{ borderColor: 'var(--rejected)' }}>
              <p className="text-[13px]" style={{ color: 'var(--rejected)' }}>
                {res.error === 'compile_error' ? 'It did not compile.'
                  : res.error === 'timeout' ? 'It ran too long on this experiment.'
                  : 'It crashed during the experiment.'}
              </p>
              {res.detail && <pre className="mono mt-2 overflow-x-auto text-[11px]" style={{ color: 'var(--ink-dim)' }}>{res.detail}</pre>}
            </div>
          )}
          {res.ok && res.trace.kind === 'job_queue' && <JobResult tr={res.trace as JobTrace} info={info} />}
          {res.ok && res.trace.kind === 'pool' && <PoolResult tr={res.trace as PoolTrace} info={info} />}
        </div>
      )}
    </div>
  )
}

function Stat({ k, v, warn }: { k: string; v: string | number; warn?: boolean }) {
  return (
    <div className="rounded-md border px-3 py-2" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
      <div className="mono text-[10px] uppercase" style={{ color: 'var(--ink-faint)', letterSpacing: '0.1em' }}>{k}</div>
      <div className="display mt-0.5 text-[18px]" style={{ fontWeight: 600, color: warn ? 'var(--signal)' : 'var(--ink)' }}>{v}</div>
    </div>
  )
}

function clock(t: number, L: number) {
  const d = Math.floor(t / L), m = t % L
  const hh = Math.floor((480 + m) / 60), mm = (480 + m) % 60
  return `d${d + 1} ${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`
}

function JobResult({ tr, info }: { tr: JobTrace; info: ProbeInfo }) {
  const L = tr.day_length, st = tr.stats
  const days = st.days_simulated
  const runs = useMemo(() => {
    const open: Record<number, number> = {}
    const out: { id: number; s: number; e: number }[] = []
    for (const ev of tr.events) {
      if (ev.kind === 'start') open[ev.id] = ev.t
      else if ((ev.kind === 'finish' || ev.kind === 'freed') && open[ev.id] !== undefined) {
        out.push({ id: ev.id, s: open[ev.id], e: ev.t }); delete open[ev.id]
      }
    }
    for (const [id, s] of Object.entries(open)) out.push({ id: Number(id), s, e: Math.min(days * L, s + L) })
    return out
  }, [tr, days, L])
  const byId = useMemo(() => Object.fromEntries(tr.jobs.map((j) => [j.id, j])), [tr])
  const refusals = tr.events.filter((e) => e.kind === 'refused_too_late' || e.kind.startsWith('invalid'))

  const entries = useMemo(() => {
    const g: Record<number, JobRow[]> = {}
    for (const j of tr.jobs) (g[j.entry ?? 0] ??= []).push(j)
    return Object.entries(g).map(([e, js]) => {
      const waits = js.map((j) => j.wait).filter((w): w is number => w !== null)
      return {
        entry: Number(e), n: js.length, minutes: js[0].minutes,
        finished: js.filter((j) => j.status === 'finished').length,
        never: js.filter((j) => j.status === 'never_started').length,
        rejected: js.filter((j) => j.status === 'rejected').length,
        avg: waits.length ? Math.round(waits.reduce((a, b) => a + b, 0) / waits.length) : null,
        max: waits.length ? Math.max(...waits) : null,
      }
    })
  }, [tr])

  const rowH = 20, W = 1000
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-6">
        <Stat k="busy" v={`${Math.round((100 * st.busy_minutes) / Math.max(1, st.open_minutes))}%`} />
        <Stat k="idle, work waiting" v={`${st.idle_while_waiting} min`} />
        <Stat k="too-late picks" v={st.too_late_attempts} warn={st.too_late_attempts > 0} />
        <Stat k="invalid picks" v={st.invalid_picks} warn={st.invalid_picks > 0} />
        <Stat k="longest queue" v={st.max_queue} />
        <Stat k="never started" v={tr.jobs.filter((j) => j.status === 'never_started').length}
          warn={tr.jobs.some((j) => j.status === 'never_started')} />
      </div>

      <div>
        <Label>What the {info.machine} ran, day by day</Label>
        <div className="rounded-lg border p-3" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
          <svg viewBox={`0 0 ${W + 44} ${days * rowH + 16}`} className="w-full" role="img"
            aria-label="Timeline of jobs run per day">
            {Array.from({ length: days }).map((_, d) => (
              <g key={d} transform={`translate(44, ${d * rowH})`}>
                <rect x={0} y={2} width={W} height={rowH - 4} fill="var(--panel-2)" rx={2} />
                <text x={-8} y={rowH / 2 + 4} textAnchor="end" fontSize={10} fill="var(--ink-faint)"
                  fontFamily="var(--mono)">day {d + 1}</text>
              </g>
            ))}
            {runs.map((r, i) => {
              const d = Math.floor(r.s / L)
              if (d >= days) return null
              const x = ((r.s % L) / L) * W, w = Math.max(0.8, ((r.e - r.s) / L) * W)
              const j = byId[r.id]
              const c = PALETTE[(j?.entry ?? 0) % PALETTE.length]
              return (
                <rect key={i} x={44 + x} y={d * rowH + 3} width={w} height={rowH - 6} fill={c} opacity={0.85}
                  stroke="var(--panel)" strokeWidth={0.6}>
                  <title>{`#${r.id} · ${j?.minutes} min · started ${clock(r.s, L)} · waited ${j?.wait ?? '?'} min`}</title>
                </rect>
              )
            })}
            {refusals.map((e, i) => {
              const d = Math.floor(e.t / L)
              if (d >= days) return null
              const x = 44 + ((e.t % L) / L) * W
              return <path key={`r${i}`} d={`M${x},${d * rowH + 1} l3,-4 h-6 z`} fill="var(--signal)">
                <title>{`${e.kind.replace(/_/g, ' ')} #${e.id} at ${clock(e.t, L)}`}</title></path>
            })}
            <text x={44} y={days * rowH + 12} fontSize={9} fill="var(--ink-faint)" fontFamily="var(--mono)">opening</text>
            <text x={44 + W} y={days * rowH + 12} fontSize={9} textAnchor="end" fill="var(--ink-faint)"
              fontFamily="var(--mono)">closing</text>
          </svg>
          {refusals.length > 0 && (
            <p className="mono mt-1 text-[11px]" style={{ color: 'var(--signal)' }}>
              ▲ = the scheduler picked something the {info.machine} refused to start
            </p>
          )}
        </div>
      </div>

      <div>
        <Label>By entry in your experiment</Label>
        <div className="overflow-x-auto rounded-md border" style={{ borderColor: 'var(--line)' }}>
          <table className="mono w-full text-[12px]">
            <thead><tr style={{ background: 'var(--panel-2)', color: 'var(--ink-faint)' }}>
              {['entry', 'jobs', 'length', 'finished', 'never started', 'rejected', 'avg wait', 'worst wait'].map((h) =>
                <th key={h} className="px-2.5 py-1.5 text-left font-normal">{h}</th>)}
            </tr></thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.entry} className="border-t" style={{ borderColor: 'var(--line)', color: 'var(--ink-dim)' }}>
                  <td className="px-2.5 py-1">
                    <span className="mr-1.5 inline-block h-2 w-2 rounded-sm" style={{ background: PALETTE[e.entry % PALETTE.length] }} />
                    jobs[{e.entry}]
                  </td>
                  <td className="px-2.5 py-1">{e.n}</td><td className="px-2.5 py-1">{e.minutes} min</td>
                  <td className="px-2.5 py-1">{e.finished}</td>
                  <td className="px-2.5 py-1" style={{ color: e.never ? 'var(--signal)' : undefined }}>{e.never}</td>
                  <td className="px-2.5 py-1">{e.rejected}</td>
                  <td className="px-2.5 py-1">{e.avg ?? '—'}</td><td className="px-2.5 py-1">{e.max ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function PoolResult({ tr, info }: { tr: PoolTrace; info: ProbeInfo }) {
  const P = tr.pool_size
  const W = 1000, H = 140
  const n = tr.ops.length
  const x = (k: number) => (n <= 1 ? 0 : (k / (n - 1)) * W)
  const y = (v: number) => H - (Math.max(0, Math.min(P, v)) / P) * (H - 10) - 4
  const line = (key: 'in_use' | 'ledger') => tr.ops.map((o, i) => `${i ? 'L' : 'M'}${x(i)},${y(o[key])}`).join(' ')
  const diverge = tr.ops.filter((o) => o.in_use !== o.ledger)
  const said = (o: PoolTrace['ops'][number]) => o.outcome === 'got_slot' ? `slot ${o.returned}`
    : o.outcome === 'denied' ? 'none available' : o.outcome === 'invalid_slot' ? `bad slot ${o.returned}`
    : o.outcome

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Stat k="operations" v={tr.stats.op_count} />
        <Stat k={`${info.unit}s in use (system)`} v={`${tr.stats.in_use} / ${P}`} />
        <Stat k="desk receipts say out" v={tr.stats.ledger} warn={tr.stats.ledger !== tr.stats.in_use} />
        <Stat k="steps where they differ" v={diverge.length} warn={diverge.length > 0} />
      </div>

      <div>
        <Label>In use vs. what the desk recorded, after each operation</Label>
        <div className="rounded-lg border p-3" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full" preserveAspectRatio="none" style={{ height: 150 }}>
            <line x1={0} x2={W} y1={y(P)} y2={y(P)} stroke="var(--line-bright)" strokeDasharray="4 4" />
            <path d={line('ledger')} fill="none" stroke="var(--signal)" strokeWidth={1.5} strokeDasharray="5 3" />
            <path d={line('in_use')} fill="none" stroke="var(--structure)" strokeWidth={1.8} />
          </svg>
          <div className="mono mt-1 flex gap-4 text-[11px]" style={{ color: 'var(--ink-faint)' }}>
            <span><span style={{ color: 'var(--structure)' }}>━</span> marked in use by the pool</span>
            <span><span style={{ color: 'var(--signal)' }}>╍</span> checkouts granted − returns accepted</span>
            <span>┄ capacity ({P})</span>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-[1fr_1.2fr]">
        <div>
          <Label>The pool at the end</Label>
          <div className="grid gap-1.5" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(54px, 1fr))' }}>
            {tr.slots.map((s) => (
              <div key={s.slot} className="mono rounded border px-1.5 py-1 text-[10.5px]"
                title={s.in_use ? `slot ${s.slot}: held by ${s.holder}` : `slot ${s.slot}: free (last holder ${s.holder})`}
                style={{ borderColor: s.in_use ? 'var(--structure)' : 'var(--line)',
                         background: s.in_use ? 'color-mix(in srgb, var(--structure) 14%, transparent)' : 'transparent',
                         color: s.in_use ? 'var(--ink)' : 'var(--ink-faint)' }}>
                <div>#{s.slot}</div>
                <div className="truncate">{s.in_use ? s.holder : 'free'}</div>
              </div>
            ))}
          </div>
        </div>
        <div>
          <Label>Operation log</Label>
          <div className="max-h-[300px] overflow-auto rounded-md border" style={{ borderColor: 'var(--line)' }}>
            <table className="mono w-full text-[11.5px]">
              <thead className="sticky top-0"><tr style={{ background: 'var(--panel-2)', color: 'var(--ink-faint)' }}>
                {['#', 'call', 'holder', 'system said', 'in use', 'receipts'].map((h) =>
                  <th key={h} className="px-2 py-1.5 text-left font-normal">{h}</th>)}
              </tr></thead>
              <tbody>
                {tr.ops.slice(0, 400).map((o) => (
                  <tr key={o.k} className="border-t" style={{ borderColor: 'var(--line)',
                    color: 'var(--ink-dim)', background: o.in_use !== o.ledger ? 'color-mix(in srgb, var(--signal) 8%, transparent)' : undefined }}>
                    <td className="px-2 py-0.5">{o.k + 1}</td>
                    <td className="px-2 py-0.5">{o.op === 'checkout' ? info.checkout_func : info.release_func}</td>
                    <td className="px-2 py-0.5">{o.holder}</td><td className="px-2 py-0.5">{said(o)}</td>
                    <td className="px-2 py-0.5">{o.in_use}</td><td className="px-2 py-0.5">{o.ledger}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
