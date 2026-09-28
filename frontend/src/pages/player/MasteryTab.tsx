import { useMastery } from '../../api/hooks'
import type { Badge } from '../../api/types'
import { ErrorBox, Loading, Panel, ProgressBar, Stat } from '../../components/ui'
import { fmt, prettyKey } from '../../lib/format'
import { usePlayerCtx } from './context'

function MasteryRow({ m }: { m: Badge }) {
  return (
    <li className="grid grid-cols-[2.5rem_minmax(0,1fr)] items-center gap-3 py-1.5">
      {m.card_icon ? <img src={m.card_icon} alt="" className="h-11 w-9 object-contain" loading="lazy" /> : <span />}
      <div className="min-w-0">
        <div className="flex justify-between gap-2 text-sm">
          <span className="truncate">{m.card}</span>
          <span className="num shrink-0 text-xs text-ink-3">
            lvl {m.level}/{m.max_level}
            {!m.maxed && m.target ? ` · ${fmt(m.progress)}/${fmt(m.target)}` : ''}
          </span>
        </div>
        <div className="mt-1">
          <ProgressBar value={m.maxed ? 1 : m.completion} label={`${m.card} mastery`} />
        </div>
      </div>
    </li>
  )
}

export default function MasteryTab() {
  const { tag } = usePlayerCtx()
  const q = useMastery(tag)
  if (q.isPending) return <Loading />
  if (q.isError) return <ErrorBox error={q.error} />
  const d = q.data

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Mastery levels" value={fmt(d.mastery_total_levels)} />
        <Stat label="Masteries maxed" value={d.mastery_maxed} hint={`of ${d.mastery_started} started`} />
        <Stat label="Not started" value={d.cards_without_mastery} hint="cards with no mastery progress" />
        <Stat label="Achievements" value={`${d.achievements.filter((a) => a.stars === 3).length}/${d.achievements.length}`} hint="at 3 stars" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel title="Closest to next mastery level" subtitle="Quick mastery rewards: play these next">
          <ul>{d.closest_mastery.map((m) => <MasteryRow key={m.badge} m={m} />)}</ul>
        </Panel>
        <Panel title="Badges">
          <ul className="space-y-2.5">
            {d.badges.map((b) => (
              <li key={b.badge} className="grid grid-cols-[2.5rem_minmax(0,1fr)] items-center gap-3">
                {b.icon ? <img src={b.icon} alt="" className="h-9 w-9 object-contain" loading="lazy" /> : <span />}
                <div className="min-w-0">
                  <div className="flex justify-between gap-2 text-sm">
                    <span className="truncate">{prettyKey(b.badge)}</span>
                    <span className="num shrink-0 text-xs text-ink-3">
                      {b.level != null ? `lvl ${b.level}/${b.max_level}` : ''} {b.target ? `· ${fmt(b.progress)}/${fmt(b.target)}` : `· ${fmt(b.progress)}`}
                    </span>
                  </div>
                  <div className="mt-1">
                    <ProgressBar value={b.maxed ? 1 : b.completion} label={prettyKey(b.badge)} />
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <Panel title="Achievements">
        <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {d.achievements.map((a) => (
            <li key={a.name} className="rounded-lg border border-line p-3">
              <div className="flex justify-between text-sm">
                <span className="font-medium">{a.name}</span>
                <span aria-label={`${a.stars} of 3 stars`} className="text-accent">
                  {'★'.repeat(a.stars)}
                  <span className="text-ink-3">{'☆'.repeat(3 - a.stars)}</span>
                </span>
              </div>
              <p className="mb-2 text-xs text-ink-3">{a.info}</p>
              <ProgressBar value={a.completion} label={a.name} />
              <p className="num mt-1 text-right text-xs text-ink-3">
                {fmt(a.value)} / {fmt(a.target)}
              </p>
            </li>
          ))}
        </ul>
      </Panel>

      <Panel title={`All masteries (${d.mastery.length})`}>
        <ul className="grid grid-cols-1 gap-x-8 md:grid-cols-2 xl:grid-cols-3">
          {d.mastery.map((m) => (
            <MasteryRow key={m.badge} m={m} />
          ))}
        </ul>
      </Panel>
    </div>
  )
}
