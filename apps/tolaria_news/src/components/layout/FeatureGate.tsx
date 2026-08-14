import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { karnTabletsEnabled } from '@/lib/featureFlags'

/**
 * Single source of truth for hiding the Karn-Tablets-tied pages
 * (Metagame/Archetypes/Trends, T4 iteration 2 — ADR-13, not shipped yet):
 * wraps their route elements and bounces to "/" when the flag is off, so
 * there's no separate "nav link hidden but the route still resolves" gap.
 * AppShell's nav uses the same flag to decide whether to render the links.
 */
export function FeatureGate({ children }: { children: ReactNode }) {
  if (!karnTabletsEnabled) return <Navigate to="/" replace />
  return children
}
