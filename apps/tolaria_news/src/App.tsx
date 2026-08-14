import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { FeatureGate } from '@/components/layout/FeatureGate'
import { LandingPage } from '@/pages/LandingPage'
import { TournamentListPage } from '@/pages/TournamentListPage'
import { TournamentDetailPage } from '@/pages/TournamentDetailPage'
import { DeckDetailPage } from '@/pages/DeckDetailPage'
import { MetagamePage } from '@/pages/MetagamePage'
import { ArchetypesPage } from '@/pages/ArchetypesPage'
import { TrendsPage } from '@/pages/TrendsPage'

function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/tournaments" element={<TournamentListPage />} />
          <Route path="/tournaments/:id" element={<TournamentDetailPage />} />
          <Route path="/decks/:id" element={<DeckDetailPage />} />

          {/* Karn Tablets (T4 iteration 2 / T6, ADR-13) — prepared ahead of
              the backend, hidden behind VITE_FEATURE_KARN_TABLETS. */}
          <Route
            path="/metagame"
            element={
              <FeatureGate>
                <MetagamePage />
              </FeatureGate>
            }
          />
          <Route
            path="/archetypes"
            element={
              <FeatureGate>
                <ArchetypesPage />
              </FeatureGate>
            }
          />
          <Route
            path="/trends"
            element={
              <FeatureGate>
                <TrendsPage />
              </FeatureGate>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  )
}

export default App
