import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useProfile } from '../components/ProfileBadge'
import { Button, Chip, Label, Panel, Spinner } from '../components/ui'
import { userId } from '../lib/user'
import type { Archetype, Cohort, WorldSummary } from '../types'

const DIFFS = [
  { v: 0.2, label: 'Gentle' },
  { v: 0.45, label: 'Standard' },
  { v: 0.7, label: 'Hard' },
  { v: 0.9, label: 'Brutal' },
]

export default function LandingPage() {
  const nav = useNavigate()
  const uid = userId()
  const [archetypes, setArchetypes] = useState<Archetype[]>([])
  const [archetype, setArchetype] = useState<string>('')
  // null = calibrated to this person's rating (the default)
  const [difficulty, setDifficulty] = useState<number | null>(null)
  const profile = useProfile()
  const [worlds, setWorlds] = useState<WorldSummary[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hosted, setHosted] = useState<Cohort[]>([])
  const [joinCode, setJoinCode] = useState('')
  const [cohortName, setCohortName] = useState('')
  const [cohortArch, setCohortArch] = useState('')
  const [cohortDiff, setCohortDiff] = useState(0.45)
  const [cohortBusy, setCohortBusy] = useState(false)
  const [cohortErr, setCohortErr] = useState<string | null>(null)

  useEffect(() => {
    api.archetypes().then(setArchetypes).catch(() => {})
    api.hostedCohorts(uid).then(setHosted).catch(() => {})
    refresh()
  }, [])
  function refresh() { api.list(uid).then(setWorlds).catch(() => {}) }

  async function generate() {
    setBusy(true); setError(null)
    try {
      const w = await api.create(uid, difficulty, archetype || undefined)
      nav(`/worlds/${w.world_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e)); setBusy(false)
    }
  }
  async function del(id: string) { await api.remove(id, uid); refresh() }
  async function hostCohort() {
    setCohortBusy(true); setCohortErr(null)
    try {
      const c = await api.createCohort(uid, cohortName, cohortArch || undefined, cohortDiff)
      nav(`/cohorts/${c.code}/host`)
    } catch (e) { setCohortErr(e instanceof Error ? e.message : String(e)); setCohortBusy(false) }
  }

  return (
    <div className="space-y-12">
      <section>
        <div className="mb-3 flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: 'var(--signal)' }} />
          <span className="mono text-[11px] uppercase" style={{ color: 'var(--signal)', letterSpacing: '0.14em' }}>
            system integrity: compromised
          </span>
        </div>
        <h1 className="display max-w-[20ch] text-[40px] leading-[1.05]" style={{ fontWeight: 600 }}>
          A broken system, built on demand, for you alone.
        </h1>
        <p className="mt-5 max-w-[62ch] text-[16px]" style={{ color: 'var(--ink-dim)' }}>
          Press generate and VANTA writes a small working system from scratch — its own names, its own
          numbers, and one real defect drawn at random. It then compiles and runs it to prove the defect
          is genuine and that more than one different fix can resolve it. No two generations are the same,
          and nothing is stored in advance. Question people who lived through a real run of it, design
          your own experiments, then submit a fix that holds.
        </p>
        <Link to="/guide" className="mono mt-4 inline-block text-[12px] underline-offset-2 hover:underline"
          style={{ color: 'var(--structure)' }}>
          New here? Read the 5-minute guide →
        </Link>
      </section>

      <Panel className="p-6">
        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <Label>Defect class</Label>
            <div className="flex flex-wrap gap-2">
              <ArchChip active={archetype === ''} onClick={() => setArchetype('')} label="Surprise me" />
              {archetypes.map((a) => (
                <ArchChip key={a.id} active={archetype === a.id}
                  onClick={() => setArchetype(a.id)} label={a.title} />
              ))}
            </div>
          </div>
          <div>
            <Label>Difficulty</Label>
            <div className="flex flex-wrap gap-2">
              <ArchChip active={difficulty === null} onClick={() => setDifficulty(null)}
                label={profile ? `Calibrated to you · ${profile.recommended_difficulty.toFixed(2)}` : 'Calibrated to you'} />
              {DIFFS.map((d) => (
                <ArchChip key={d.v} active={difficulty !== null && Math.abs(difficulty - d.v) < 0.01}
                  onClick={() => setDifficulty(d.v)} label={d.label} />
              ))}
            </div>
            {difficulty === null && profile && (
              <p className="mono mt-2 text-[11px]" style={{ color: 'var(--ink-faint)' }}>
                {profile.level} · rating {Math.round(profile.rating)} · {profile.worlds_solved} solved.
                Each fix you land pitches the next world a little harder.
              </p>
            )}
          </div>
        </div>
        <div className="mt-6 flex items-center gap-4">
          <Button onClick={generate} disabled={busy}>
            {busy ? <><Spinner /> compiling a system that has never existed…</> : 'Generate a world'}
          </Button>
          {busy && (
            <span className="mono text-[12px]" style={{ color: 'var(--ink-faint)' }}>
              evolving &amp; proving the defect — a few seconds
            </span>
          )}
        </div>
        {error && <p className="mt-3 text-[13px]" style={{ color: 'var(--rejected)' }}>{error}</p>}
      </Panel>

      <section>
        <div className="mb-3 flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: 'var(--structure)' }} />
          <span className="mono text-[11px] uppercase" style={{ color: 'var(--structure)', letterSpacing: '0.14em' }}>
            cohorts · one problem, a world per person
          </span>
        </div>
        <div className="grid gap-4 md:grid-cols-[1fr_1.4fr]">
          <Panel className="p-6">
            <Label>Join a cohort</Label>
            <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (joinCode.trim()) nav(`/cohorts/${joinCode.trim().toUpperCase()}`) }}>
              <input value={joinCode} onChange={(e) => setJoinCode(e.target.value.toUpperCase())} maxLength={6}
                placeholder="CODE" aria-label="Join code"
                className="vanta-focus mono w-full rounded-md border px-3 py-2 text-[18px] tracking-[0.2em]"
                style={{ borderColor: 'var(--line-bright)', background: 'var(--panel-2)', color: 'var(--ink)' }} />
              <Button type="submit" disabled={joinCode.trim().length < 6}>Join</Button>
            </form>
            <p className="mt-3 text-[13px]" style={{ color: 'var(--ink-faint)' }}>
              Everyone in a cohort faces the same defect, but each system is evolved separately with
              its own names and numbers.
            </p>
          </Panel>
          <Panel className="p-6">
            <Label>Host a cohort</Label>
            <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); if (cohortName.trim()) hostCohort() }}>
              <input value={cohortName} onChange={(e) => setCohortName(e.target.value)} maxLength={80}
                placeholder="e.g. CS1 lab, week 6" aria-label="Cohort name"
                className="vanta-focus w-full rounded-md border px-3 py-2 text-[14px]"
                style={{ borderColor: 'var(--line-bright)', background: 'var(--panel-2)', color: 'var(--ink)' }} />
              <div className="flex flex-wrap gap-2">
                <ArchChip active={cohortArch === ''} onClick={() => setCohortArch('')} label="Surprise everyone" />
                {archetypes.map((a) => (
                  <ArchChip key={a.id} active={cohortArch === a.id} onClick={() => setCohortArch(a.id)} label={a.title} />
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                {DIFFS.map((d) => (
                  <ArchChip key={d.v} active={Math.abs(cohortDiff - d.v) < 0.01} onClick={() => setCohortDiff(d.v)} label={d.label} />
                ))}
              </div>
              <div className="flex items-center gap-3">
                <Button type="submit" disabled={cohortBusy || !cohortName.trim()}>
                  {cohortBusy ? <><Spinner /> opening…</> : 'Open cohort'}
                </Button>
                {cohortErr && <span className="text-[13px]" style={{ color: 'var(--rejected)' }}>{cohortErr}</span>}
              </div>
            </form>
          </Panel>
        </div>
        {hosted.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="mono self-center text-[11px]" style={{ color: 'var(--ink-faint)' }}>You host:</span>
            {hosted.map((c) => (
              <button key={c.code} onClick={() => nav(`/cohorts/${c.code}/host`)}
                className="vanta-focus rounded-md border px-3 py-1.5 text-left text-[13px]"
                style={{ borderColor: 'var(--line-bright)', color: 'var(--ink-dim)' }}>
                <span className="mono" style={{ color: 'var(--structure)' }}>{c.code}</span> · {c.name} · {c.member_count} joined
              </button>
            ))}
          </div>
        )}
      </section>

      {worlds.length > 0 && (
        <section>
          <Label>Your open worlds</Label>
          <div className="space-y-2">
            {worlds.map((w) => (
              <Panel key={w.world_id} className="flex items-center justify-between p-4">
                <div>
                  <div className="display text-[15px]" style={{ fontWeight: 500 }}>{w.title}</div>
                  <div className="mt-1 flex items-center gap-2">
                    <Chip tone="structure">{w.world_id}</Chip>
                    <span className="mono text-[11px]" style={{ color: 'var(--ink-faint)' }}>
                      seed {w.seed}
                    </span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="ghost" onClick={() => nav(`/worlds/${w.world_id}`)}>Open</Button>
                  <Button variant="danger" onClick={() => del(w.world_id)}>Delete</Button>
                </div>
              </Panel>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function ArchChip({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button type="button" onClick={onClick}
      className="vanta-focus rounded-md border px-3 py-1.5 text-[13px] transition-all"
      style={{
        borderColor: active ? 'var(--structure)' : 'var(--line-bright)',
        background: active ? 'color-mix(in srgb, var(--structure) 14%, transparent)' : 'transparent',
        color: active ? 'var(--structure)' : 'var(--ink-dim)',
      }}>
      {label}
    </button>
  )
}
