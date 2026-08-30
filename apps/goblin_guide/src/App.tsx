import type { ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useIdentity } from '@barrins/goblin-guide'
import { ForgotPasswordRoute } from './ForgotPasswordRoute'
import { LoginRoute } from './LoginRoute'
import { ResetPasswordRoute } from './ResetPasswordRoute'
import { Shell } from './Shell'
import { SignupRoute } from './SignupRoute'
import { VerifyEmailRoute } from './VerifyEmailRoute'

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
        <Route path="/signup" element={<SignupRoute />} />
        <Route path="/verify-email" element={<VerifyEmailRoute />} />
        <Route path="/forgot-password" element={<ForgotPasswordRoute />} />
        <Route path="/reset-password" element={<ResetPasswordRoute />} />
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
