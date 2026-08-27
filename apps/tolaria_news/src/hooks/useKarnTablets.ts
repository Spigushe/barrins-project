import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { getMetagame, getArchetypes, getTrends } from '@/api/karnTablets'
import type { WindowMode } from '@/schemas/karnTablets'

export function useMetagame(windowMode: WindowMode, at?: string) {
  return useQuery({
    queryKey: ['metagame', windowMode, at ?? null],
    queryFn: () => getMetagame(windowMode, at),
    placeholderData: keepPreviousData,
  })
}

export function useArchetypes(windowMode: WindowMode, at?: string, cursor?: string) {
  return useQuery({
    queryKey: ['archetypes', windowMode, at ?? null, cursor ?? null],
    queryFn: () => getArchetypes(windowMode, at, cursor),
    // Keep the current page on screen while the next one loads.
    placeholderData: keepPreviousData,
  })
}

export function useTrends(windowMode: WindowMode) {
  return useQuery({
    queryKey: ['trends', windowMode],
    queryFn: () => getTrends(windowMode),
  })
}
