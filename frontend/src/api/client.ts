import type { Archetype, SubmitResult, WorldFull, WorldSummary } from '../types'

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
  create: (created_by: string, target_difficulty: number, archetype_id?: string) =>
    req<WorldFull>('POST', '/api/worlds', { created_by, target_difficulty, archetype_id }),
  list: (created_by: string) =>
    req<WorldSummary[]>('GET', `/api/worlds?created_by=${encodeURIComponent(created_by)}`),
  get: (id: string) => req<WorldFull>('GET', `/api/worlds/${id}`),
  submit: (id: string, c_source: string) =>
    req<SubmitResult>('POST', `/api/worlds/${id}/submit`, { c_source }),
  remove: (id: string) => req<{ deleted: string }>('DELETE', `/api/worlds/${id}`),
}
