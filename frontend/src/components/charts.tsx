import type { ReactNode } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

// Single-series charts only (one axis, slot-1 color). Separate measures get separate charts.

// Rows are plain objects; fields are read by key.
type Row = Record<string, unknown>
type Data = readonly object[]

function TooltipBox({ title, lines }: { title: ReactNode; lines: ReactNode[] }) {
  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-2 text-xs shadow-lg">
      <div className="mb-1 font-semibold text-ink">{title}</div>
      {lines.map((l, i) => (
        <div key={i} className="num text-ink-2">
          {l}
        </div>
      ))}
    </div>
  )
}

export function LineSeries({
  data,
  x,
  y,
  xFormat = (v) => String(v),
  yFormat = (v) => String(v),
  tooltip,
  height = 220,
  label,
}: {
  data: Data
  x: string
  y: string
  xFormat?: (v: unknown) => string
  yFormat?: (v: number) => string
  tooltip?: (row: Row) => ReactNode[]
  height?: number
  label: string
}) {
  return (
    <div role="img" aria-label={label} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data as unknown as Row[]} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey={x} tickFormatter={xFormat} minTickGap={32} tickLine={false} />
          <YAxis
            domain={['auto', 'auto']}
            tickFormatter={yFormat}
            width={52}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ stroke: 'var(--text-3)', strokeWidth: 1 }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <TooltipBox
                  title={xFormat(payload[0].payload[x])}
                  lines={tooltip ? tooltip(payload[0].payload) : [yFormat(payload[0].value as number)]}
                />
              ) : null
            }
          />
          <Line
            type="monotone"
            dataKey={y}
            stroke="var(--series-1)"
            strokeWidth={2}
            dot={data.length <= 40 ? { r: 3, fill: 'var(--series-1)', stroke: 'var(--surface)', strokeWidth: 2 } : false}
            activeDot={{ r: 5, stroke: 'var(--surface)', strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Win-rate bars with a 50% reference line; empty buckets render as gaps. */
export function WinRateBars({
  data,
  x,
  xFormat = (v) => String(v),
  height = 200,
  label,
}: {
  data: readonly (object & { win_rate: number | null; games: number })[]
  x: string
  xFormat?: (v: unknown) => string
  height?: number
  label: string
}) {
  return (
    <div role="img" aria-label={label} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data as unknown as Row[]} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barCategoryGap={2}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey={x} tickFormatter={xFormat} tickLine={false} interval="preserveStartEnd" />
          <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={(v) => `${v}%`} width={40} axisLine={false} tickLine={false} />
          <ReferenceLine y={50} stroke="var(--text-3)" strokeOpacity={0.6} />
          <Tooltip
            cursor={{ fill: 'var(--surface-2)' }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const r = payload[0].payload as Row & { win_rate: number | null; games: number; wins?: number; ci_low?: number; ci_high?: number }
              return (
                <TooltipBox
                  title={xFormat(r[x])}
                  lines={
                    r.games
                      ? [`Win rate ${r.win_rate}%`, `${r.wins ?? '?'} W / ${r.games} games`, r.ci_low != null ? `95% CI ${r.ci_low}–${r.ci_high}%` : '']
                      : ['No games']
                  }
                />
              )
            }}
          />
          <Bar dataKey="win_rate" fill="var(--series-1)" radius={[4, 4, 0, 0]} isAnimationActive={false} maxBarSize={36} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Signed bars around zero (e.g. daily net trophies): diverging poles, neutral axis. */
export function SignedBars({
  data,
  x,
  y,
  xFormat = (v) => String(v),
  height = 180,
  label,
}: {
  data: Data
  x: string
  y: string
  xFormat?: (v: unknown) => string
  height?: number
  label: string
}) {
  return (
    <div role="img" aria-label={label} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data as unknown as Row[]} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barCategoryGap={2}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey={x} tickFormatter={xFormat} tickLine={false} minTickGap={24} />
          <YAxis width={44} axisLine={false} tickLine={false} />
          <ReferenceLine y={0} stroke="var(--text-3)" />
          <Tooltip
            cursor={{ fill: 'var(--surface-2)' }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <TooltipBox title={xFormat(payload[0].payload[x])} lines={[`${(payload[0].value as number) > 0 ? '+' : ''}${payload[0].value} trophies`]} />
              ) : null
            }
          />
          <Bar
            dataKey={y}
            isAnimationActive={false}
            maxBarSize={24}
            radius={[4, 4, 4, 4]}
            shape={(props: unknown) => {
              const p = props as { x: number; y: number; width: number; height: number; value: number }
              const h = Math.abs(p.height)
              const top = p.height < 0 ? p.y + p.height : p.y
              return <rect x={p.x} y={top} width={p.width} height={h} rx={3} fill={p.value >= 0 ? 'var(--div-pos)' : 'var(--div-neg)'} />
            }}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
