import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
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

interface DiffCard {
  name: string
  status: 'added' | 'removed' | 'unchanged' | 'quantity_changed'
  old_qty: number | null
  new_qty: number | null
  is_commander: boolean
  card_test_notes: string[]
}

function makeDiff(cards: DiffCard[]) {
  return {
    version_id: 'v2',
    version: 2,
    compared_to_version_id: 'v1',
    compared_to_version: 1,
    cards,
    unparsed_lines: [] as { line: string; status: string }[],
  }
}

let diff = makeDiff([
  {
    name: 'Sol Ring',
    status: 'added',
    old_qty: null,
    new_qty: 1,
    is_commander: false,
    card_test_notes: ['great swap into the control matchup'],
  },
])
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

async function expandVersion2() {
  const user = userEvent.setup()
  render(<VersionHistorySection />)
  await user.click(screen.getByRole('button', { name: /Version 2/ }))
}

describe('VersionHistorySection — S16 matched card-test comments', () => {
  beforeEach(() => {
    showChangeLog = true
    diff = makeDiff([
      {
        name: 'Sol Ring',
        status: 'added',
        old_qty: null,
        new_qty: 1,
        is_commander: false,
        card_test_notes: ['great swap into the control matchup'],
      },
    ])
  })

  it('shows a matched card test note under its diff line when the setting is on', async () => {
    await expandVersion2()

    expect(screen.getByText('great swap into the control matchup')).toBeInTheDocument()
  })

  it('hides the matched card test note when the setting is off', async () => {
    showChangeLog = false
    await expandVersion2()

    expect(
      screen.queryByText('great swap into the control matchup'),
    ).not.toBeInTheDocument()
  })
})

describe('VersionHistorySection — grouping changes by shared comment', () => {
  beforeEach(() => {
    showChangeLog = true
  })

  it('renders cards that share a comment together under it once', async () => {
    diff = makeDiff([
      {
        name: 'Flood Plain',
        status: 'removed',
        old_qty: 1,
        new_qty: null,
        is_commander: false,
        card_test_notes: ['tapland inutile'],
      },
      {
        name: 'Mystic Gate',
        status: 'added',
        old_qty: null,
        new_qty: 1,
        is_commander: false,
        card_test_notes: ['tapland inutile'],
      },
    ])
    await expandVersion2()

    expect(screen.getAllByText('tapland inutile')).toHaveLength(1)
    expect(screen.getByText('- 1 Flood Plain')).toBeInTheDocument()
    expect(screen.getByText('+ 1 Mystic Gate')).toBeInTheDocument()
    expect(screen.queryByText('Other changes')).not.toBeInTheDocument()
  })

  it('orders removed before added within a comment group', async () => {
    diff = makeDiff([
      {
        name: 'Brainstorm',
        status: 'added',
        old_qty: null,
        new_qty: 1,
        is_commander: false,
        card_test_notes: ['swap'],
      },
      {
        name: 'Ponder',
        status: 'removed',
        old_qty: 1,
        new_qty: null,
        is_commander: false,
        card_test_notes: ['swap'],
      },
    ])
    await expandVersion2()

    const lines = screen.getAllByText(/^[+-] 1 /).map((el) => el.textContent)
    expect(lines).toEqual(['- 1 Ponder', '+ 1 Brainstorm'])
  })

  it('drops changes with no comment into an "Other changes" block', async () => {
    diff = makeDiff([
      {
        name: 'Flood Plain',
        status: 'removed',
        old_qty: 1,
        new_qty: null,
        is_commander: false,
        card_test_notes: ['tapland inutile'],
      },
      {
        name: 'Mystic Gate',
        status: 'added',
        old_qty: null,
        new_qty: 1,
        is_commander: false,
        card_test_notes: ['tapland inutile'],
      },
      {
        name: 'Ponder',
        status: 'removed',
        old_qty: 1,
        new_qty: null,
        is_commander: false,
        card_test_notes: [],
      },
    ])
    await expandVersion2()

    expect(screen.getByText('Other changes')).toBeInTheDocument()
    expect(screen.getByText('- 1 Ponder')).toBeInTheDocument()
  })

  it('keeps a flat list (no "Other changes" header) when nothing has a comment', async () => {
    diff = makeDiff([
      {
        name: 'Ponder',
        status: 'removed',
        old_qty: 1,
        new_qty: null,
        is_commander: false,
        card_test_notes: [],
      },
      {
        name: 'Brainstorm',
        status: 'added',
        old_qty: null,
        new_qty: 1,
        is_commander: false,
        card_test_notes: [],
      },
    ])
    await expandVersion2()

    expect(screen.queryByText('Other changes')).not.toBeInTheDocument()
    expect(screen.getByText('- 1 Ponder')).toBeInTheDocument()
    expect(screen.getByText('+ 1 Brainstorm')).toBeInTheDocument()
  })
})
