import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as personalDecksApi from '@/api/personalDecks'
import { useViewingOwner } from './useViewingOwner'

export function usePersonalDecks() {
  const owner = useViewingOwner()
  return useQuery({
    queryKey: ['personal-decks', owner?.id ?? 'self'],
    queryFn: () => personalDecksApi.listPersonalDecks(),
  })
}

export function useCreatePersonalDeck() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: personalDecksApi.createPersonalDeck,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['personal-decks'] })
    },
  })
}

export function useArchivePersonalDeck() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: personalDecksApi.archivePersonalDeck,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['personal-decks'] })
    },
  })
}
