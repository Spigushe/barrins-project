import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useSession } from '@/hooks/useAuth'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const session = useSession()
  if (session.accessToken === null) {
    return <Navigate to="/login" replace />
  }
  return children
}
