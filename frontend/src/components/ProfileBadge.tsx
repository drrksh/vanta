import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { PROFILE_EVENT, userId } from '../lib/user'
import type { Profile } from '../types'

export function useProfile(): Profile | null {
  const [p, setP] = useState<Profile | null>(null)
  useEffect(() => {
    const load = () => api.profile(userId()).then(setP).catch(() => {})
    load()
    window.addEventListener(PROFILE_EVENT, load)
    return () => window.removeEventListener(PROFILE_EVENT, load)
  }, [])
  return p
}

export function ProfileBadge() {
  const p = useProfile()
  if (!p) return null
  return (
    <span className="mono inline-flex items-center gap-2 rounded border px-2 py-0.5 text-[11px]"
      title={`${p.worlds_solved} solved · ${p.experiments_run} experiments · ${p.witness_questions} witness questions`}
      style={{ borderColor: 'var(--line-bright)', color: 'var(--ink-dim)' }}>
      <span style={{ color: 'var(--structure)' }}>{p.level}</span>
      <span>{Math.round(p.rating)}</span>
    </span>
  )
}
