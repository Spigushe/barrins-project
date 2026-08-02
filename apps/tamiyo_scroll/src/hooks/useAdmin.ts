import { useQuery } from '@tanstack/react-query'
import * as adminApi from '@/api/admin'
import { useCurrentUser } from './useAuth'

export function usePlatformMetrics() {
  const { data: currentUser } = useCurrentUser()
  return useQuery({
    queryKey: ['admin', 'metrics'],
    queryFn: () => adminApi.getPlatformMetrics(),
    // Only an admin can call this endpoint (backend 403s otherwise) — no
    // point firing the request before we know the current user's role.
    enabled: currentUser?.role === 'admin',
  })
}
