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
    },
  })
}

export function useSharedUsers() {
  return useQuery({
    queryKey: ['settings', 'shared-users'],
    queryFn: settingsApi.listSharedUsers,
  })
}
