import type { ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useIdentity } from '@barrins/goblin-guide'
import { ConfirmEmailChangeRoute } from './ConfirmEmailChangeRoute'
import { ForgotPasswordRoute } from './ForgotPasswordRoute'
import { LoginRoute } from './LoginRoute'
import { ResetPasswordRoute } from './ResetPasswordRoute'
import { ServiceAccountsRoute } from './ServiceAccountsRoute'
import { Shell } from './Shell'
import { SignupRoute } from './SignupRoute'
import { VerifyEmailRoute } from './VerifyEmailRoute'

function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useIdentity()
  const location = useLocation()
  if (!isAuthenticated) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${next}`} replace />
  }
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
          path="/confirm-email-change"
          element={
            <RequireAuth>
              <ConfirmEmailChangeRoute />
            </RequireAuth>
          }
        />
        <Route
          path="/service-accounts"
          element={
            <RequireAuth>
              <ServiceAccountsRoute />
            </RequireAuth>
          }
        />
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
