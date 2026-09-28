import { useState } from 'react'
import { Link } from 'react-router-dom'

import { useMetaCompare } from '../../api/hooks'
import { Deck, Empty, ErrorBox, GameCard, Loading, Panel, Segmented, WinRateBar } from '../../components/ui'
import { pct } from '../../lib/format'
import { usePlayerCtx } from './context'

export default function MetaTab() {
  const { tag, player } = usePlayerCtx()
  const [mode, setMode] = useState('ranked')
  const q = useMetaCompare(tag, mode, 14)

  if (q.isPending) return <Loading />
  if (q.isError) return <ErrorBox error={q.error} />
  const d = q.data

  if (d.decks_observed === 0)
    return (
      <Empty>
        No meta data yet. Open the <Link to="/meta" className="text-accent underline">Meta page</Link> and start a crawl of the top Ranked players.
      </Empty>
    )

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Segmented label="Meta source" value={mode} onChange={setMode} options={[{ value: 'ranked', label: 'Ranked' }, { value: 'ladder', label: 'Top ladder' }, { value: 'all', label: 'Both' }]} />
        <span className="text-sm text-ink-3">{d.decks_observed} top-player decks, last {d.days} days</span>
      </div>

      <Panel title="Your deck in the meta" subtitle="How often top players run each of your cards, and how it does for them">
        <ul className="grid grid-cols-1 gap-x-8 gap-y-2 md:grid-cols-2">
          {d.my_cards.map((c) => (
            <li key={c.id} className="grid grid-cols-[3.5rem_minmax(0,1fr)] items-center gap-3">
              <GameCard card={{ ...c, rarity: null, elixir: null, form: null }} showLevel={false} />
              <div>
                <div className="flex justify-between text-sm">
                  <span>{c.name}</span>
                  <span className="num text-xs text-ink-3">{pct(c.meta_usage)} usage · {c.meta_games}g</span>
                </div>
                <WinRateBar rate={{ win_rate: c.meta_win_rate, games: c.meta_games }} compact />
              </div>
            </li>
          ))}
        </ul>
        {d.exact_matches.games > 0 && (
          <p className="mt-4 text-sm">
            Top players ran your exact deck {d.exact_matches.games}× and won <b>{pct(d.exact_matches.win_rate)}</b>.
          </p>
        )}
        {d.off_meta_cards.length > 0 && (
          <p className="mt-2 text-sm text-ink-3">Off-meta (&lt;2% usage): {d.off_meta_cards.map((c) => c.name).join(', ')}</p>
        )}
      </Panel>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel title="Swap ideas" subtitle="Cards in top decks that share ≥5 cards with yours">
          {d.swap_suggestions.length ? (
            <ul className="space-y-2">
              {d.swap_suggestions.map((c) => (
                <li key={c.id} className="grid grid-cols-[3.5rem_minmax(0,1fr)] items-center gap-3">
                  <GameCard card={{ ...c, form: null }} showLevel={false} />
                  <div>
                    <div className="flex justify-between text-sm">
                      <span>{c.name}</span>
                      <span className="num text-xs text-ink-3">in {c.in_similar_decks} similar decks</span>
                    </div>
                    <WinRateBar rate={{ win_rate: c.similar_win_rate, games: c.in_similar_decks }} compact />
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <Empty>No close variants of your deck in the meta sample.</Empty>
          )}
        </Panel>
        <Panel title="Similar top decks">
          {d.similar_decks.length ? (
            <ul className="space-y-3">
              {d.similar_decks.map((s, i) => (
                <li key={i} className="border-b border-line pb-3 last:border-0">
                  <div className="mb-1.5 flex justify-between text-sm">
                    <span className="font-medium">{s.archetype} <span className="text-ink-3">· {s.shared}/8 shared</span></span>
                    <span className="num">{pct(s.win_rate, 0)} <span className="text-ink-3">· {s.games}g</span></span>
                  </div>
                  <Deck cards={s.cards} size="sm" />
                  <p className="mt-1 text-xs text-ink-3">Swaps in: {s.missing.map((c) => c.name).join(', ')}</p>
                </li>
              ))}
            </ul>
          ) : (
            <Empty>Your deck ({player.summary.current_deck.length} cards) has no close relatives among top decks.</Empty>
          )}
        </Panel>
      </div>
    </div>
  )
}
