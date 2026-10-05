import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { ProbeLab } from '../components/ProbeLab'
import { Button, Chip, Label, Panel, Spinner } from '../components/ui'
import { Witnesses } from '../components/Witnesses'
import { notifyProfileChanged, userId } from '../lib/user'
import type { SubmitResultWithRating, WorldFull } from '../types'

export default function WorldPage() {
  const { id } = useParams<{ id: string }>()
  const nav = useNavigate()
  const [world, setWorld] = useState<WorldFull | null>(null)
  const [code, setCode] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<SubmitResultWithRating | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<'witnesses' | 'probe'>('witnesses')

  useEffect(() => {
    if (!id) return
    api.get(id).then((w) => { setWorld(w); setCode(w.starter_source.trim()) })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [id])

  async function submit() {
    if (!id) return
    setSubmitting(true); setResult(null)
    try { setResult(await api.submit(id, code, userId())); notifyProfileChanged() }
    catch (e) { setError(e instanceof Error ? e.message : String(e)) }
    finally { setSubmitting(false) }
  }

  if (error) return (
    <Panel className="p-6" style={{ borderColor: 'var(--rejected)' }}>
      <p style={{ color: 'var(--rejected)' }}>{error}</p>
      <div className="mt-4"><Button variant="ghost" onClick={() => nav('/')}>Back</Button></div>
    </Panel>
  )
  if (!world) return (
    <div className="flex items-center gap-2" style={{ color: 'var(--ink-dim)' }}>
      <Spinner /> Loading world…
    </div>
  )

  // Map test results onto the requirements checklist (best-effort by index,
  // since each requirement corresponds to the mandatory property set).
  const tests = result?.tests ?? []

  return (
    <div className="space-y-8">
      <div>
        <div className="mb-2 flex items-center gap-2">
          <Chip tone="structure">{world.world_id}</Chip>
          <span className="mono text-[11px]" style={{ color: 'var(--ink-faint)' }}>seed {world.seed}</span>
        </div>
        <h1 className="display text-[28px]" style={{ fontWeight: 600 }}>{world.title}</h1>
      </div>

      <section>
        <Label>Situation</Label>
        <p className="max-w-[70ch] text-[16px]">{world.briefing}</p>
      </section>

      <section className="grid gap-8 md:grid-cols-[1fr_1fr]">
        <div>
          <Label>Your task</Label>
          <p className="text-[15px]" style={{ color: 'var(--ink-dim)' }}>{world.specification}</p>
          <Panel className="mt-3 px-3 py-2">
            <code className="mono text-[13px]" style={{ color: 'var(--structure)' }}>
              {world.function_signature}
            </code>
          </Panel>
          <p className="mt-3 mono text-[12px]" style={{ color: 'var(--ink-faint)' }}>
            {world.sample_input_description}
          </p>
        </div>
        <div>
          <Label>Requirements — must all hold</Label>
          <ul className="space-y-2">
            {world.mandatory_properties.map((p, i) => {
              const t = tests[i]
              const mark = !result ? '·' : t ? (t.passed ? '✓' : '✗') : '·'
              const col = !result || !t ? 'var(--ink-faint)'
                : t.passed ? 'var(--accepted)' : 'var(--rejected)'
              return (
                <li key={i} className="flex gap-2.5 text-[14px]">
                  <span className="mono mt-0.5" style={{ color: col }}>{mark}</span>
                  <span style={{ color: 'var(--ink-dim)' }}>{p}</span>
                </li>
              )
            })}
          </ul>
        </div>
      </section>

      <section>
        <div className="mb-3 flex items-end justify-between gap-4">
          <div>
            <Label>Investigate</Label>
            <p className="max-w-[64ch] text-[14px]" style={{ color: 'var(--ink-dim)' }}>
              Nobody here knows the answer, and nothing is scripted. Talk to people who lived through a
              real run of this system, or design your own experiment and run it.
            </p>
          </div>
          <div className="inline-flex shrink-0 rounded-md border p-0.5" style={{ borderColor: 'var(--line-bright)' }}>
            {([['witnesses', 'Witnesses'], ['probe', 'Probe lab']] as const).map(([k, label]) => (
              <button key={k} onClick={() => setTab(k)}
                className="vanta-focus rounded px-3.5 py-1.5 text-[13px]"
                style={{ background: tab === k ? 'var(--panel-2)' : 'transparent',
                         color: tab === k ? 'var(--structure)' : 'var(--ink-dim)' }}>
                {label}
              </button>
            ))}
          </div>
        </div>
        <div className={tab === 'witnesses' ? '' : 'hidden'}>
          <Witnesses worldId={world.world_id} code={code} starter={world.starter_source} />
        </div>
        <div className={tab === 'probe' ? '' : 'hidden'}>
          <ProbeLab worldId={world.world_id} code={code} starter={world.starter_source} />
        </div>
      </section>

      <section>
        <Label>{code.trim() === world.starter_source.trim()
          ? 'Source — this is the current, broken behavior' : 'Source — your edited version'}</Label>
        <textarea
          value={code} onChange={(e) => setCode(e.target.value)} rows={18} spellCheck={false}
          className="vanta-focus mono w-full resize-y rounded-lg border p-4 text-[13px] leading-relaxed"
          style={{ borderColor: 'var(--line-bright)', background: 'var(--panel-2)', color: 'var(--ink)' }}
        />
        <div className="mt-4 flex items-center gap-3">
          <Button onClick={submit} disabled={submitting}>
            {submitting ? <><Spinner /> compiling &amp; running hidden tests…</> : 'Submit fix'}
          </Button>
          <Button variant="ghost" onClick={() => setCode(world.starter_source.trim())}>Reset to original</Button>
        </div>
      </section>

      {result && (
        <Panel className="p-5"
          style={{ borderColor: result.verdict === 'accepted' ? 'var(--accepted)' : 'var(--rejected)' }}>
          <div className="flex items-center gap-3">
            <Chip tone={result.verdict === 'accepted' ? 'accepted' : 'rejected'}>
              {result.verdict === 'accepted' ? 'ACCEPTED' : 'REJECTED'}
            </Chip>
            <span className="text-[14px]" style={{ color: 'var(--ink-dim)' }}>
              {result.verdict === 'accepted'
                ? 'Your fix satisfies every required property.'
                : result.reason === 'compile_error' ? 'Your code did not compile.'
                : result.reason === 'timeout' ? 'Your code ran too long.'
                : 'Your fix does not satisfy every required property yet.'}
            </span>
          </div>
          {result.rating && result.rating.counted && (
            <p className="mono mt-3 text-[12px]" style={{ color: 'var(--ink-dim)' }}>
              rating {Math.round(result.rating.before)} → {Math.round(result.rating.after)}{' '}
              <span style={{ color: result.rating.after >= result.rating.before ? 'var(--accepted)' : 'var(--rejected)' }}>
                ({result.rating.after >= result.rating.before ? '+' : ''}
                {Math.round(result.rating.after - result.rating.before)})
              </span>
              {result.verdict === 'accepted' && ' · your next generated world will be pitched higher'}
            </p>
          )}
          {result.detail && (
            <pre className="mono mt-3 overflow-x-auto rounded p-3 text-[12px]"
              style={{ background: 'var(--field)', color: 'var(--rejected)' }}>
              {result.detail}
            </pre>
          )}
        </Panel>
      )}
    </div>
  )
}
