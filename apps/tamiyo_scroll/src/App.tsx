import {
  BrowserRouter,
  Link,
  Navigate,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom'
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
    return <Navigate to="/tracker" replace />
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

/** Old `/app/*` links (bookmarks, shared URLs from before routes were
 * flattened to the top level) still resolve — redirects to the same
 * path with the `/app` prefix stripped, preserving any query string.
 * Exported for `App.test.tsx` — the redirect target-computation is the
 * one piece of new logic in this file worth testing directly. */
export function AppPrefixRedirect() {
  const location = useLocation()
  const target = location.pathname.replace(/^\/app/, '') || '/'
  return <Navigate to={`${target}${location.search}`} replace />
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
          path="/metagame"
          element={
            <ProtectedRoute>
              <AppShell>
                <MetagameTab />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/tracker"
          element={
            <ProtectedRoute>
              <AppShell>
                <SuiviBo3Tab />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/decklist"
          element={
            <ProtectedRoute>
              <AppShell>
                <DecklistTab />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/sessions"
          element={
            <ProtectedRoute>
              <AppShell>
                <SessionsTab />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/team"
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
          path="/admin/metrics"
          element={
            <ProtectedRoute>
              <AdminRoute>
                <AdminMetricsPage />
              </AdminRoute>
            </ProtectedRoute>
          }
        />

        <Route path="/app/*" element={<AppPrefixRedirect />} />
        <Route path="*" element={<RootRedirect />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
