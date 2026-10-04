import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { Button, Chip, Label, Panel, Spinner } from '../components/ui'
import type { Archetype, WorldSummary } from '../types'

function userId(): string {
  let id = localStorage.getItem('vanta_uid')
  if (!id) { id = Math.random().toString(36).slice(2, 10); localStorage.setItem('vanta_uid', id) }
  return id
}

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
  const [difficulty, setDifficulty] = useState(0.45)
  const [worlds, setWorlds] = useState<WorldSummary[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.archetypes().then(setArchetypes).catch(() => {})
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
  async function del(id: string) { await api.remove(id); refresh() }

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
          and nothing is stored in advance. Read the code, find what's wrong, and submit a fix that holds.
        </p>
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
              {DIFFS.map((d) => (
                <ArchChip key={d.v} active={Math.abs(difficulty - d.v) < 0.01}
                  onClick={() => setDifficulty(d.v)} label={d.label} />
              ))}
            </div>
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
    <button onClick={onClick}
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
