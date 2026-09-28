import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { useMeta, useMetaStatus, useStartMetaCrawl } from '../api/hooks'
import { Deck, Empty, ErrorBox, GameCard, Loading, Panel, Segmented, Stat, WinRateBar } from '../components/ui'
import { pct, timeAgo } from '../lib/format'

export default function MetaPage() {
  const [mode, setMode] = useState('ranked')
  const [days, setDays] = useState(14)
  const q = useMeta(mode, days)
  const status = useMetaStatus()
  const start = useStartMetaCrawl()
  const qc = useQueryClient()
  const running = status.data?.running ?? false
  const last = status.data?.last_crawl

  // When a crawl finishes, reload the stats.
  useEffect(() => {
    if (!running && last?.status === 'done') qc.invalidateQueries({ queryKey: ['meta'] })
  }, [running, last?.status, last?.id, qc])

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-4xl font-bold uppercase tracking-wide">Meta</h1>
          <p className="text-sm text-ink-2">Aggregated from the battle logs of the top Path of Legends players.</p>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-ink-3">
            {running && last
              ? `Crawling ${last.players_done}/${last.players_total} players…`
              : last
                ? `Last crawl ${timeAgo(last.finished_at ?? last.started_at)} · ${last.status}${last.source ? ` · ${last.source}` : ''}`
                : 'Never crawled'}
          </span>
          <button
            onClick={() => start.mutate()}
            disabled={running || start.isPending}
            className="rounded-md bg-accent px-4 py-2 font-semibold text-accent-ink hover:opacity-90 disabled:opacity-50"
          >
            {running ? 'Crawling…' : 'Refresh meta'}
          </button>
        </div>
      </header>
      {last?.status === 'failed' && <ErrorBox error={new Error(last.error ?? 'Crawl failed')} />}

      <div className="flex flex-wrap gap-3">
        <Segmented label="Mode" value={mode} onChange={setMode} options={[{ value: 'ranked', label: 'Ranked' }, { value: 'ladder', label: 'Top ladder' }, { value: 'all', label: 'Both' }]} />
        <Segmented label="Window" value={days} onChange={setDays} options={[{ value: 3, label: '3 days' }, { value: 7, label: '7 days' }, { value: 14, label: '14 days' }, { value: 30, label: '30 days' }]} />
      </div>

      {q.isPending && <Loading />}
      {q.isError && <ErrorBox error={q.error} />}
      {q.data && q.data.decks_observed === 0 && <Empty>No meta battles in this window. Hit “Refresh meta”; a crawl takes about 30 seconds.</Empty>}
      {q.data && q.data.decks_observed > 0 && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            <Stat label="Matches" value={q.data.matches} />
            <Stat label="Decks observed" value={q.data.decks_observed} />
            <Stat label="Archetypes" value={q.data.archetypes.length} />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Panel title="Top cards" subtitle="Usage = share of decks · bar = win rate">
              <ul className="space-y-1.5">
                {q.data.cards.slice(0, 20).map((c) => (
                  <li key={c.id} className="grid grid-cols-[2.5rem_minmax(0,1fr)_minmax(6rem,9rem)] items-center gap-3 text-sm">
                    <GameCard card={{ ...c, form: null }} size="sm" showLevel={false} />
                    <span className="truncate">
                      {c.name} <span className="text-xs text-ink-3">· {pct(c.usage)}{c.special_form_rate > 0 ? ` · ${pct(c.special_form_rate, 0)} evo/hero` : ''}</span>
                    </span>
                    <WinRateBar rate={c} compact />
                  </li>
                ))}
              </ul>
            </Panel>
            <Panel title="Archetypes">
              <ul className="space-y-1.5">
                {q.data.archetypes.slice(0, 15).map((a) => (
                  <li key={a.archetype} className="grid grid-cols-[minmax(0,1fr)_minmax(6rem,9rem)] items-center gap-3 text-sm">
                    <span className="truncate">
                      {a.archetype} <span className="text-xs text-ink-3">· {pct(a.usage)} · {a.games}g</span>
                    </span>
                    <WinRateBar rate={a} compact />
                  </li>
                ))}
              </ul>
            </Panel>
          </div>

          <Panel title="Top decks" subtitle="Exact 8-card lists seen at least 3 times">
            {q.data.top_decks.length ? (
              <ul className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {q.data.top_decks.map((d, i) => (
                  <li key={i} className="rounded-lg border border-line p-3">
                    <div className="mb-2 flex justify-between text-sm">
                      <span className="font-semibold">{d.archetype}</span>
                      <span className="num">
                        {pct(d.win_rate, 0)} <span className="text-ink-3">· {d.games}g</span>
                      </span>
                    </div>
                    <Deck cards={d.cards} size="sm" />
                  </li>
                ))}
              </ul>
            ) : (
              <Empty>No deck repeated 3+ times yet.</Empty>
            )}
          </Panel>
        </>
      )}
    </div>
  )
}
