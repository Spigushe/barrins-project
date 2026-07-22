import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import { useSession } from '@/hooks/useAuth'
import { LoginPage } from '@/pages/LoginPage'
import { VerifyEmailPage } from '@/pages/VerifyEmailPage'
import { MetagameTab } from '@/pages/MetagameTab'
import { SuiviBo3Tab } from '@/pages/SuiviBo3Tab'
import { DecklistTab } from '@/pages/DecklistTab'

function RootRedirect() {
  const session = useSession()
  return (
    <Navigate to={session.accessToken !== null ? '/app/metagame' : '/login'} replace />
  )
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />

        <Route
          path="/app/metagame"
          element={
            <ProtectedRoute>
              <AppShell>
                <MetagameTab />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/app/suivi-bo3"
          element={
            <ProtectedRoute>
              <AppShell>
                <SuiviBo3Tab />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/app/decklist"
          element={
            <ProtectedRoute>
              <AppShell>
                <DecklistTab />
              </AppShell>
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<RootRedirect />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
