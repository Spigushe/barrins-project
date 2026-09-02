import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { FetchLike } from '../auth/client'
import { IdentityProvider } from '../auth/IdentityProvider'
import type { Application } from '../auth/schemas'
import { ApplicationsScreen } from './ApplicationsScreen'

const SVG = "<svg xmlns='http://www.w3.org/2000/svg'/>"

function app(over: Partial<Application>): Application {
  return {
    key: 'x',
    name: 'X',
    description: 'd',
    url: 'https://x.test',
    logo_svg: SVG,
    access: 'open',
    min_role: null,
    ...over,
  }
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

function renderScreen(apps: Application[] | Response, currentAppKey?: string) {
  const fetchImpl: FetchLike = vi.fn(async (url: string) => {
    if (url.endsWith('/api/v1/applications')) {
      return apps instanceof Response ? apps : json(apps)
    }
    throw new Error(`unexpected ${url}`)
  })
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <IdentityProvider config={{ serviceUrl: 'https://identity.test', fetchImpl }}>
        <ApplicationsScreen currentAppKey={currentAppKey} />
      </IdentityProvider>
    </QueryClientProvider>,
  )
}

const MIXED: Application[] = [
  app({ key: 'goblin_guide', name: 'Goblin Guide', access: 'open' }),
  app({ key: 'tamiyo_scroll', name: 'Tamiyo Scroll', access: 'open' }),
  app({ key: 'tolaria_news', name: 'Tolaria News', access: 'login_required' }),
  app({
    key: 'karn_jupyter',
    name: 'Karn Tablets',
    access: 'role_denied',
    min_role: 'ml_developer',
  }),
]

describe('<ApplicationsScreen>', () => {
  it('renders one group per access state, non-empty only', async () => {
    renderScreen(MIXED)

    expect(await screen.findByRole('heading', { name: 'Available' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Sign in to open' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Restricted' })).toBeInTheDocument()
  })

  it('filters out the current app', async () => {
    renderScreen(MIXED, 'goblin_guide')

    expect(await screen.findByText('Tamiyo Scroll')).toBeInTheDocument()
    expect(screen.queryByText('Goblin Guide')).not.toBeInTheDocument()
  })

  it('makes only "open" apps a link', async () => {
    renderScreen(MIXED)

    const tamiyo = await screen.findByText('Tamiyo Scroll')
    expect(tamiyo.closest('a')).toHaveAttribute('href', 'https://x.test')

    const tolaria = screen.getByText('Tolaria News')
    expect(tolaria.closest('a')).toBeNull()
  })

  it('badges the gated apps: sign-in vs role', async () => {
    renderScreen(MIXED)

    await screen.findByText('Tolaria News')
    expect(screen.getByText('Sign in')).toBeInTheDocument()
    expect(screen.getByText('Needs ml_developer')).toBeInTheDocument()
  })

  it('renders each logo as an inline-svg data URI', async () => {
    renderScreen([app({ key: 'k', name: 'Solo' })])

    const img = await screen.findByRole('presentation')
    expect(img.getAttribute('src')).toMatch(/^data:image\/svg\+xml;utf8,/)
  })

  it('groups the same app names under the right headings', async () => {
    renderScreen(MIXED)

    const available = (await screen.findByRole('heading', { name: 'Available' }))
      .parentElement as HTMLElement
    expect(within(available).getByText('Tamiyo Scroll')).toBeInTheDocument()
    expect(within(available).queryByText('Karn Tablets')).not.toBeInTheDocument()
  })

  it('shows an error state when the request fails', async () => {
    renderScreen(json({ detail: 'boom' }, 500))

    expect(await screen.findByRole('alert')).toHaveTextContent('boom')
  })

  it('shows an empty note when nothing else is available', async () => {
    renderScreen([app({ key: 'only_me' })], 'only_me')

    expect(
      await screen.findByText('No other applications are available yet.'),
    ).toBeInTheDocument()
  })
})
