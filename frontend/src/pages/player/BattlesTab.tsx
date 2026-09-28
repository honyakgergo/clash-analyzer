import { useState } from 'react'

import { useAnalytics, useBattles } from '../../api/hooks'
import type { Battle, CardRate, Rate } from '../../api/types'
import { SignedBars, WinRateBars } from '../../components/charts'
import {
  Deck,
  Empty,
  ErrorBox,
  InsightList,
  Loading,
  Panel,
  SampleNote,
  Segmented,
  Stat,
  WinRateBar,
} from '../../components/ui'
import { MODE_LABEL, WEEKDAYS, dateTime, fmt, pct, shortDate, signed } from '../../lib/format'
import { usePlayerCtx } from './context'

const MODES = ['competitive', 'ladder', 'ranked', 'war', 'seasonal', 'event', 'all'].map((m) => ({
  value: m,
  label: MODE_LABEL[m],
}))
const RANGES: { value: number; label: string }[] = [
  { value: 0, label: 'All time' },
  { value: 30, label: '30 days' },
  { value: 7, label: '7 days' },
]

function RateRow({ label, rate, note }: { label: string; rate: Rate; note?: string }) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_minmax(6rem,1.1fr)] items-center gap-3 py-1.5 text-sm">
      <div className="min-w-0" title={note}>
        <div className="truncate text-ink-2">{label}</div>
        <div className="truncate text-[11px]">
          <SampleNote rate={rate} />
        </div>
      </div>
      <WinRateBar rate={rate} />
    </div>
  )
}

function CardRateTable({ rows, empty }: { rows: CardRate[]; empty: string }) {
  if (!rows.length) return <Empty>{empty}</Empty>
  return (
    <ul className="space-y-1">
      {rows.map((r) => (
        <li key={r.id} className="grid grid-cols-[2rem_minmax(0,1fr)_minmax(6rem,10rem)] items-center gap-3 text-sm">
          {r.icon ? <img src={r.icon} alt="" className="h-9 w-8 object-contain" /> : <span />}
          <span className="truncate">
            {r.name} <span className="text-xs text-ink-3">· {r.games}g</span>
          </span>
          <WinRateBar rate={r} compact />
        </li>
      ))}
    </ul>
  )
}

function BattleRow({ b }: { b: Battle }) {
  const tone = b.result === 'win' ? 'text-good-ink' : b.result === 'loss' ? 'text-critical' : 'text-ink-2'
  return (
    <li className="grid gap-3 border-b border-line py-3 last:border-0 md:grid-cols-[7rem_1fr_1fr]">
      <div className="text-sm">
        <div className={`font-display text-xl font-bold uppercase ${tone}`}>
          {b.result} <span className="num">{b.crowns}–{b.opp_crowns}</span>
        </div>
        <div className="text-xs text-ink-3">{dateTime(b.battle_time)}</div>
        <div className="text-xs text-ink-3">
          {MODE_LABEL[b.mode_group] ?? b.mode_group}
          {b.trophy_change ? ` · ${signed(b.trophy_change)}🏆` : ''}
        </div>
      </div>
      <div>
        <div className="mb-1 text-xs text-ink-3">
          You · {b.archetype} · lvl {b.avg_level?.toFixed(1)} · leaked {b.elixir_leaked?.toFixed(1)}
        </div>
        <Deck cards={b.deck} size="sm" />
      </div>
      <div>
        <div className="mb-1 truncate text-xs text-ink-3">
          {b.opp_name} · {b.opp_archetype} · lvl {b.opp_avg_level?.toFixed(1)}
        </div>
        <Deck cards={b.opp_deck} size="sm" />
      </div>
    </li>
  )
}

export default function BattlesTab() {
  const { tag } = usePlayerCtx()
  const [mode, setMode] = useState('competitive')
  const [days, setDays] = useState(0)
  const q = useAnalytics(tag, mode, days || null)
  const recent = useBattles(tag, mode === 'competitive' ? 'competitive' : mode, 15)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Segmented label="Game mode" value={mode} options={MODES} onChange={setMode} />
        <Segmented label="Time range" value={days} options={RANGES} onChange={setDays} />
      </div>

      {q.isPending && <Loading />}
      {q.isError && <ErrorBox error={q.error} />}
      {q.data && q.data.summary.games === 0 && (
        <Empty>No stored battles for this filter yet. Track the player, or play a few games.</Empty>
      )}
      {q.data && q.data.summary.games > 0 && <Report data={q.data} />}

      <Panel title="Recent battles">
        {recent.data?.items.length ? (
          <ul>{recent.data.items.map((b) => <BattleRow key={b.id} b={b} />)}</ul>
        ) : (
          <Empty>No battles.</Empty>
        )}
      </Panel>
    </div>
  )
}

function Report({ data }: { data: NonNullable<ReturnType<typeof useAnalytics>['data']> }) {
  const { summary: s, tilt, levels, close_games: close, elixir, evolutions: evo, matchups, timeline } = data
  const hourly = timeline.hourly.map((h) => ({ ...h, win_rate: h.games ? h.win_rate : null }))
  const weekday = timeline.weekday.map((d) => ({ ...d, label: WEEKDAYS[d.weekday], win_rate: d.games ? d.win_rate : null }))

  return (
    <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <Stat label="Win rate" value={pct(s.win_rate)} hint={<SampleNote rate={s} />} />
        <Stat label="Record" value={`${s.wins}–${s.losses}`} hint={s.draws ? `${s.draws} draws` : `${s.games} games`} />
        <Stat label="Net trophies" value={signed(s.net_trophies)} hint={`avg +${s.avg_trophies_win ?? '–'} / ${s.avg_trophies_loss ?? '–'}`} tone={s.net_trophies > 0 ? 'good' : s.net_trophies < 0 ? 'bad' : undefined} />
        <Stat label="3-crowns" value={s.three_crown_wins} hint={`three-crowned ${s.three_crowned}×`} />
        <Stat label="Avg level gap" value={signed(s.avg_level_gap, 2)} hint="you minus opponent" tone={(s.avg_level_gap ?? 0) >= 0 ? 'good' : 'bad'} />
        <Stat label="Elixir leaked" value={s.avg_elixir_leaked ?? '–'} hint="avg per game" />
      </div>

      <Panel title="What the data says" subtitle={`${s.games} battles · ${data.timezone}`}>
        <InsightList items={data.insights} />
      </Panel>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel title="Tilt & momentum" subtitle="Your win rate depending on the previous result">
          <RateRow label="After a win" rate={tilt.after_win} />
          <RateRow label="After a loss" rate={tilt.after_loss} />
          <RateRow label="After 2+ losses" rate={tilt.after_2_losses} />
          <RateRow label="After 3+ wins" rate={tilt.after_3_wins} />
          <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 border-t border-line pt-3 text-sm text-ink-2">
            <span>Longest win streak <b className="num text-ink">{tilt.longest_win_streak}</b></span>
            <span>Longest loss streak <b className="num text-ink">{tilt.longest_loss_streak}</b></span>
            <span>{tilt.sessions.count} sessions · avg {tilt.sessions.avg_length} games</span>
          </div>
        </Panel>
        <Panel title="Session fatigue" subtitle="Win rate by game number within a session (20-min gaps split sessions)">
          <WinRateBars data={tilt.sessions.by_game_index} x="index" xFormat={(v) => `#${v}`} label="Win rate by game number in session" />
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel
          title="Levels vs skill"
          subtitle={
            levels.share_losses_underleveled != null
              ? `${levels.share_losses_underleveled}% of ${levels.losses_total} losses were against decks ≥0.5 levels higher`
              : 'Average card level of your deck minus your opponent’s'
          }
        >
          <WinRateBars data={levels.buckets} x="bucket" label="Win rate by level gap" />
          <p className="mt-2 text-xs text-ink-3">
            At even levels you win <b className="text-ink">{pct(levels.even_level.win_rate)}</b> ({levels.even_level.games} games). This is your skill baseline.
          </p>
        </Panel>
        <Panel title="Elixir leaked" subtitle={`avg ${elixir.avg_in_wins ?? '–'} in wins vs ${elixir.avg_in_losses ?? '–'} in losses`}>
          <WinRateBars data={elixir.buckets} x="bucket" label="Win rate by elixir leaked" />
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Panel title="Close games">
          <RateRow label="One-crown games" rate={close.one_crown} />
          <RateRow label="Blowouts (2+)" rate={close.blowouts} />
          <dl className="mt-3 space-y-1.5 border-t border-line pt-3 text-sm">
            <div className="flex justify-between"><dt className="text-ink-3">1-crown losses</dt><dd className="num">{close.one_crown_losses}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-3">Enemy tower HP left in those</dt><dd className="num">{fmt(close.near_miss_tower_hp)}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-3">Your king HP left in wins</dt><dd className="num">{fmt(close.avg_king_hp_left_in_wins != null ? Math.round(close.avg_king_hp_left_in_wins) : null)}</dd></div>
          </dl>
        </Panel>
        <Panel title="Evos & heroes" subtitle="Your special forms vs your opponent's">
          {evo.special_advantage.map((r) => (
            <RateRow key={r.bucket} label={`${r.bucket[0].toUpperCase()}${r.bucket.slice(1)} specials`} rate={r} />
          ))}
          <div className="mt-2 border-t border-line pt-2">
            <RateRow label="With a hero" rate={evo.with_hero} />
            <RateRow label="Without a hero" rate={evo.without_hero} />
          </div>
        </Panel>
        <Panel title="By mode" subtitle="All stored battles in this range">
          {data.by_mode.map((m) => (
            <RateRow key={m.mode} label={MODE_LABEL[m.mode] ?? m.mode} rate={m} />
          ))}
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel title="Nemesis cards" subtitle={`Lowest win rate against (≥${matchups.min_games} games)`}>
          <CardRateTable rows={matchups.nemesis} empty="Not enough games per card yet." />
        </Panel>
        <Panel title="Prey cards" subtitle="Highest win rate against">
          <CardRateTable rows={matchups.prey} empty="Not enough games per card yet." />
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel title="Opponent archetypes">
          {matchups.archetypes.slice(0, 10).map((a) => (
            <RateRow key={a.archetype} label={a.archetype} rate={a} />
          ))}
        </Panel>
        <Panel title="Your decks">
          <ul className="space-y-3">
            {data.decks.slice(0, 5).map((d) => (
              <li key={d.last_played + d.archetype} className="border-b border-line pb-3 last:border-0">
                <div className="mb-1.5 flex items-baseline justify-between gap-2 text-sm">
                  <span className="font-semibold">{d.archetype} <span className="font-normal text-ink-3">· {d.avg_elixir?.toFixed(1)} elixir</span></span>
                  <span className="num">
                    {pct(d.win_rate, 0)} <span className="text-ink-3">· {d.games}g</span>
                  </span>
                </div>
                <Deck cards={d.cards} size="sm" />
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel title="Best time to play" subtitle={`Win rate by hour (${data.timezone})`}>
          <WinRateBars data={hourly} x="hour" xFormat={(v) => `${String(v).padStart(2, '0')}h`} label="Win rate by hour of day" />
        </Panel>
        <Panel title="By weekday">
          <WinRateBars data={weekday} x="label" label="Win rate by weekday" />
        </Panel>
      </div>

      {timeline.daily.length > 1 && (
        <Panel title="Daily trophy change" subtitle="Ladder only">
          <SignedBars data={timeline.daily} x="date" y="net_trophies" xFormat={(v) => shortDate(String(v))} label="Net trophies per day" />
        </Panel>
      )}

      <Panel title="Your cards" subtitle="Win rate when the card was in your deck">
        <div className="grid grid-cols-1 gap-x-8 gap-y-1 md:grid-cols-2">
          {data.cards.slice(0, 16).map((c) => (
            <div key={c.id} className="grid grid-cols-[2rem_minmax(0,1fr)_minmax(6rem,10rem)] items-center gap-3 text-sm">
              {c.icon ? <img src={c.icon} alt="" className="h-9 w-8 object-contain" /> : <span />}
              <span className="truncate">
                {c.name} <span className="text-xs text-ink-3">· {c.games}g</span>
              </span>
              <WinRateBar rate={c} compact />
            </div>
          ))}
        </div>
        {data.tower_troops.length > 1 && (
          <div className="mt-4 border-t border-line pt-3">
            {data.tower_troops.map((t) => (
              <RateRow key={t.tower_troop} label={t.tower_troop} rate={t} />
            ))}
          </div>
        )}
        <p className="mt-3 text-xs text-ink-3">
          Bars show win rate. The whisker is the 95% interval, and the tick marks 50%. Small samples have wide whiskers.
        </p>
      </Panel>
    </>
  )
}
