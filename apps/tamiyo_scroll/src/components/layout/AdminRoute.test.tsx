import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { vi } from 'vitest'
import { AdminRoute } from './AdminRoute'

let currentUser: { role: string } | undefined = undefined
let isLoading = false

vi.mock('@barrins/goblin-guide', () => ({
  useCurrentUser: () => ({ data: currentUser, isLoading }),
}))

function renderAdminRoute() {
  return render(
    <MemoryRouter initialEntries={['/admin/metrics']}>
      <Routes>
        <Route
          path="/admin/metrics"
          element={
            <AdminRoute>
              <div>Secret admin metrics</div>
            </AdminRoute>
          }
        />
        <Route path="/tracker" element={<div>Tracker tab</div>} />
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
    expect(screen.queryByText('Tracker tab')).not.toBeInTheDocument()
  })

  it('redirects a non-admin user away, without ever rendering the page', () => {
    currentUser = { role: 'user' }
    isLoading = false
    renderAdminRoute()
    expect(screen.queryByText('Secret admin metrics')).not.toBeInTheDocument()
    expect(screen.getByText('Tracker tab')).toBeInTheDocument()
  })

  it('redirects a moderator/ml_developer user away too (below admin level)', () => {
    currentUser = { role: 'ml_developer' }
    isLoading = false
    renderAdminRoute()
    expect(screen.queryByText('Secret admin metrics')).not.toBeInTheDocument()
    expect(screen.getByText('Tracker tab')).toBeInTheDocument()
  })

  it('renders the page for an admin user', () => {
    currentUser = { role: 'admin' }
    isLoading = false
    renderAdminRoute()
    expect(screen.getByText('Secret admin metrics')).toBeInTheDocument()
  })
})
