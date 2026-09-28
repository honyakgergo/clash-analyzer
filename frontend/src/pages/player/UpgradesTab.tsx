import { useMemo, useState } from 'react'

import { useUpgrades } from '../../api/hooks'
import type { CardPlan } from '../../api/types'
import { Empty, ErrorBox, GameCard, Loading, Panel, ProgressBar, Segmented, Stat } from '../../components/ui'
import { compact, fmt, signed } from '../../lib/format'
import { usePlayerCtx } from './context'

const TARGETS = [13, 14, 15, 16].map((v) => ({ value: v, label: `Lvl ${v}` }))
const SORTS = [
  { value: 'level', label: 'Level' },
  { value: 'progress', label: 'Closest' },
  { value: 'gold', label: 'Gold to max' },
] as const
type Sort = (typeof SORTS)[number]['value']

function toCard(p: CardPlan) {
  return { id: p.id, name: p.name, rarity: p.rarity, elixir: p.elixir, form: null, icon: p.icon, level: p.level }
}

function Row({ p, showUsage }: { p: CardPlan; showUsage?: boolean }) {
  const progress = p.maxed ? 1 : p.next_cards ? Math.min(1, p.count / p.next_cards) : 0
  return (
    <li className="grid grid-cols-[3.5rem_minmax(0,1fr)_auto] items-center gap-3 border-b border-line py-2 last:border-0">
      <GameCard card={toCard(p)} size="md" />
      <div className="min-w-0">
        <div className="flex items-baseline justify-between gap-2 text-sm">
          <span className="truncate font-medium">{p.name}</span>
          <span className="num shrink-0 text-xs text-ink-3">
            {p.maxed ? 'MAX' : `${fmt(p.count)} / ${fmt(p.next_cards)}`}
          </span>
        </div>
        <div className="mt-1.5">
          <ProgressBar value={progress} label={`${p.name} copies toward next level`} />
        </div>
        <div className="mt-1 text-xs text-ink-3">
          {p.maxed
            ? 'Maxed'
            : p.can_upgrade
              ? `Upgrade ready · ${fmt(p.next_gold)} gold${p.levels_affordable > 1 ? ` · ${p.levels_affordable} levels affordable` : ''}`
              : `${fmt(p.copies_missing_next)} copies short`}
          {showUsage && p.usage > 0 && ` · in ${Math.round(p.usage * 100)}% of games`}
          {p.vs_opponents != null && ` · ${signed(p.vs_opponents, 1)} vs opp avg`}
        </div>
      </div>
      <div className="text-right text-xs">
        <div className="num font-semibold">{compact(p.to_max_gold)}</div>
        <div className="text-ink-3">to max</div>
      </div>
    </li>
  )
}

export default function UpgradesTab() {
  const { tag } = usePlayerCtx()
  const [target, setTarget] = useState(16)
  const [sort, setSort] = useState<Sort>('level')
  const [rarity, setRarity] = useState('all')
  const q = useUpgrades(tag, target)

  const cards = useMemo(() => {
    const list = (q.data?.cards ?? []).filter((c) => rarity === 'all' || c.rarity === rarity)
    const key: Record<Sort, (c: CardPlan) => number> = {
      level: (c) => -c.level,
      progress: (c) => (c.maxed ? 2 : -(c.count / (c.next_cards || 1))),
      gold: (c) => c.to_max_gold,
    }
    return [...list].sort((a, b) => key[sort](a) - key[sort](b))
  }, [q.data, sort, rarity])

  if (q.isPending) return <Loading />
  if (q.isError) return <ErrorBox error={q.error} />
  const d = q.data
  const ds = d.deck_summary
  const cs = d.collection_summary

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-ink-3">Deck target</span>
        <Segmented label="Target level" value={target} options={TARGETS} onChange={setTarget} />
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label={`Gold to lvl ${target}`} value={compact(ds.gold_to_target)} hint={`${ds.cards_at_target}/8 deck cards there`} />
        <Stat label="Copies missing" value={compact(ds.copies_missing_to_target)} hint={`for the deck to reach lvl ${target}`} />
        <Stat label="Upgrades ready" value={cs.upgradable_now} hint={`${compact(cs.gold_for_all_affordable)} gold to do them all`} />
        <Stat label="Collection maxed" value={`${cs.maxed}/${cs.cards}`} hint={`${compact(cs.gold_to_max_all)} gold to max everything`} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel
          title="Your deck"
          subtitle={
            d.opponent_avg_level != null
              ? `avg ${ds.avg_level} vs opponents' ${d.opponent_avg_level} over ${d.games_analyzed} games`
              : `avg level ${ds.avg_level}`
          }
        >
          <ul>{d.deck.map((p) => <Row key={p.id} p={p} />)}</ul>
        </Panel>
        <div className="space-y-6">
          <Panel title="Upgrade next" subtitle="Cards you play, enough copies, cheapest gain first">
            {d.upgradable_now.length ? (
              <ul>{d.upgradable_now.slice(0, 6).map((p) => <Row key={p.id} p={p} showUsage />)}</ul>
            ) : (
              <Empty>None of the cards you play have enough copies right now.</Empty>
            )}
          </Panel>
          <Panel title="Almost there" subtitle="Cards you play, closest to their next level">
            {d.closest_blocked.length ? (
              <ul>{d.closest_blocked.slice(0, 5).map((p) => <Row key={p.id} p={p} showUsage />)}</ul>
            ) : (
              <Empty>Nothing blocked.</Empty>
            )}
          </Panel>
        </div>
      </div>

      <Panel
        title="Collection"
        subtitle={Object.entries(cs.by_level)
          .reverse()
          .map(([lvl, n]) => `${n}× lvl ${lvl}`)
          .join(' · ')}
        action={
          <div className="flex flex-wrap gap-2">
            <Segmented
              label="Rarity"
              value={rarity}
              onChange={setRarity}
              options={['all', 'common', 'rare', 'epic', 'legendary', 'champion'].map((r) => ({ value: r, label: r[0].toUpperCase() + r.slice(1) }))}
            />
            <Segmented label="Sort" value={sort} onChange={setSort} options={[...SORTS]} />
          </div>
        }
      >
        <ul className="grid grid-cols-1 gap-x-8 md:grid-cols-2 xl:grid-cols-3">{cards.map((p) => <Row key={p.id} p={p} />)}</ul>
      </Panel>

      <ul className="space-y-1 text-xs text-ink-3">
        {d.notes.map((n) => (
          <li key={n}>ⓘ {n}</li>
        ))}
      </ul>
    </div>
  )
}
