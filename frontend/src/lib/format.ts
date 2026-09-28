const nf = new Intl.NumberFormat('en-US')

export const fmt = (n: number | null | undefined): string => (n == null ? '–' : nf.format(n))

export const pct = (n: number | null | undefined, digits = 1): string =>
  n == null ? '–' : `${n.toFixed(digits)}%`

export const signed = (n: number | null | undefined, digits = 0): string => {
  if (n == null) return '–'
  const s = n.toFixed(digits)
  return n > 0 ? `+${s}` : s
}

/** 1_234_567 -> "1.23M", 45_000 -> "45k" */
export function compact(n: number | null | undefined): string {
  if (n == null) return '–'
  const abs = Math.abs(n)
  if (abs >= 1e6) return `${(n / 1e6).toFixed(abs >= 1e7 ? 1 : 2)}M`
  if (abs >= 1e4) return `${Math.round(n / 1e3)}k`
  if (abs >= 1e3) return `${(n / 1e3).toFixed(1)}k`
  return String(n)
}

export function timeAgo(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return 'never'
  const s = Math.round((now.getTime() - new Date(iso).getTime()) / 1000)
  if (s < 60) return 'just now'
  const m = Math.round(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.round(m / 60)
  if (h < 48) return `${h}h ago`
  return `${Math.round(h / 24)}d ago`
}

export const shortDate = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

export const dateTime = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

export const MODE_LABEL: Record<string, string> = {
  competitive: 'Ladder + Ranked',
  all: 'All modes',
  ladder: 'Ladder',
  ranked: 'Ranked',
  seasonal: 'Seasonal Trophy Road',
  war: 'Clan War',
  '2v2': '2v2',
  event: 'Events & Tournaments',
  tournament: 'Tournament',
  friendly: 'Friendly',
  other: 'Other',
}

export const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

/** "MasteryHogRider"-style internal names -> "Hog Rider"; also prettifies progress keys. */
export function prettyKey(key: string): string {
  if (!key) return 'Merge Tactics'
  return key
    .replace(/^AutoChess/, 'Merge Tactics')
    .replace(/[-_]/g, ' ')
    .replace(/([a-z])([A-Z0-9])/g, '$1 $2')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b[a-z]/g, (c) => c.toUpperCase())
}
