import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { Button, Chip, Label, Panel, Spinner } from '../components/ui'
import { userId } from '../lib/user'
import type { CohortHostView } from '../types'

const VARIANT_LABEL: Record<string, string> = {
  pure_shortest_first: 'always runs the shortest job (long jobs can starve)',
  truncating_priority: 'integer-division priority score (ordering collapses)',
  no_close_check: 'ignores the time left before closing',
  linear_search_first_match: 'release matches stale holder ids on free slots',
  off_by_one_index: 'release computes the slot index with an off-by-one',
  no_double_checkout_guard: 'checkout lets one holder take two slots',
}

export default function CohortHostPage() {
  const { code = '' } = useParams<{ code: string }>()
  const nav = useNavigate()
  const uid = userId()
  const [view, setView] = useState<CohortHostView | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [updated, setUpdated] = useState<Date | null>(null)
  const [reveal, setReveal] = useState(false)
  const [copied, setCopied] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const load = useCallback(() => {
    api.cohortHost(code, uid).then((v) => { setView(v); setUpdated(new Date()); setError(null) })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [code, uid])

  useEffect(() => {
    load()
    const t = window.setInterval(load, 8000)
    return () => window.clearInterval(t)
  }, [load])

  if (error && !view) return (
    <Panel className="p-6" style={{ borderColor: 'var(--rejected)' }}>
      <p style={{ color: 'var(--rejected)' }}>{error}</p>
      <div className="mt-4"><Link to="/" className="text-[14px]" style={{ color: 'var(--structure)' }}>Back</Link></div>
    </Panel>
  )
  if (!view) return <div className="flex items-center gap-2" style={{ color: 'var(--ink-dim)' }}><Spinner /> Opening console…</div>

  const joinUrl = `${window.location.origin}/cohorts/${view.code}`
  const o = view.originality
  const started = view.members.filter((m) => m.submissions > 0).length

  async function copy() {
    try { await navigator.clipboard.writeText(joinUrl); setCopied(true); setTimeout(() => setCopied(false), 1500) }
    catch { /* clipboard blocked */ }
  }
  async function close() { await api.closeCohort(view!.code, uid); load() }
  async function del() { await api.deleteCohort(view!.code, uid); nav('/') }

  return (
    <div className="space-y-10">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <div className="mb-3 flex items-center gap-2">
            <Chip tone="signal">host console</Chip>
            <Chip tone={view.status === 'open' ? 'accepted' : 'neutral'}>{view.status}</Chip>
          </div>
          <h1 className="display text-[32px] leading-tight" style={{ fontWeight: 600 }}>{view.name}</h1>
          <p className="mt-2 text-[15px]" style={{ color: 'var(--ink-dim)' }}>
            {view.defect_class}{view.setting ? <> · set in {view.setting}</> : null} · difficulty {view.target_difficulty.toFixed(2)}
          </p>
          <div className="mt-3 text-[13px]" style={{ color: 'var(--ink-faint)' }}>
            {reveal ? (
              <span>Planted defect: <span style={{ color: 'var(--signal)' }}>{VARIANT_LABEL[view.defect_variant] ?? view.defect_variant}</span>{' '}
                <button className="underline" onClick={() => setReveal(false)}>hide</button></span>
            ) : (
              <button className="mono text-[12px] underline-offset-2 hover:underline" style={{ color: 'var(--structure)' }}
                onClick={() => setReveal(true)}>reveal the planted defect (host only, careful if projecting)</button>
            )}
          </div>
        </div>

        <Panel className="min-w-[300px] p-5">
          <Label>Join code</Label>
          <div className="mono text-[44px] leading-none tracking-[0.18em]" style={{ color: 'var(--structure)', fontWeight: 600 }}>
            {view.code}
          </div>
          <div className="mono mt-3 text-[12px]" style={{ color: 'var(--ink-dim)' }}>{joinUrl.replace(/^https?:\/\//, '')}</div>
          <div className="mono mt-1 text-[12px]" style={{ color: 'var(--ink-faint)' }}>Discord: /vanta join code:{view.code}</div>
          <div className="mt-3"><Button variant="ghost" onClick={copy}>{copied ? 'Copied' : 'Copy join link'}</Button></div>
        </Panel>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Tile k="joined" v={view.member_count} />
        <Tile k="submitted at least once" v={started} />
        <Tile k="solved" v={view.solved_count} tone="accepted" />
        <Tile k="distinct approaches" v={o.accepted ? `${o.distinct_approaches} / ${o.accepted}` : '—'}
          sub={o.accepted ? 'among accepted solutions' : 'waiting for accepted solutions'} />
      </div>

      <section className="grid gap-6 md:grid-cols-[1.1fr_1fr]">
        <div>
          <Label>Approaches among accepted solutions</Label>
          {o.accepted === 0 ? (
            <p className="text-[14px]" style={{ color: 'var(--ink-faint)' }}>
              Once people's fixes are accepted, VANTA groups them by what each person actually wrote:
              their own names normalized away, with their starter code subtracted.
            </p>
          ) : (
            <div className="space-y-2">
              {o.approaches.map((g, i) => (
                <Panel key={i} className="flex items-start gap-3 p-3">
                  <span className="mono mt-0.5 text-[11px]" style={{ color: 'var(--ink-faint)' }}>#{i + 1}</span>
                  <div className="flex flex-wrap gap-1.5">
                    {g.map((n) => <Chip key={n} tone="accepted">{n}</Chip>)}
                  </div>
                </Panel>
              ))}
            </div>
          )}
          {o.unchanged_from_starter.length > 0 && (
            <p className="mt-3 text-[13px]" style={{ color: 'var(--ink-faint)' }}>
              Submitted the starter essentially unchanged: {o.unchanged_from_starter.join(', ')}
            </p>
          )}
        </div>
        <div>
          <Label>Most similar pairs</Label>
          {o.pairs.length === 0 ? (
            <p className="text-[14px]" style={{ color: 'var(--ink-faint)' }}>Needs at least two changed submissions.</p>
          ) : (
            <div className="space-y-1.5">
              {o.pairs.slice(0, 8).map((p, i) => (
                <div key={i} className="grid grid-cols-[1fr_120px_44px] items-center gap-3 text-[13px]">
                  <span className="truncate" style={{ color: 'var(--ink-dim)' }}>{p.a} ↔ {p.b}</span>
                  <span className="h-1.5 rounded-full" style={{ background: 'var(--panel-2)' }}>
                    <span className="block h-1.5 rounded-full" style={{
                      width: `${Math.round(p.similarity * 100)}%`,
                      background: p.similarity >= 0.85 ? 'var(--signal)' : 'var(--structure)' }} />
                  </span>
                  <span className="mono text-right text-[12px]" style={{ color: p.similarity >= 0.85 ? 'var(--signal)' : 'var(--ink-faint)' }}>
                    {Math.round(p.similarity * 100)}%
                  </span>
                </div>
              ))}
              <p className="pt-2 text-[12px]" style={{ color: 'var(--ink-faint)' }}>
                Amber means the parts two people added are near-identical. That can happen honestly with a
                one-line fix, so check before you conclude anything.
              </p>
            </div>
          )}
        </div>
      </section>

      <section>
        <div className="mb-2 flex items-baseline justify-between">
          <Label>Members, in the order they joined</Label>
          {updated && <span className="mono text-[11px]" style={{ color: 'var(--ink-faint)' }}>
            live · updated {updated.toLocaleTimeString()}</span>}
        </div>
        {view.members.length === 0 ? (
          <Panel className="p-6"><p style={{ color: 'var(--ink-faint)' }}>Nobody has joined yet. Share the code.</p></Panel>
        ) : (
          <div className="overflow-x-auto rounded-lg border" style={{ borderColor: 'var(--line)' }}>
            <table className="w-full text-[13px]">
              <thead>
                <tr className="mono text-[10.5px] uppercase" style={{ background: 'var(--panel-2)', color: 'var(--ink-faint)', letterSpacing: '0.08em' }}>
                  {['member', 'their identifiers', 'status', 'submissions', 'best', 'experiments', 'witness qs'].map((h) =>
                    <th key={h} className="px-3 py-2 text-left font-normal">{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {view.members.map((m) => (
                  <tr key={m.user_id} className="border-t" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
                    <td className="px-3 py-2" style={{ color: 'var(--ink)' }}>{m.display_name}</td>
                    <td className="mono px-3 py-2 text-[11.5px]" style={{ color: 'var(--ink-faint)' }}>{m.identifiers.join(' · ')}</td>
                    <td className="px-3 py-2">
                      {!m.world_exists ? <Chip tone="neutral">world deleted</Chip>
                        : m.solved ? <Chip tone="accepted">solved</Chip>
                        : m.submissions ? <Chip tone="signal">working</Chip>
                        : <Chip tone="neutral">investigating</Chip>}
                    </td>
                    <td className="mono px-3 py-2" style={{ color: 'var(--ink-dim)' }}>{m.submissions}</td>
                    <td className="mono px-3 py-2" style={{ color: 'var(--ink-dim)' }}>{m.best ? `${m.best.passed}/${m.best.total}` : '—'}</td>
                    <td className="mono px-3 py-2" style={{ color: 'var(--ink-dim)' }}>{m.experiments}</td>
                    <td className="mono px-3 py-2" style={{ color: 'var(--ink-dim)' }}>{m.witness_questions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-2 text-[12px]" style={{ color: 'var(--ink-faint)' }}>
          Every row has different identifiers: VANTA refuses to give two members the same names, so a
          neighbour's code won't compile in your world.
        </p>
      </section>

      <section className="flex flex-wrap items-center gap-3 border-t pt-6" style={{ borderColor: 'var(--line)' }}>
        {view.status === 'open' && <Button variant="ghost" onClick={close}>Close to new members</Button>}
        {!confirmDelete ? (
          <Button variant="danger" onClick={() => setConfirmDelete(true)}>Delete cohort…</Button>
        ) : (
          <>
            <span className="text-[13px]" style={{ color: 'var(--rejected)' }}>
              This deletes the cohort and all {view.member_count} member worlds.
            </span>
            <Button variant="danger" onClick={del}>Yes, delete everything</Button>
            <Button variant="ghost" onClick={() => setConfirmDelete(false)}>Cancel</Button>
          </>
        )}
      </section>
    </div>
  )
}

function Tile({ k, v, sub, tone }: { k: string; v: string | number; sub?: string; tone?: 'accepted' }) {
  return (
    <Panel className="px-4 py-3">
      <div className="mono text-[10.5px] uppercase" style={{ color: 'var(--ink-faint)', letterSpacing: '0.1em' }}>{k}</div>
      <div className="display mt-1 text-[26px]" style={{ fontWeight: 600, color: tone === 'accepted' ? 'var(--accepted)' : 'var(--ink)' }}>{v}</div>
      {sub && <div className="text-[11.5px]" style={{ color: 'var(--ink-faint)' }}>{sub}</div>}
    </Panel>
  )
}
