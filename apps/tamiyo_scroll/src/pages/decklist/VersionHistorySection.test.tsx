import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { VersionHistorySection } from './VersionHistorySection'

const versions = [
  {
    id: 'v2',
    personal_deck_id: 'deck-1',
    version: 2,
    content: '4 Lightning Bolt\n1 Sol Ring',
    source: 'manual' as const,
    created_at: '2026-08-24T10:00:00+00:00',
  },
]

const diff = {
  version_id: 'v2',
  version: 2,
  compared_to_version_id: 'v1',
  compared_to_version: 1,
  cards: [
    {
      name: 'Sol Ring',
      status: 'added' as const,
      old_qty: null,
      new_qty: 1,
      is_commander: false,
      card_test_notes: ['great swap into the control matchup'],
    },
  ],
  unparsed_lines: [],
}

let showChangeLog = true

vi.mock('@/contexts/active-deck-context', () => ({
  useActiveDeck: () => ({ activeDeckId: 'deck-1', canEdit: true }),
}))

vi.mock('@/hooks/useSettings', () => ({
  useMySettings: () => ({ data: { show_decklist_change_log: showChangeLog } }),
}))

vi.mock('@/hooks/useDecklistVersions', () => ({
  useDecklistVersions: () => ({ data: versions }),
  useDecklistVersionDiff: () => ({ data: diff }),
  useDecklistVersionView: () => ({ data: undefined }),
  useDeleteDecklistVersion: () => ({ mutateAsync: vi.fn() }),
}))

describe('VersionHistorySection — S16 matched card-test comments', () => {
  it('shows a matched card test note under its diff line when the setting is on', async () => {
    showChangeLog = true
    const user = userEvent.setup()
    render(<VersionHistorySection />)

    await user.click(screen.getByRole('button', { name: /Version 2/ }))

    expect(screen.getByText('great swap into the control matchup')).toBeInTheDocument()
  })

  it('hides the matched card test note when the setting is off', async () => {
    showChangeLog = false
    const user = userEvent.setup()
    render(<VersionHistorySection />)

    await user.click(screen.getByRole('button', { name: /Version 2/ }))

    expect(
      screen.queryByText('great swap into the control matchup'),
    ).not.toBeInTheDocument()
  })
})
