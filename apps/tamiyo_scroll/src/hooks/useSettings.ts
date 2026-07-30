import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as settingsApi from '@/api/settings'

export function useMySettings() {
  return useQuery({
    queryKey: ['settings', 'me'],
    queryFn: settingsApi.getMySettings,
  })
}

export function useUpdateMySettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: settingsApi.updateMySettings,
    onSuccess: (settings) => {
      queryClient.setQueryData(['settings', 'me'], settings)
      // data_shared/receive_shared_data change what sharing_merge.py
      // returns for every one of these — without this, toggling sharing
      // off then on shows stale merge results (e.g. an archived-deck
      // fallback line that doesn't reappear) until something unrelated
      // happens to refetch them.
      void queryClient.invalidateQueries({ queryKey: ['matches'] })
      void queryClient.invalidateQueries({ queryKey: ['meta-decks'] })
      void queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}
