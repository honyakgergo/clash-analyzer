import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { useClan } from '../api/hooks'
import type { ClanMember } from '../api/types'
import { ErrorBox, Loading, Panel, Segmented, Stat } from '../components/ui'
import { fmt, timeAgo } from '../lib/format'

type Sort = 'rank' | 'war' | 'inactive' | 'donations'

export default function ClanPage() {
  const { tag = '' } = useParams()
  const q = useClan(tag)
  const [sort, setSort] = useState<Sort>('rank')

  const members = useMemo(() => {
    const list = [...(q.data?.members ?? [])]
    const key: Record<Sort, (m: ClanMember) => number> = {
      rank: (m) => m.clan_rank,
      war: (m) => -m.war_fame,
      inactive: (m) => -(m.days_inactive ?? 0),
      donations: (m) => -m.donations,
    }
    return list.sort((a, b) => key[sort](a) - key[sort](b))
  }, [q.data, sort])

  if (q.isPending) return <Loading />
  if (q.isError) return <ErrorBox error={q.error} />
  const c = q.data
  const race = c.river_race
  const inactive = c.members.filter((m) => (m.days_inactive ?? 0) >= 7).length

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-4xl font-bold uppercase tracking-wide">{c.name}</h1>
        <p className="text-sm text-ink-2">
          <span className="font-mono">{c.tag}</span> · {c.location} · {c.type} · requires {fmt(c.required_trophies)} 🏆
        </p>
        {c.description && <p className="mt-2 max-w-2xl text-sm text-ink-3">{c.description}</p>}
      </header>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <Stat label="Members" value={`${c.member_count}/50`} />
        <Stat label="Clan score" value={fmt(c.clan_score)} />
        <Stat label="War trophies" value={fmt(c.war_trophies)} />
        <Stat label="Donations/week" value={fmt(c.donations_per_week)} />
        <Stat label="Inactive 7d+" value={inactive} tone={inactive > 5 ? 'bad' : undefined} hint="kick candidates" />
      </div>

      {race && (
        <Panel
          title="River race"
          subtitle={`${race.period_type ?? '–'}${race.is_war_day ? ` · ${race.members_missing_decks_today} members haven't used all ${race.decks_per_day} decks today` : ''}`}
        >
          <ol className="space-y-1.5 text-sm">
            {race.standings.map((s, i) => (
              <li key={s.tag} className={`flex justify-between rounded px-2 py-1 ${s.is_us ? 'bg-accent/15 font-semibold' : ''}`}>
                <span>
                  {i + 1}. {s.name} {s.finished && <span className="text-good-ink">✓ finished</span>}
                </span>
                <span className="num">{fmt(s.fame)} fame</span>
              </li>
            ))}
          </ol>
        </Panel>
      )}

      <Panel
        title="Members"
        action={
          <Segmented
            label="Sort members"
            value={sort}
            onChange={setSort}
            options={[
              { value: 'rank', label: 'Trophies' },
              { value: 'war', label: 'War fame' },
              { value: 'donations', label: 'Donations' },
              { value: 'inactive', label: 'Inactive' },
            ]}
          />
        }
      >
        <div className="-mx-4 overflow-x-auto px-4">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="text-left text-xs uppercase tracking-wider text-ink-3">
              <tr>
                <th className="py-2 pr-3">Player</th>
                <th className="py-2 pr-3 text-right">Trophies</th>
                <th className="py-2 pr-3 text-right">Donated</th>
                <th className="py-2 pr-3 text-right">War fame</th>
                <th className="py-2 pr-3 text-right">Decks today</th>
                <th className="py-2 text-right">Last seen</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.tag} className="border-t border-line">
                  <td className="py-2 pr-3">
                    <Link to={`/player/${m.tag.replace('#', '')}`} className="font-medium hover:text-accent">
                      {m.name}
                    </Link>
                    <span className="ml-2 text-xs text-ink-3">{m.role}</span>
                  </td>
                  <td className="num py-2 pr-3 text-right">{fmt(m.trophies)}</td>
                  <td className="num py-2 pr-3 text-right">{fmt(m.donations)}</td>
                  <td className="num py-2 pr-3 text-right">{fmt(m.war_fame)}</td>
                  <td className={`num py-2 pr-3 text-right ${race?.is_war_day && m.war_decks_today < race.decks_per_day ? 'text-critical' : ''}`}>
                    {m.war_decks_today}/{race?.decks_per_day ?? 4}
                  </td>
                  <td className={`py-2 text-right ${(m.days_inactive ?? 0) >= 7 ? 'text-critical' : 'text-ink-3'}`}>{timeAgo(m.last_seen)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}
