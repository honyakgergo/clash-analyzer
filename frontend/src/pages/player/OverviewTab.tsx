import { useAnalytics, useChests } from '../../api/hooks'
import type { PolResult } from '../../api/types'
import { Deck, GameCard, InsightList, Loading, Panel, Stat } from '../../components/ui'
import { fmt, pct, prettyKey } from '../../lib/format'
import { usePlayerCtx } from './context'

function Ranked({ label, r }: { label: string; r: PolResult | null }) {
  return (
    <div className="flex items-center justify-between py-1.5 text-sm">
      <span className="text-ink-3">{label}</span>
      <span className="num font-medium">
        {r ? (
          <>
            League {r.leagueNumber}
            {r.trophies ? ` · ${fmt(r.trophies)} rating` : ''}
            {r.rank ? ` · #${fmt(r.rank)}` : ''}
          </>
        ) : (
          '–'
        )}
      </span>
    </div>
  )
}

export default function OverviewTab() {
  const { tag, player } = usePlayerCtx()
  const s = player.summary
  const analytics = useAnalytics(tag, 'competitive', null)
  const chests = useChests(tag)
  const streak = s.win_streak ?? 0

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <Stat label="Trophies" value={fmt(s.trophies)} hint={`best ${fmt(s.best_trophies)}`} />
        <Stat label="King tower" value={s.king_tower_level ?? '–'} hint={`collection lvl ${fmt(s.collection_level)}`} />
        <Stat label="Career win rate" value={pct(s.win_rate)} hint={`${fmt(s.wins)} W · ${fmt(s.losses)} L`} />
        <Stat label="3-crown wins" value={fmt(s.three_crown_wins)} hint={`${pct(s.three_crown_rate)} of wins`} />
        <Stat
          label="Streak"
          value={streak === 0 ? '–' : `${Math.abs(streak)}${streak > 0 ? 'W' : 'L'}`}
          hint={streak > 0 ? 'on a win streak' : streak < 0 ? 'on a losing streak' : 'no streak'}
          tone={streak > 0 ? 'good' : streak < 0 ? 'bad' : undefined}
        />
        <Stat label="Days played" value={fmt(s.days_played)} hint={s.days_played ? `${(s.days_played / 365).toFixed(1)} years` : undefined} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Panel
          className="lg:col-span-2"
          title="Current deck"
          subtitle={`avg elixir ${s.current_deck_avg_elixir ?? '–'} · avg level ${s.current_deck_avg_level ?? '–'}`}
        >
          <div className="flex flex-wrap items-end gap-4">
            <Deck cards={s.current_deck} size="lg" />
            {s.tower_troop && (
              <div className="border-l border-line pl-4">
                <div className="mb-1 text-xs uppercase tracking-wider text-ink-3">Tower</div>
                <GameCard card={s.tower_troop} size="md" />
              </div>
            )}
          </div>
          <p className="mt-3 text-xs text-ink-3">The current deck updates after a battle, so it can lag behind deck edits.</p>
        </Panel>

        <Panel title="Ranked (Path of Legends)">
          <Ranked label="This season" r={s.ranked.current} />
          <Ranked label="Last season" r={s.ranked.last} />
          <Ranked label="Best ever" r={s.ranked.best} />
          {s.legacy_best_trophies != null && (
            <div className="mt-2 flex justify-between border-t border-line pt-2 text-sm">
              <span className="text-ink-3">Pre-rework trophy best</span>
              <span className="num font-medium">{fmt(s.legacy_best_trophies)}</span>
            </div>
          )}
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Panel className="lg:col-span-2" title="Insights" subtitle="From your stored ladder and ranked battles">
          {analytics.isPending ? <Loading /> : analytics.data ? <InsightList items={analytics.data.insights} /> : null}
        </Panel>

        <Panel title="Upcoming chests">
          {chests.data?.length ? (
            <ol className="space-y-1.5 text-sm">
              {chests.data.slice(0, 9).map((c) => (
                <li key={c.index} className="flex justify-between">
                  <span>{c.name}</span>
                  <span className="num text-ink-3">{c.index === 0 ? 'next' : `+${c.index}`}</span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-sm text-ink-3">{chests.isPending ? 'Loading…' : 'No chest data.'}</p>
          )}
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Panel title="Career">
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            {[
              ['Battles', fmt(s.battle_count)],
              ['Challenge best', s.challenge_max_wins != null ? `${s.challenge_max_wins} wins` : '–'],
              ['Challenge cards won', fmt(s.challenge_cards_won)],
              ['Tournament battles', fmt(s.tournament_battles)],
              ['War day wins', fmt(s.war_day_wins)],
              ['Star points', fmt(s.star_points)],
              ['Donations (season)', fmt(s.donations)],
              ['Donations (lifetime)', fmt(s.total_donations)],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between border-b border-line/60 pb-1.5">
                <dt className="text-ink-3">{k}</dt>
                <dd className="num font-medium">{v}</dd>
              </div>
            ))}
          </dl>
        </Panel>
        <Panel title="Other modes" subtitle="Seasonal ladders tracked by the API">
          {s.other_modes.length ? (
            <ul className="space-y-1.5 text-sm">
              {s.other_modes.map((m) => (
                <li key={m.key} className="flex justify-between border-b border-line/60 pb-1.5">
                  <span>
                    {prettyKey(m.key)} <span className="text-ink-3">· {m.arena}</span>
                  </span>
                  <span className="num">
                    {fmt(m.trophies)} <span className="text-ink-3">/ best {fmt(m.best_trophies)}</span>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-ink-3">No other modes played.</p>
          )}
        </Panel>
      </div>
    </div>
  )
}
