// A stable, anonymous id per browser so ratings and worlds follow the person.
export function userId(): string {
  try {
    let id = localStorage.getItem('vanta_uid')
    if (!id) { id = Math.random().toString(36).slice(2, 10); localStorage.setItem('vanta_uid', id) }
    return id
  } catch {
    const w = window as unknown as { __vanta_uid?: string }
    if (!w.__vanta_uid) w.__vanta_uid = Math.random().toString(36).slice(2, 10)
    return w.__vanta_uid
  }
}

export const PROFILE_EVENT = 'vanta:profile-changed'
export function notifyProfileChanged() { window.dispatchEvent(new Event(PROFILE_EVENT)) }
