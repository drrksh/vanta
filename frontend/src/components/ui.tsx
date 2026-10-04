import type { ReactNode } from 'react'

export function Panel({
  children, className = '', style,
}: { children: ReactNode; className?: string; style?: React.CSSProperties }) {
  return (
    <div
      className={`rounded-lg border ${className}`}
      style={{ borderColor: 'var(--line)', background: 'var(--panel)', ...style }}
    >
      {children}
    </div>
  )
}

export function Label({ children }: { children: ReactNode }) {
  return (
    <div
      className="mono mb-2 text-[11px] uppercase"
      style={{ color: 'var(--ink-faint)', letterSpacing: '0.12em' }}
    >
      {children}
    </div>
  )
}

type Tone = 'structure' | 'signal' | 'accepted' | 'rejected' | 'neutral'
const TONE: Record<Tone, string> = {
  structure: 'var(--structure)', signal: 'var(--signal)',
  accepted: 'var(--accepted)', rejected: 'var(--rejected)', neutral: 'var(--ink-dim)',
}

export function Chip({ children, tone = 'neutral' }: { children: ReactNode; tone?: Tone }) {
  const c = TONE[tone]
  return (
    <span
      className="mono inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-[12px]"
      style={{ color: c, borderColor: `color-mix(in srgb, ${c} 40%, transparent)`,
               background: `color-mix(in srgb, ${c} 10%, transparent)` }}
    >
      {children}
    </span>
  )
}

export function Button({
  children, onClick, variant = 'primary', disabled, type = 'button', className = '',
}: {
  children: ReactNode; onClick?: () => void
  variant?: 'primary' | 'ghost' | 'danger'; disabled?: boolean
  type?: 'button' | 'submit'; className?: string
}) {
  const base =
    'vanta-focus inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-[14px] font-medium transition-all disabled:cursor-not-allowed disabled:opacity-40'
  const styles: Record<string, React.CSSProperties> = {
    primary: { background: 'var(--structure)', color: '#07131a' },
    ghost: { background: 'transparent', color: 'var(--ink-dim)', border: '1px solid var(--line-bright)' },
    danger: { background: 'transparent', color: 'var(--rejected)',
              border: '1px solid color-mix(in srgb, var(--rejected) 45%, transparent)' },
  }
  return (
    <button type={type} onClick={onClick} disabled={disabled}
      className={`${base} ${className}`} style={styles[variant]}>
      {children}
    </button>
  )
}

export function Spinner({ className = '' }: { className?: string }) {
  return (
    <svg className={`h-4 w-4 animate-spin ${className}`} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path className="opacity-90" d="M22 12a10 10 0 0 0-10-10" stroke="currentColor"
        strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}
