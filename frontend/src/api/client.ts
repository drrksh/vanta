import type {
  Archetype, Profile, ProbeInfo, ProbeResult, SubmitResultWithRating, Witness, WitnessAnswer,
  WorldFull, WorldSummary,
} from '../types'

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const resp = await fetch(path, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!resp.ok) {
    let detail: unknown = resp.statusText
    try { detail = (await resp.json()).detail } catch { /* no body */ }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  if (resp.status === 204) return undefined as T
  return (await resp.json()) as T
}

export const api = {
  archetypes: () => req<Archetype[]>('GET', '/api/archetypes'),
  /** target_difficulty null = calibrated to this user's rating. */
  create: (created_by: string, target_difficulty: number | null, archetype_id?: string) =>
    req<WorldFull & { calibrated: boolean }>('POST', '/api/worlds',
      { created_by, target_difficulty, archetype_id }),
  list: (created_by: string) =>
    req<WorldSummary[]>('GET', `/api/worlds?created_by=${encodeURIComponent(created_by)}`),
  get: (id: string) => req<WorldFull>('GET', `/api/worlds/${id}`),
  submit: (id: string, c_source: string, user_id?: string) =>
    req<SubmitResultWithRating>('POST', `/api/worlds/${id}/submit`, { c_source, user_id }),
  remove: (id: string) => req<{ deleted: string }>('DELETE', `/api/worlds/${id}`),

  probeInfo: (id: string) => req<ProbeInfo>('GET', `/api/worlds/${id}/probe`),
  probe: (id: string, scenario: unknown, c_source: string | null, user_id?: string) =>
    req<ProbeResult>('POST', `/api/worlds/${id}/probe`, { scenario, c_source, user_id }),
  witnesses: (id: string) => req<Witness[]>('GET', `/api/worlds/${id}/witnesses`),
  ask: (id: string, key: string,
        body: { question?: string; topic?: string; c_source?: string | null; user_id?: string }) =>
    req<WitnessAnswer>('POST', `/api/worlds/${id}/witnesses/${key}/ask`, body),
  profile: (user_id: string) => req<Profile>('GET', `/api/profiles/${encodeURIComponent(user_id)}`),
}
