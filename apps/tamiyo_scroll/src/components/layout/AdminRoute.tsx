import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useCurrentUser } from '@/hooks/useAuth'

/** Gates a route to admin users only (S6). Nest inside `ProtectedRoute` —
 * this assumes an authenticated session already exists and only adds the
 * role check on top of it. */
export function AdminRoute({ children }: { children: ReactNode }) {
  const { data: currentUser, isLoading } = useCurrentUser()

  // Avoid a flash-redirect while /auth/me is still in flight — role isn't
  // known yet, so neither render the page nor bounce the user away.
  if (isLoading) return null

  if (currentUser?.role !== 'admin') {
    return <Navigate to="/app/metagame" replace />
  }

  return children
}
