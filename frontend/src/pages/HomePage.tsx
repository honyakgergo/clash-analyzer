import { Link } from 'react-router-dom'

import { useHealth, useTracked } from '../api/hooks'
import { TagSearch } from '../components/Layout'
import { Panel } from '../components/ui'
import { fmt, timeAgo } from '../lib/format'

const FEATURES = [
  ['Progress tracker', 'Trophies, Ranked rating, collection and mastery over time. The API keeps no history, so this app builds it.'],
  ['Upgrade planner', 'Gold and copies to level your deck, and which upgrades give the most for the gold.'],
  ['Battle analytics', 'Tilt detection, level-gap vs skill losses, elixir leak, close games, nemesis cards and archetypes.'],
  ['Meta comparison', 'Top Ranked players crawled and aggregated. See how your deck stacks up and what to swap.'],
]

export default function HomePage() {
  const health = useHealth()
  const tracked = useTracked()
  const defaultTag = health.data?.default_player_tag

  return (
    <div className="space-y-10">
      <section className="mx-auto max-w-2xl pt-8 text-center sm:pt-16">
        <h1 className="font-display text-5xl font-bold uppercase leading-none tracking-wide sm:text-6xl">
          Know why you <span className="text-accent">win</span>.
        </h1>
        <p className="mx-auto mt-4 max-w-lg text-ink-2">
          Enter any player tag. Your history keeps growing while you play, and you get analytics the game doesn't show you.
        </p>
        <div className="mx-auto mt-8 max-w-lg">
          <TagSearch big autoFocus />
          {defaultTag && (
            <p className="mt-3 text-sm text-ink-3">
              or open{' '}
              <Link className="font-mono text-accent hover:underline" to={`/player/${defaultTag.replace('#', '')}`}>
                #{defaultTag.replace('#', '')}
              </Link>
            </p>
          )}
          {health.data && !health.data.api_key_configured && (
            <p className="mt-3 text-sm text-critical">⚠ The backend has no API key configured. See backend/.env.example.</p>
          )}
          {health.isError && <p className="mt-3 text-sm text-critical">⚠ Backend not reachable. Start it with `uv run clash-analyzer`.</p>}
        </div>
      </section>

      {!!tracked.data?.length && (
        <Panel title="Tracked players" subtitle="Polled every 15 minutes in the background">
          <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {tracked.data.map((p) => (
              <li key={p.tag}>
                <Link
                  to={`/player/${p.tag.replace('#', '')}`}
                  className="flex items-center justify-between rounded-lg border border-line px-4 py-3 hover:border-accent"
                >
                  <span>
                    <span className="font-semibold">{p.name}</span>
                    <span className="ml-2 font-mono text-xs text-ink-3">{p.tag}</span>
                  </span>
                  <span className="text-right text-sm">
                    <span className="num font-semibold">🏆 {fmt(p.trophies)}</span>
                    <span className="block text-xs text-ink-3">{timeAgo(p.last_refreshed_at)}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map(([title, text]) => (
          <div key={title} className="rounded-xl border border-line bg-surface p-5">
            <h3 className="font-display text-lg font-bold uppercase tracking-wide">{title}</h3>
            <p className="mt-1.5 text-sm text-ink-2">{text}</p>
          </div>
        ))}
      </section>
    </div>
  )
}
