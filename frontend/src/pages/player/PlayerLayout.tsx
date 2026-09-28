import { Link, NavLink, Navigate, Outlet, useParams } from 'react-router-dom'

import { usePlayer, useRefreshPlayer, useTrackToggle } from '../../api/hooks'
import { ErrorBox, Loading } from '../../components/ui'
import { fmt, timeAgo } from '../../lib/format'
import { cleanTag } from '../../lib/tags'
import type { PlayerCtx } from './context'

const TABS = [
  ['', 'Overview'],
  ['battles', 'Battle analytics'],
  ['progress', 'Progress'],
  ['upgrades', 'Upgrades'],
  ['mastery', 'Mastery'],
  ['meta', 'vs Meta'],
] as const

export default function PlayerLayout() {
  const { tag: raw = '' } = useParams()
  const tag = cleanTag(raw)
  if (!tag) return <ErrorBox error={new Error(`"${raw}" is not a valid player tag.`)} />
  if (tag !== raw) return <Navigate to={`/player/${tag}`} replace />
  return <PlayerShell tag={tag} />
}

function PlayerShell({ tag }: { tag: string }) {
  const q = usePlayer(tag)
  const refresh = useRefreshPlayer(tag)
  const track = useTrackToggle(tag)

  if (q.isPending) return <Loading label={`Fetching #${tag} from Clash Royale…`} />
  if (q.isError) return <ErrorBox error={q.error} />
  const { summary: s } = q.data

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-display text-4xl font-bold uppercase tracking-wide">{s.name}</h1>
            <span className="rounded bg-surface-2 px-2 py-0.5 font-mono text-sm text-ink-2">{s.tag}</span>
          </div>
          <p className="mt-1 text-sm text-ink-2">
            🏆 <span className="num font-semibold text-ink">{fmt(s.trophies)}</span>
            {s.arena && <> · {s.arena}</>}
            {s.clan && (
              <>
                {' · '}
                <Link to={`/clan/${s.clan.tag.replace('#', '')}`} className="text-accent hover:underline">
                  {s.clan.name}
                </Link>
                {s.role && <span className="text-ink-3"> ({s.role})</span>}
              </>
            )}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-ink-3">
            {q.data.battles_stored} battles stored · updated {timeAgo(q.data.last_refreshed_at)}
          </span>
          <button
            onClick={() => refresh.mutate()}
            disabled={refresh.isPending}
            className="rounded-md border border-line px-3 py-1.5 font-medium hover:border-accent disabled:opacity-50"
          >
            {refresh.isPending ? 'Refreshing…' : '↻ Refresh'}
          </button>
          <button
            onClick={() => track.mutate(!q.data.tracked)}
            disabled={track.isPending}
            aria-pressed={q.data.tracked}
            className={`rounded-md px-3 py-1.5 font-semibold ${
              q.data.tracked ? 'border border-accent text-accent' : 'bg-accent text-accent-ink hover:opacity-90'
            }`}
            title="Tracked players are polled every 15 minutes so no battle is lost"
          >
            {q.data.tracked ? '★ Tracking' : '☆ Track'}
          </button>
        </div>
      </header>

      {!q.data.tracked && (
        <p className="rounded-lg border border-line bg-surface-2/60 px-4 py-2.5 text-sm text-ink-2">
          The API only returns the last ~30 battles. Hit <b>Track</b> to poll this player in the background and build a real history.
        </p>
      )}

      <nav className="-mx-4 overflow-x-auto px-4" aria-label="Player sections">
        <ul className="flex min-w-max gap-1 border-b border-line">
          {TABS.map(([path, label]) => (
            <li key={path}>
              <NavLink
                end={path === ''}
                to={path}
                className={({ isActive }) =>
                  `-mb-px block border-b-2 px-3 py-2 text-sm font-medium ${
                    isActive ? 'border-accent text-ink' : 'border-transparent text-ink-3 hover:text-ink'
                  }`
                }
              >
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <Outlet context={{ tag, player: q.data } satisfies PlayerCtx} />
    </div>
  )
}
