import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PersonalDecklistImportSection } from './PersonalDecklistImportSection'

vi.mock('@/contexts/active-deck-context', () => ({
  useActiveDeck: () => ({ activeDeckId: 'deck-1', canEdit: true }),
}))

const importMoxfieldMutateAsync = vi.fn()

vi.mock('@/hooks/useDecklistVersions', () => ({
  useImportMoxfield: () => ({
    mutateAsync: importMoxfieldMutateAsync,
    isPending: false,
  }),
  useCreateDecklistVersion: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

function fillAndSubmitMoxfieldForm() {
  fireEvent.change(screen.getByLabelText('Moxfield link'), {
    target: { value: 'https://moxfield.com/decks/abc123' },
  })
  fireEvent.click(screen.getByText('Import from Moxfield'))
}

describe('PersonalDecklistImportSection', () => {
  it('shows a staleness warning when the import response flags a Moxfield change', async () => {
    importMoxfieldMutateAsync.mockResolvedValueOnce({
      id: 'v2',
      personal_deck_id: 'deck-1',
      version: 2,
      content: '1 Sol Ring',
      source: 'moxfield_import',
      created_at: '2026-07-30T00:00:00Z',
      moxfield_deck_changed_since_last_import: true,
    })

    render(<PersonalDecklistImportSection />)
    fillAndSubmitMoxfieldForm()

    await waitFor(() => {
      expect(
        screen.getByText(/changed on Moxfield since your last import/i),
      ).toBeInTheDocument()
    })
  })

  it('shows no warning when the response flag is false or null', async () => {
    importMoxfieldMutateAsync.mockResolvedValueOnce({
      id: 'v1',
      personal_deck_id: 'deck-1',
      version: 1,
      content: '1 Sol Ring',
      source: 'moxfield_import',
      created_at: '2026-07-30T00:00:00Z',
      moxfield_deck_changed_since_last_import: null,
    })

    render(<PersonalDecklistImportSection />)
    fillAndSubmitMoxfieldForm()

    await waitFor(() => {
      expect(importMoxfieldMutateAsync).toHaveBeenCalled()
    })
    expect(
      screen.queryByText(/changed on Moxfield since your last import/i),
    ).not.toBeInTheDocument()
  })
})
