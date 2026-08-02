import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { vi } from 'vitest'
import { AdminRoute } from './AdminRoute'

let currentUser: { role: string } | undefined = undefined
let isLoading = false

vi.mock('@/hooks/useAuth', () => ({
  useCurrentUser: () => ({ data: currentUser, isLoading }),
}))

function renderAdminRoute() {
  return render(
    <MemoryRouter initialEntries={['/app/admin/metrics']}>
      <Routes>
        <Route
          path="/app/admin/metrics"
          element={
            <AdminRoute>
              <div>Secret admin metrics</div>
            </AdminRoute>
          }
        />
        <Route path="/app/metagame" element={<div>Metagame tab</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AdminRoute', () => {
  it('renders nothing while the current user is still loading', () => {
    currentUser = undefined
    isLoading = true
    renderAdminRoute()
    expect(screen.queryByText('Secret admin metrics')).not.toBeInTheDocument()
    expect(screen.queryByText('Metagame tab')).not.toBeInTheDocument()
  })

  it('redirects a non-admin user away, without ever rendering the page', () => {
    currentUser = { role: 'user' }
    isLoading = false
    renderAdminRoute()
    expect(screen.queryByText('Secret admin metrics')).not.toBeInTheDocument()
    expect(screen.getByText('Metagame tab')).toBeInTheDocument()
  })

  it('redirects a placeholder/ml_developer user away too (below admin level)', () => {
    currentUser = { role: 'ml_developer' }
    isLoading = false
    renderAdminRoute()
    expect(screen.queryByText('Secret admin metrics')).not.toBeInTheDocument()
    expect(screen.getByText('Metagame tab')).toBeInTheDocument()
  })

  it('renders the page for an admin user', () => {
    currentUser = { role: 'admin' }
    isLoading = false
    renderAdminRoute()
    expect(screen.getByText('Secret admin metrics')).toBeInTheDocument()
  })
})
