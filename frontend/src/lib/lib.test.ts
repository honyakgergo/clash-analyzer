import { describe, expect, it } from 'vitest'

import { compact, fmt, pct, prettyKey, signed, timeAgo } from './format'
import { cleanTag, tagPath } from './tags'

describe('cleanTag', () => {
  it.each(['#PQGGV0JP', 'pqggvojp', ' ##pqggv0jp ', '%23PQGGV0JP'])('normalizes %s', (raw) => {
    expect(cleanTag(raw)).toBe('PQGGV0JP')
  })
  it.each(['', '#', 'AB', 'HELLO123', 'PQGG V0JP'])('rejects %s', (raw) => {
    expect(cleanTag(raw)).toBeNull()
  })
  it('builds a path segment without #', () => {
    expect(tagPath('#pqggvojp')).toBe('PQGGV0JP')
  })
})

describe('format', () => {
  it('formats numbers and placeholders', () => {
    expect(fmt(12345)).toBe('12,345')
    expect(fmt(null)).toBe('–')
    expect(pct(55.66)).toBe('55.7%')
    expect(signed(5)).toBe('+5')
    expect(signed(-3)).toBe('-3')
    expect(signed(0)).toBe('0')
  })
  it('compacts large numbers', () => {
    expect(compact(840000)).toBe('840k')
    expect(compact(37418000)).toBe('37.4M')
    expect(compact(2543000)).toBe('2.54M')
    expect(compact(1500)).toBe('1.5k')
    expect(compact(12)).toBe('12')
  })
  it('renders relative time', () => {
    const now = new Date('2026-09-28T12:00:00Z')
    expect(timeAgo('2026-09-28T11:59:30Z', now)).toBe('just now')
    expect(timeAgo('2026-09-28T11:30:00Z', now)).toBe('30m ago')
    expect(timeAgo('2026-09-28T02:00:00Z', now)).toBe('10h ago')
    expect(timeAgo('2026-09-20T12:00:00Z', now)).toBe('8d ago')
    expect(timeAgo(null, now)).toBe('never')
  })
  it('prettifies internal keys', () => {
    expect(prettyKey('seasonal-trophy-road-202609')).toBe('Seasonal Trophy Road 202609')
    expect(prettyKey('AutoChess_2026_Season_11')).toBe('Merge Tactics 2026 Season 11')
    expect(prettyKey('MasteryHogRider')).toBe('Mastery Hog Rider')
    expect(prettyKey('')).toBe('Merge Tactics')
  })
})
