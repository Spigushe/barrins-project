import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useIdentity } from '@barrins/goblin-guide'
import { SessionBootSplash } from '@/components/layout/SessionBootSplash'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isBootstrapping } = useIdentity()
  const location = useLocation()

  // Cookie mode restores the session from the HttpOnly cookie on load (ADR-18)
  // — wait for that before bouncing to /login, or a reload of a protected
  // page flashes the login screen.
  if (isBootstrapping) return <SessionBootSplash />

  if (!isAuthenticated) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${next}`} replace />
  }

  return children
}
