import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { tagPath } from '../lib/tags'
import { api } from './client'
import type {
  AnalyticsResponse,
  Battle,
  Chest,
  ClanResponse,
  Health,
  MasteryResponse,
  MetaCompareResponse,
  MetaResponse,
  MetaStatus,
  PlayerResponse,
  ProgressResponse,
  TrackedPlayer,
  UpgradesResponse,
} from './types'

const TZ = Intl.DateTimeFormat().resolvedOptions().timeZone

export const useHealth = () => useQuery({ queryKey: ['health'], queryFn: () => api.get<Health>('/health') })

export const useTracked = () =>
  useQuery({ queryKey: ['tracked'], queryFn: () => api.get<TrackedPlayer[]>('/players/tracked') })

export const usePlayer = (tag: string) =>
  useQuery({ queryKey: ['player', tag], queryFn: () => api.get<PlayerResponse>(`/players/${tagPath(tag)}`) })

// Sub-resources wait for the profile query so the backend ingests once, not in parallel.
function usePlayerSub<T>(tag: string, key: string, path: string, params: Record<string, unknown> = {}) {
  const player = usePlayer(tag)
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '') as [string, string][],
  ).toString()
  return useQuery({
    queryKey: ['player', tag, key, params],
    queryFn: () => api.get<T>(`/players/${tagPath(tag)}/${path}${qs ? `?${qs}` : ''}`),
    enabled: player.isSuccess,
  })
}

export const useAnalytics = (tag: string, mode: string, days: number | null) =>
  usePlayerSub<AnalyticsResponse>(tag, 'analytics', 'analytics', { mode, days, tz: TZ })

export const useProgress = (tag: string) => usePlayerSub<ProgressResponse>(tag, 'progress', 'progress')

export const useUpgrades = (tag: string, targetLevel: number) =>
  usePlayerSub<UpgradesResponse>(tag, 'upgrades', 'upgrades', { target_level: targetLevel })

export const useMastery = (tag: string) => usePlayerSub<MasteryResponse>(tag, 'mastery', 'mastery')

export const useChests = (tag: string) => usePlayerSub<Chest[]>(tag, 'chests', 'chests')

export const useBattles = (tag: string, mode: string, limit = 25) =>
  usePlayerSub<{ items: Battle[] }>(tag, 'battles', 'battles', { mode, limit })

export const useMetaCompare = (tag: string, mode: string, days: number) =>
  usePlayerSub<MetaCompareResponse>(tag, 'meta-compare', 'meta-compare', { mode, days })

export const useClan = (tag: string) =>
  useQuery({ queryKey: ['clan', tag], queryFn: () => api.get<ClanResponse>(`/clans/${tagPath(tag)}`) })

export const useMeta = (mode: string, days: number) =>
  useQuery({ queryKey: ['meta', mode, days], queryFn: () => api.get<MetaResponse>(`/meta?mode=${mode}&days=${days}`) })

export const useMetaStatus = () =>
  useQuery({
    queryKey: ['meta-status'],
    queryFn: () => api.get<MetaStatus>('/meta/status'),
    refetchInterval: (q) => (q.state.data?.running ? 1500 : false),
  })

export function useStartMetaCrawl() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<{ started: boolean }>('/meta/refresh'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['meta-status'] }),
  })
}

export function useRefreshPlayer(tag: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<{ new_battles: number }>(`/players/${tagPath(tag)}/refresh`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['player', tag] }),
  })
}

export function useTrackToggle(tag: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (track: boolean) =>
      track ? api.post(`/players/${tagPath(tag)}/track`) : api.del(`/players/${tagPath(tag)}/track`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['player', tag] })
      qc.invalidateQueries({ queryKey: ['tracked'] })
    },
  })
}
