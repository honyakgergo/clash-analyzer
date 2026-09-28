import { useEffect, useState, type FormEvent } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'

import { cleanTag } from '../lib/tags'
import { applyTheme, initialTheme, type Theme } from '../lib/theme'

export function TagSearch({ autoFocus = false, big = false }: { autoFocus?: boolean; big?: boolean }) {
  const [value, setValue] = useState('')
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  function submit(e: FormEvent) {
    e.preventDefault()
    const tag = cleanTag(value)
    if (!tag) {
      setError('Tags use only 0 2 8 9 C G J L P Q R U V Y')
      return
    }
    setError(null)
    setValue('')
    navigate(`/player/${tag}`)
  }

  return (
    <form onSubmit={submit} className="w-full" role="search">
      <div className={`flex items-center gap-2 rounded-lg border border-line bg-surface ${big ? 'p-1.5' : 'p-1'}`}>
        <span className={`pl-2 font-mono text-ink-3 ${big ? 'text-lg' : ''}`}>#</span>
        <input
          aria-label="Player tag"
          autoFocus={autoFocus}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Player tag, e.g. PQGGV0JP"
          className={`min-w-0 flex-1 bg-transparent font-mono uppercase outline-none placeholder:normal-case placeholder:text-ink-3 ${big ? 'py-2 text-lg' : 'py-1 text-sm'}`}
        />
        <button className={`rounded-md bg-accent font-semibold text-accent-ink hover:opacity-90 ${big ? 'px-5 py-2.5' : 'px-3 py-1.5 text-sm'}`}>
          Analyze
        </button>
      </div>
      {error && <p className="mt-1.5 text-xs text-critical">{error}</p>}
    </form>
  )
}

export default function Layout() {
  const [theme, setTheme] = useState<Theme>(initialTheme)
  useEffect(() => applyTheme(theme), [theme])
  const next: Theme = theme === 'dark' ? 'light' : 'dark'

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-line bg-bg/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-2.5">
          <Link to="/" className="flex shrink-0 items-center gap-2">
            <img src="/favicon.svg" alt="" className="h-7 w-7" />
            <span className="hidden font-display text-xl font-bold uppercase tracking-wider sm:inline">
              Clash<span className="text-accent">Analyzer</span>
            </span>
          </Link>
          <div className="min-w-0 max-w-md flex-1">
            <TagSearch />
          </div>
          <nav className="ml-auto flex items-center gap-1 text-sm">
            <NavLink
              to="/meta"
              className={({ isActive }) => `rounded-md px-3 py-1.5 font-medium ${isActive ? 'bg-surface-2 text-ink' : 'text-ink-2 hover:text-ink'}`}
            >
              Meta
            </NavLink>
            <button
              onClick={() => setTheme(next)}
              className="rounded-md px-2.5 py-1.5 text-base text-ink-2 hover:text-ink"
              aria-label={`Switch to ${next} mode`}
              title={`Switch to ${next} mode`}
            >
              {theme === 'dark' ? '☀' : '☾'}
            </button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
      <footer className="mx-auto max-w-7xl px-4 pb-8 pt-4 text-xs text-ink-3">
        Not affiliated with Supercell. Data from the official Clash Royale API, used under Supercell's Fan Content Policy.
      </footer>
    </div>
  )
}
