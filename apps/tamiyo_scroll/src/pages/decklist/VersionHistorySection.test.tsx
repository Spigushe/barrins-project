import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { DecklistVersion } from '@/schemas/tamiyoScroll'
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

let versions: DecklistVersion[] = [version]

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
}))

describe('VersionHistorySection — delete confirmation', () => {
  beforeEach(() => {
    versions = [version]
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
