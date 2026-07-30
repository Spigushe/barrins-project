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

export function useAvailableSharers() {
  return useQuery({
    queryKey: ['settings', 'available-sharers'],
    queryFn: settingsApi.listAvailableSharers,
  })
}

function useInvalidateSharerQueries() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: ['settings', 'available-sharers'] })
    void queryClient.invalidateQueries({ queryKey: ['settings', 'shared-users'] })
  }
}

export function useCreateReceiveOptIn() {
  const invalidate = useInvalidateSharerQueries()
  return useMutation({
    mutationFn: settingsApi.createReceiveOptIn,
    onSuccess: invalidate,
  })
}

export function useDeleteReceiveOptIn() {
  const invalidate = useInvalidateSharerQueries()
  return useMutation({
    mutationFn: settingsApi.deleteReceiveOptIn,
    onSuccess: invalidate,
  })
}
