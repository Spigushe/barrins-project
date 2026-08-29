import type { ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useIdentity } from '@barrins/goblin-guide'
import { LoginRoute } from './LoginRoute'
import { Shell } from './Shell'

function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useIdentity()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginRoute />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Shell />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
