import { Link, Route, Routes } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import WorldPage from './pages/WorldPage'

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b" style={{ borderColor: 'var(--line)' }}>
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link to="/" className="flex items-baseline gap-3">
            <span className="display text-lg font-700" style={{ fontWeight: 700, letterSpacing: '0.02em' }}>
              VANTA
            </span>
            <span className="mono hidden text-[11px] sm:inline" style={{ color: 'var(--ink-faint)' }}>
              generated broken · fixed by you
            </span>
          </Link>
          <span className="mono text-[11px]" style={{ color: 'var(--ink-faint)' }}>
            Virtualized Adversarial Network &amp; Technical Assessment
          </span>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-10">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/worlds/:id" element={<WorldPage />} />
        </Routes>
      </main>
    </div>
  )
}
