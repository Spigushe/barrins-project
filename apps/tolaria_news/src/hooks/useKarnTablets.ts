import { useQuery } from '@tanstack/react-query'
import { getMetagame, getArchetypes, getTrends } from '@/api/karnTablets'
import type { WindowMode } from '@/schemas/karnTablets'

export function useMetagame(windowMode: WindowMode) {
  return useQuery({
    queryKey: ['metagame', windowMode],
    queryFn: () => getMetagame(windowMode),
  })
}

export function useArchetypes(windowMode: WindowMode) {
  return useQuery({
    queryKey: ['archetypes', windowMode],
    queryFn: () => getArchetypes(windowMode),
  })
}

export function useTrends(windowMode: WindowMode) {
  return useQuery({
    queryKey: ['trends', windowMode],
    queryFn: () => getTrends(windowMode),
  })
}
