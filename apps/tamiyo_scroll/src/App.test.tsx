import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AppPrefixRedirect } from './App'

function LocationProbe({ label }: { label: string }) {
  const location = useLocation()
  return (
    <div>
      {label}: {location.pathname}
      {location.search}
    </div>
  )
}

function renderAtPath(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/tracker" element={<LocationProbe label="Tracker tab" />} />
        <Route path="/team/:teamId" element={<LocationProbe label="Team page" />} />
        <Route path="/app/*" element={<AppPrefixRedirect />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AppPrefixRedirect — old /app/* links still resolve', () => {
  it('redirects a flat old path to its new top-level path', () => {
    renderAtPath('/app/tracker')
    expect(screen.getByText('Tracker tab: /tracker')).toBeInTheDocument()
  })

  it('redirects a nested old path, preserving the rest of it', () => {
    renderAtPath('/app/team/team-1')
    expect(screen.getByText('Team page: /team/team-1')).toBeInTheDocument()
  })

  it('preserves the query string across the redirect', () => {
    renderAtPath('/app/team/team-1?tab=members')
    expect(screen.getByText('Team page: /team/team-1?tab=members')).toBeInTheDocument()
  })
})
