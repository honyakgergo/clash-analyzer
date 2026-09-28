import { useProgress } from '../../api/hooks'
import type { Delta, Snapshot } from '../../api/types'
import { LineSeries } from '../../components/charts'
import { Empty, ErrorBox, Loading, Panel, Stat, Tone } from '../../components/ui'
import { dateTime, fmt, shortDate, signed } from '../../lib/format'
import { usePlayerCtx } from './context'

const SNAPSHOT_CHARTS: { key: keyof Snapshot; title: string }[] = [
  { key: 'trophies', title: 'Trophies' },
  { key: 'collection_level', title: 'Collection level' },
  { key: 'mastery_levels', title: 'Total mastery levels' },
  { key: 'avg_card_level', title: 'Average card level' },
]

function DeltaTiles({ label, d }: { label: string; d: Delta | null | undefined }) {
  if (!d) return null
  return (
    <Panel title={`Last ${label}`} subtitle={`since ${dateTime(d.since)}`}>
      <dl className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
        {(
          [
            ['Trophies', d.trophies],
            ['Wins', d.wins],
            ['Battles', d.battles],
            ['Collection lvl', d.collection_level],
            ['Mastery lvls', d.mastery_levels],
            ['Cards maxed', d.cards_maxed],
            ['King tower', d.king_tower_level],
          ] as const
        ).map(([k, v]) => (
          <div key={k} className="rounded-md bg-surface-2/60 px-3 py-2">
            <dt className="text-xs text-ink-3">{k}</dt>
            <dd className="num font-semibold">
              <Tone value={v}>{signed(v)}</Tone>
            </dd>
          </div>
        ))}
      </dl>
    </Panel>
  )
}

export default function ProgressTab() {
  const { tag, player } = usePlayerCtx()
  const q = useProgress(tag)
  if (q.isPending) return <Loading />
  if (q.isError) return <ErrorBox error={q.error} />
  const { snapshots, trophy_path: path, deltas } = q.data
  const s = player.summary

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Trophies" value={fmt(s.trophies)} hint={`${fmt(s.best_trophies - s.trophies)} below best`} />
        <Stat label="Collection level" value={fmt(s.collection_level)} />
        <Stat label="Snapshots" value={snapshots.length} hint="one per hour at most" />
        <Stat label="Battles stored" value={player.battles_stored} />
      </div>

      <Panel title="Trophy path" subtitle="Rebuilt from every stored ladder/ranked battle (trophies after each game)">
        {path.length > 1 ? (
          <LineSeries
            data={path}
            x="time"
            y="trophies"
            xFormat={(v) => shortDate(String(v))}
            yFormat={(v) => fmt(v)}
            tooltip={(r) => [`${fmt(r.trophies as number)} trophies`, `${r.result} ${signed(r.change as number)}`]}
            label="Trophies after each battle"
            height={260}
          />
        ) : (
          <Empty>Need at least two ladder battles with trophy data.</Empty>
        )}
      </Panel>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <DeltaTiles label="day" d={deltas.day} />
        <DeltaTiles label="week" d={deltas.week} />
      </div>

      {snapshots.length > 1 ? (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {SNAPSHOT_CHARTS.map(({ key, title }) => (
            <Panel key={key} title={title}>
              <LineSeries
                data={snapshots as unknown as Record<string, unknown>[]}
                x="time"
                y={key}
                xFormat={(v) => shortDate(String(v))}
                label={`${title} over time`}
                height={180}
              />
            </Panel>
          ))}
        </div>
      ) : (
        <Empty>
          Profile snapshots build up over time. Only {snapshots.length} so far. Track this player and check back tomorrow for trend lines.
        </Empty>
      )}
    </div>
  )
}
