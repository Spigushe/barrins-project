import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type {
  DecklistVersion,
  DecklistVersionDiff,
  DecklistView,
} from '@/schemas/tamiyoScroll'
import { VersionHistorySection } from './VersionHistorySection'

const version: DecklistVersion = {
  id: 'version-1',
  personal_deck_id: 'deck-mine',
  version: 3,
  content: '4 Lightning Bolt',
  source: 'manual',
  created_at: '2026-07-15T12:00:00+00:00',
  moxfield_deck_changed_since_last_import: null,
}

const emptyView: DecklistView = {
  commander_cards: [],
  library_cards: [],
  unparsed_lines: [],
}
const emptyDiff: DecklistVersionDiff = {
  version_id: 'version-1',
  version: 3,
  compared_to_version_id: null,
  compared_to_version: null,
  cards: [],
  unparsed_lines: [],
}

let versions: DecklistVersion[] = [version]
let showDiffSetting = false
let versionView: DecklistView = emptyView
let versionDiff: DecklistVersionDiff = emptyDiff

const deleteVersionMutateAsync = vi.fn()

vi.mock('@/contexts/active-deck-context', () => ({
  useActiveDeck: () => ({ activeDeckId: 'deck-mine', canEdit: true }),
}))

vi.mock('@/hooks/useDecklistVersions', () => ({
  useDecklistVersions: () => ({ data: versions }),
  useDeleteDecklistVersion: () => ({
    mutateAsync: deleteVersionMutateAsync,
    isPending: false,
  }),
  useDecklistVersionView: () => ({ data: versionView }),
  useDecklistVersionDiff: () => ({ data: versionDiff }),
}))

vi.mock('@/hooks/useSettings', () => ({
  useMySettings: () => ({ data: { show_decklist_version_diff: showDiffSetting } }),
}))

describe('VersionHistorySection — delete confirmation', () => {
  beforeEach(() => {
    versions = [version]
    showDiffSetting = false
    versionView = emptyView
    versionDiff = emptyDiff
    deleteVersionMutateAsync.mockClear()
  })

  it('asks for confirmation before deleting, without deleting immediately', async () => {
    const user = userEvent.setup()
    render(<VersionHistorySection />)

    await user.click(screen.getByRole('button', { name: '✕' }))

    expect(deleteVersionMutateAsync).not.toHaveBeenCalled()
    expect(screen.getByText('Delete version 3?')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Delete' }))

    expect(deleteVersionMutateAsync).toHaveBeenCalledWith({
      deckId: 'deck-mine',
      versionId: 'version-1',
    })
  })

  it('cancels without deleting', async () => {
    const user = userEvent.setup()
    render(<VersionHistorySection />)

    await user.click(screen.getByRole('button', { name: '✕' }))
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(deleteVersionMutateAsync).not.toHaveBeenCalled()
    expect(screen.queryByText('Delete version 3?')).not.toBeInTheDocument()
  })
})

describe('VersionHistorySection — expand in place (S15)', () => {
  beforeEach(() => {
    versions = [version]
    showDiffSetting = false
    versionView = {
      commander_cards: [],
      library_cards: [
        {
          category: 'instant',
          count: 1,
          cards: [
            {
              qty: 4,
              name: 'Lightning Bolt',
              status: 'neutral',
              mana_cost: null,
              type_line: null,
              text: null,
              keywords: [],
              scryfall_id: null,
            },
          ],
        },
      ],
      unparsed_lines: [],
    }
    versionDiff = emptyDiff
    deleteVersionMutateAsync.mockClear()
  })

  it('expands a version to show its full content when the diff setting is off', async () => {
    const user = userEvent.setup()
    render(<VersionHistorySection />)

    await user.click(screen.getByText('Version 3'))

    expect(await screen.findByText('Lightning Bolt')).toBeInTheDocument()
  })

  it('collapses again on a second click', async () => {
    const user = userEvent.setup()
    render(<VersionHistorySection />)

    await user.click(screen.getByText('Version 3'))
    expect(await screen.findByText('Lightning Bolt')).toBeInTheDocument()

    await user.click(screen.getByText('Version 3'))
    expect(screen.queryByText('Lightning Bolt')).not.toBeInTheDocument()
  })

  it('shows a diff instead of full content when the diff setting is on', async () => {
    showDiffSetting = true
    versionDiff = {
      version_id: 'version-1',
      version: 3,
      compared_to_version_id: 'version-0',
      compared_to_version: 2,
      cards: [
        {
          name: 'Sol Ring',
          status: 'added',
          old_qty: null,
          new_qty: 1,
          is_commander: false,
        },
      ],
      unparsed_lines: [],
    }
    const user = userEvent.setup()
    render(<VersionHistorySection />)

    await user.click(screen.getByText('Version 3'))

    expect(await screen.findByText('+ 1 Sol Ring')).toBeInTheDocument()
    expect(screen.queryByText('Lightning Bolt')).not.toBeInTheDocument()
  })

  it('shows a no-prior-version message for the first version when diff is on', async () => {
    showDiffSetting = true
    const user = userEvent.setup()
    render(<VersionHistorySection />)

    await user.click(screen.getByText('Version 3'))

    expect(
      await screen.findByText(/no prior version to compare against/i),
    ).toBeInTheDocument()
  })

  it('clicking delete does not expand the row', async () => {
    const user = userEvent.setup()
    render(<VersionHistorySection />)

    await user.click(screen.getByRole('button', { name: '✕' }))

    expect(screen.queryByText('Lightning Bolt')).not.toBeInTheDocument()
  })
})
