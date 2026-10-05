import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { Button, Chip, Label, Panel, Spinner } from '../components/ui'
import { userId } from '../lib/user'
import type { Cohort } from '../types'

export default function CohortJoinPage() {
  const { code = '' } = useParams<{ code: string }>()
  const nav = useNavigate()
  const uid = userId()
  const [cohort, setCohort] = useState<Cohort | null>(null)
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.cohort(code, uid).then(setCohort).catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [code, uid])

  async function join() {
    setBusy(true); setError(null)
    try {
      const r = await api.joinCohort(code, uid, name)
      nav(`/worlds/${r.member.world_id}`)
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); setBusy(false) }
  }

  if (error && !cohort) return (
    <Panel className="p-6" style={{ borderColor: 'var(--rejected)' }}>
      <p style={{ color: 'var(--rejected)' }}>{error}</p>
      <div className="mt-4"><Link to="/" className="text-[14px]" style={{ color: 'var(--structure)' }}>Back</Link></div>
    </Panel>
  )
  if (!cohort) return <div className="flex items-center gap-2" style={{ color: 'var(--ink-dim)' }}><Spinner /> Finding cohort…</div>

  const member = cohort.membership
  const isHost = cohort.host_id === uid
  return (
    <div className="mx-auto max-w-xl space-y-8">
      <div>
        <div className="mb-3 flex items-center gap-2">
          <Chip tone="signal">cohort · {cohort.code}</Chip>
          <Chip tone={cohort.status === 'open' ? 'accepted' : 'neutral'}>{cohort.status}</Chip>
        </div>
        <h1 className="display text-[32px] leading-tight" style={{ fontWeight: 600 }}>{cohort.name}</h1>
        <p className="mt-3 text-[15px]" style={{ color: 'var(--ink-dim)' }}>
          Everyone in this cohort gets the same defect, <b style={{ color: 'var(--ink)' }}>{cohort.archetype_title}</b>,
          in the same setting. Each person's system is evolved separately, with its own names and
          numbers. Your fix has to be yours: code written for someone else's world won't compile in yours.
        </p>
        <p className="mono mt-3 text-[12px]" style={{ color: 'var(--ink-faint)' }}>
          {cohort.member_count} joined · difficulty {cohort.target_difficulty.toFixed(2)}
        </p>
      </div>

      <Panel className="p-6">
        {member ? (
          <div className="space-y-4">
            <p className="text-[15px]">You're in as <b>{member.display_name}</b>.</p>
            <Button onClick={() => nav(`/worlds/${member.world_id}`)}>Open your world</Button>
          </div>
        ) : cohort.status !== 'open' ? (
          <p style={{ color: 'var(--ink-dim)' }}>This cohort is closed to new members.</p>
        ) : (
          <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); if (name.trim()) join() }}>
            <div>
              <Label>Your name, as the host will see it</Label>
              <input value={name} onChange={(e) => setName(e.target.value)} disabled={busy} maxLength={40}
                autoFocus placeholder="e.g. Asha R"
                className="vanta-focus w-full rounded-md border px-3 py-2 text-[15px]"
                style={{ borderColor: 'var(--line-bright)', background: 'var(--panel-2)', color: 'var(--ink)' }} />
            </div>
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={busy || !name.trim()}>
                {busy ? <><Spinner /> evolving your world…</> : 'Join and get my world'}
              </Button>
              {busy && <span className="mono text-[12px]" style={{ color: 'var(--ink-faint)' }}>proving it's broken, a few seconds</span>}
            </div>
            {error && <p className="text-[13px]" style={{ color: 'var(--rejected)' }}>{error}</p>}
          </form>
        )}
      </Panel>

      {isHost && (
        <Link to={`/cohorts/${cohort.code}/host`} className="mono text-[12px]" style={{ color: 'var(--structure)' }}>
          You host this cohort → open the host console
        </Link>
      )}
    </div>
  )
}
