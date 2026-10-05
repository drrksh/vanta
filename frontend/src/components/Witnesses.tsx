import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { userId } from '../lib/user'
import type { Witness, WitnessAnswer } from '../types'
import { EvidenceTable } from './EvidenceTable'
import { Spinner } from './ui'

type Turn = { q: string; a?: WitnessAnswer; err?: string; replay: boolean }

export function Witnesses({ worldId, code, starter }: { worldId: string; code: string; starter: string }) {
  const [witnesses, setWitnesses] = useState<Witness[] | null>(null)
  const [active, setActive] = useState<string>('')
  const [threads, setThreads] = useState<Record<string, Turn[]>>({})
  const [busy, setBusy] = useState(false)
  const [draft, setDraft] = useState('')
  const [replay, setReplay] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)
  const edited = code.trim() !== starter.trim()

  useEffect(() => {
    api.witnesses(worldId).then((w) => { setWitnesses(w); if (w[0]) setActive(w[0].key) })
      .catch(() => setWitnesses([]))
  }, [worldId])
  useEffect(() => { endRef.current?.scrollIntoView({ block: 'nearest' }) }, [threads, active])

  if (witnesses === null) return <div className="flex items-center gap-2 text-[13px]"
    style={{ color: 'var(--ink-faint)' }}><Spinner /> Finding people who were there…</div>
  if (witnesses.length === 0) return <p style={{ color: 'var(--ink-faint)' }}>No witnesses in this world.</p>

  const w = witnesses.find((x) => x.key === active) ?? witnesses[0]
  const thread = threads[w.key] ?? []
  const asked = new Set(thread.map((t) => t.q))

  async function ask(text: string, topic?: string) {
    if (busy || !text.trim()) return
    const useReplay = replay && edited
    const turn: Turn = { q: text, replay: useReplay }
    setThreads((t) => ({ ...t, [w.key]: [...(t[w.key] ?? []), turn] }))
    setBusy(true); setDraft('')
    try {
      const a = await api.ask(worldId, w.key, {
        question: topic ? undefined : text, topic, c_source: useReplay ? code : null, user_id: userId(),
      })
      turn.a = a
    } catch (e) { turn.err = e instanceof Error ? e.message : String(e) }
    setThreads((t) => ({ ...t, [w.key]: [...(t[w.key] ?? []).slice(0, -1), { ...turn }] }))
    setBusy(false)
  }

  return (
    <div className="grid gap-4 md:grid-cols-[220px_1fr]">
      <div className="flex gap-2 overflow-x-auto md:flex-col md:overflow-visible">
        {witnesses.map((x) => {
          const on = x.key === w.key
          const n = (threads[x.key] ?? []).length
          return (
            <button key={x.key} onClick={() => setActive(x.key)}
              className="vanta-focus min-w-[170px] rounded-md border px-3 py-2.5 text-left transition-colors md:min-w-0"
              style={{
                borderColor: on ? 'var(--structure)' : 'var(--line)',
                background: on ? 'color-mix(in srgb, var(--structure) 9%, var(--panel))' : 'var(--panel)',
              }}>
              <div className="flex items-center justify-between">
                <span className="display text-[14px]" style={{ fontWeight: 600, color: on ? 'var(--structure)' : 'var(--ink)' }}>
                  {x.name}
                </span>
                {n > 0 && <span className="mono text-[10px]" style={{ color: 'var(--ink-faint)' }}>{n}</span>}
              </div>
              <div className="mt-0.5 text-[12px] leading-snug" style={{ color: 'var(--ink-dim)' }}>{x.role}</div>
            </button>
          )
        })}
      </div>

      <div className="flex min-h-[380px] flex-col rounded-lg border" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
        <div className="border-b px-4 py-3" style={{ borderColor: 'var(--line)' }}>
          <div className="display text-[15px]" style={{ fontWeight: 600 }}>{w.name}</div>
          <div className="mono mt-0.5 text-[11px]" style={{ color: 'var(--ink-faint)' }}>
            can see: {w.vantage}
          </div>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4" style={{ maxHeight: 460 }}>
          {thread.length === 0 && (
            <p className="text-[13px]" style={{ color: 'var(--ink-faint)' }}>
              {w.name} lived through a real run of this system. Everything they say was produced by
              executing it, and they only know what they saw from where they stood.
            </p>
          )}
          {thread.map((t, i) => <TurnView key={i} t={t} name={w.name} />)}
          {busy && (
            <div className="flex items-center gap-2 text-[13px]" style={{ color: 'var(--ink-faint)' }}>
              <Spinner /> {replay && edited ? `${w.name} is living the period again under your code…` : 'thinking back…'}
            </div>
          )}
          <div ref={endRef} />
        </div>

        <div className="border-t px-4 py-3" style={{ borderColor: 'var(--line)' }}>
          <div className="mb-2.5 flex flex-wrap gap-1.5">
            {w.questions.map((q) => (
              <button key={q.topic} disabled={busy} onClick={() => ask(q.question, q.topic)}
                className="vanta-focus rounded-full border px-2.5 py-1 text-[12px] transition-opacity disabled:opacity-40"
                style={{
                  borderColor: 'var(--line-bright)',
                  color: asked.has(q.question) ? 'var(--ink-faint)' : 'var(--ink-dim)',
                }}>
                {q.question}
              </button>
            ))}
          </div>
          <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); ask(draft) }}>
            <input value={draft} onChange={(e) => setDraft(e.target.value)} disabled={busy}
              placeholder={`Ask ${w.name} something…`}
              className="vanta-focus flex-1 rounded-md border px-3 py-1.5 text-[13px]"
              style={{ borderColor: 'var(--line-bright)', background: 'var(--panel-2)', color: 'var(--ink)' }} />
            <button type="submit" disabled={busy || !draft.trim()}
              className="vanta-focus rounded-md px-3 text-[13px] font-medium disabled:opacity-40"
              style={{ background: 'var(--structure)', color: '#07131a' }}>Ask</button>
          </form>
          <label className="mt-2.5 flex cursor-pointer items-center gap-2 text-[12px]"
            style={{ color: edited ? 'var(--ink-dim)' : 'var(--ink-faint)' }}>
            <input type="checkbox" checked={replay && edited} disabled={!edited}
              onChange={(e) => setReplay(e.target.checked)} className="accent-[var(--structure)]" />
            Also have {w.name} live through the same period under my edited code
            {!edited && <span className="mono text-[11px]">(edit the source first)</span>}
          </label>
        </div>
      </div>
    </div>
  )
}

function TurnView({ t, name }: { t: Turn; name: string }) {
  const [open, setOpen] = useState(false)
  const a = t.a
  return (
    <div className="space-y-2">
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-lg px-3 py-1.5 text-[13px]"
          style={{ background: 'var(--panel-2)', color: 'var(--ink)' }}>{t.q}</div>
      </div>
      {t.err && <p className="text-[13px]" style={{ color: 'var(--rejected)' }}>{t.err}</p>}
      {a && (
        <div className="space-y-2">
          <div className={a.replay ? 'grid gap-2 md:grid-cols-2' : ''}>
            <Bubble label={a.replay ? 'the original system' : name} text={a.text}
              tone={a.topic === 'deflect' || a.topic === 'unknown' ? 'muted' : 'normal'} />
            {a.replay && (
              <Bubble label="under your code" text={a.replay.text}
                tone={a.replay.error ? 'error' : 'yours'} detail={a.replay.detail} />
            )}
          </div>
          {(a.evidence || a.replay?.evidence) && (
            <button onClick={() => setOpen(!open)} className="mono text-[11px] underline-offset-2 hover:underline"
              style={{ color: 'var(--structure)' }}>
              {open ? 'hide the record' : 'show the record behind this'}
            </button>
          )}
          {open && (
            <div className={a.replay?.evidence ? 'grid gap-2 md:grid-cols-2' : ''}>
              {a.evidence && <EvidenceTable evidence={a.evidence} />}
              {a.replay?.evidence && <EvidenceTable evidence={a.replay.evidence} />}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Bubble({ label, text, tone, detail }: {
  label: string; text: string; tone: 'normal' | 'muted' | 'yours' | 'error'; detail?: string
}) {
  const border = tone === 'yours' ? 'var(--accepted)' : tone === 'error' ? 'var(--rejected)' : 'var(--line-bright)'
  return (
    <div className="rounded-lg border-l-2 py-1 pl-3" style={{ borderColor: border }}>
      <div className="mono mb-0.5 text-[10px] uppercase" style={{ color: 'var(--ink-faint)', letterSpacing: '0.1em' }}>
        {label}
      </div>
      <p className="text-[14px] leading-relaxed" style={{ color: tone === 'muted' ? 'var(--ink-dim)' : 'var(--ink)' }}>
        {text}
      </p>
      {detail && (
        <pre className="mono mt-1.5 overflow-x-auto rounded p-2 text-[11px]"
          style={{ background: 'var(--field)', color: 'var(--rejected)' }}>{detail}</pre>
      )}
    </div>
  )
}
