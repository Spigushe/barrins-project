import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import { AdminRoute } from '@/components/layout/AdminRoute'
import { AppShell } from '@/components/layout/AppShell'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import { useSession } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { LoginPage } from '@/pages/LoginPage'
import { VerifyEmailPage } from '@/pages/VerifyEmailPage'
import { MetagameTab } from '@/pages/MetagameTab'
import { SessionsTab } from '@/pages/SessionsTab'
import { SuiviBo3Tab } from '@/pages/SuiviBo3Tab'
import { DecklistTab } from '@/pages/DecklistTab'
import { TeamsTab } from '@/pages/TeamsTab'
import { TeamsIndexRedirect } from '@/pages/TeamsIndexRedirect'
import { TeamCreateJoinPage } from '@/pages/TeamCreateJoinPage'
import { TeamPage } from '@/pages/TeamPage'
import { AdminMetricsPage } from '@/pages/AdminMetricsPage'
import { DemoPage } from '@/demo/DemoPage'

function RootRedirect() {
  const session = useSession()

  if (session.accessToken !== null) {
    return <Navigate to="/app/metagame" replace />
  }

  // Unauthenticated: offer the demo (S7) alongside the login page, instead
  // of redirecting straight to /login.
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-xl font-extrabold text-foreground">Tamiyo Scroll</h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        Competitive MTG tracker for Duel Commander — log in to your account, or explore a
        sample deck in the demo first.
      </p>
      <div className="flex gap-3">
        <Button type="button" asChild>
          <Link to="/login">Log in</Link>
        </Button>
        <Button type="button" variant="outline" asChild>
          <Link to="/demo">Try the demo</Link>
        </Button>
      </div>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/demo" element={<DemoPage />} />

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
          path="/app/tracker"
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
        <Route
          path="/app/sessions"
          element={
            <ProtectedRoute>
              <AppShell>
                <SessionsTab />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/app/team"
          element={
            <ProtectedRoute>
              <AppShell>
                <TeamsTab />
              </AppShell>
            </ProtectedRoute>
          }
        >
          <Route index element={<TeamsIndexRedirect />} />
          <Route path="new" element={<TeamCreateJoinPage />} />
          <Route path=":teamId" element={<TeamPage />} />
        </Route>

        <Route
          path="/app/admin/metrics"
          element={
            <ProtectedRoute>
              <AdminRoute>
                <AdminMetricsPage />
              </AdminRoute>
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<RootRedirect />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
