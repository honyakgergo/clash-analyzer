import type { ReactNode } from 'react'

import { ApiError } from '../api/client'
import type { Rate, SlimCard } from '../api/types'
import { pct } from '../lib/format'

export function Panel({
  title,
  subtitle,
  action,
  children,
  className = '',
}: {
  title?: ReactNode
  subtitle?: ReactNode
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`min-w-0 rounded-xl border border-line bg-surface p-4 sm:p-5 ${className}`}>
      {(title || action) && (
        <header className="mb-4 flex flex-wrap items-start justify-between gap-2">
          <div>
            {title && <h2 className="font-display text-lg font-bold uppercase tracking-wide">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-sm text-ink-3">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  )
}

export function Stat({
  label,
  value,
  hint,
  tone,
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  tone?: 'good' | 'bad'
}) {
  return (
    <div className="rounded-lg border border-line bg-surface px-4 py-3">
      <div className="text-xs font-medium uppercase tracking-wider text-ink-3">{label}</div>
      <div className="num mt-1 font-display text-3xl font-bold leading-none">{value}</div>
      {hint && (
        <div
          className={`mt-1.5 text-xs ${tone === 'good' ? 'text-good-ink' : tone === 'bad' ? 'text-critical' : 'text-ink-3'}`}
        >
          {hint}
        </div>
      )}
    </div>
  )
}

export function Segmented<T extends string | number>({
  value,
  options,
  onChange,
  label,
}: {
  value: T
  options: { value: T; label: string }[]
  onChange: (v: T) => void
  label: string
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex flex-wrap rounded-lg border border-line bg-surface-2 p-0.5">
      {options.map((o) => (
        <button
          key={String(o.value)}
          role="radio"
          aria-checked={o.value === value}
          onClick={() => onChange(o.value)}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            o.value === value ? 'bg-surface text-ink shadow-sm' : 'text-ink-3 hover:text-ink'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-10 text-ink-3" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" />
      {label}
    </div>
  )
}

export function ErrorBox({ error }: { error: unknown }) {
  const msg = error instanceof ApiError ? error.message : error instanceof Error ? error.message : 'Something went wrong'
  const status = error instanceof ApiError ? error.status : null
  return (
    <div role="alert" className="rounded-lg border border-critical/40 bg-critical/10 px-4 py-3 text-sm">
      <span className="mr-2 font-semibold text-critical">⚠ {status === 404 ? 'Not found' : 'Error'}</span>
      {msg}
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="rounded-lg border border-dashed border-line px-4 py-8 text-center text-sm text-ink-3">{children}</div>
}

export function SampleNote({ rate }: { rate: Pick<Rate, 'games' | 'ci_low' | 'ci_high'> }) {
  if (!rate.games) return <span className="text-ink-3">no games</span>
  return (
    <span className="text-ink-3" title="95% confidence interval (Wilson)">
      {rate.games} games · {rate.ci_low}–{rate.ci_high}%
    </span>
  )
}

/** Horizontal win-rate bar: 0–100 scale, 50% tick, CI whisker. One series color. */
export function WinRateBar({ rate, compact = false }: { rate: Rate | { win_rate: number | null; ci_low?: number | null; ci_high?: number | null; games: number }; compact?: boolean }) {
  const wr = rate.win_rate ?? 0
  const lo = rate.ci_low ?? null
  const hi = rate.ci_high ?? null
  return (
    <div className="flex items-center gap-2">
      <div className={`relative flex-1 rounded-full bg-surface-2 ${compact ? 'h-1.5' : 'h-2'}`}>
        <div className="absolute inset-y-0 left-0 rounded-full bg-series-1" style={{ width: `${wr}%` }} />
        {lo != null && hi != null && rate.games > 0 && (
          <div
            className="absolute top-1/2 h-px -translate-y-1/2 bg-ink-2/60"
            style={{ left: `${lo}%`, width: `${Math.max(0, hi - lo)}%` }}
            aria-hidden
          />
        )}
        <div className="absolute -inset-y-0.5 left-1/2 w-px bg-ink-3/50" aria-hidden />
      </div>
      <span className="num w-12 text-right text-sm font-semibold">{rate.games ? pct(rate.win_rate, 0) : '–'}</span>
    </div>
  )
}

export function ProgressBar({ value, label }: { value: number; label?: string }) {
  const v = Math.max(0, Math.min(1, value))
  return (
    <div className="h-1.5 w-full rounded-full bg-surface-2" role="progressbar" aria-valuenow={Math.round(v * 100)} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <div className="h-full rounded-full bg-series-1" style={{ width: `${v * 100}%` }} />
    </div>
  )
}

const RARITY_RING: Record<string, string> = {
  common: 'var(--r-common)',
  rare: 'var(--r-rare)',
  epic: 'var(--r-epic)',
  legendary: 'var(--r-legendary)',
  champion: 'var(--r-champion)',
}

export function GameCard({ card, size = 'md', showLevel = true }: { card: SlimCard; size?: 'sm' | 'md' | 'lg'; showLevel?: boolean }) {
  const w = size === 'sm' ? 'w-10' : size === 'lg' ? 'w-20' : 'w-14'
  return (
    <figure className={`${w} shrink-0`} title={`${card.name}${card.level ? ` · level ${card.level}` : ''}${card.form ? ` · ${card.form}` : ''}`}>
      <div className="relative">
        {card.icon ? (
          <img src={card.icon} alt={card.name} loading="lazy" className="aspect-[5/6] w-full object-contain drop-shadow" />
        ) : (
          <div className="flex aspect-[5/6] w-full items-center justify-center rounded bg-surface-2 text-[10px] text-ink-3">{card.name}</div>
        )}
        {card.form && (
          <span className="absolute -right-1 -top-1 rounded bg-accent px-1 text-[9px] font-bold uppercase text-accent-ink">
            {card.form}
          </span>
        )}
      </div>
      {showLevel && card.level != null && (
        <figcaption
          className="num mx-auto -mt-1 w-fit rounded px-1.5 text-center text-[11px] font-bold"
          style={{ background: RARITY_RING[card.rarity ?? 'common'], color: '#fff' }}
        >
          {card.level}
        </figcaption>
      )}
    </figure>
  )
}

export function Deck({ cards, size = 'md' }: { cards: SlimCard[]; size?: 'sm' | 'md' | 'lg' }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {cards.map((c) => (
        <GameCard key={c.id} card={c} size={size} />
      ))}
    </div>
  )
}

export function Tone({ value, children, invert = false }: { value: number | null | undefined; children: ReactNode; invert?: boolean }) {
  if (value == null || value === 0) return <span className="text-ink-2">{children}</span>
  const good = invert ? value < 0 : value > 0
  return <span className={good ? 'text-good-ink' : 'text-critical'}>{good ? '▲' : '▼'} {children}</span>
}

export function InsightList({ items }: { items: { level: 'good' | 'warn' | 'info'; text: string }[] }) {
  const icon = { good: '✓', warn: '!', info: 'i' }
  const cls = { good: 'bg-good/15 text-good-ink', warn: 'bg-warning/20 text-ink', info: 'bg-series-1/15 text-series-1' }
  return (
    <ul className="space-y-2">
      {items.map((i) => (
        <li key={i.text} className="flex gap-3 rounded-lg border border-line bg-surface-2/50 px-3 py-2.5 text-sm">
          <span aria-label={i.level} className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${cls[i.level]}`}>
            {icon[i.level]}
          </span>
          <span>{i.text}</span>
        </li>
      ))}
    </ul>
  )
}
