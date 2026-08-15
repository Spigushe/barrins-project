import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CurrentDecklistSection } from './CurrentDecklistSection'

let activeDeckId: string | null = 'deck-mine'
let versions: { version: number; created_at: string }[] = []
let view = { commander_cards: [], library_cards: [], unparsed_lines: [] }

const downloadReportMutate = vi.fn()

vi.mock('@/contexts/active-deck-context', () => ({
  useActiveDeck: () => ({ activeDeckId, canEdit: true }),
}))

vi.mock('@/hooks/useDecklistVersions', () => ({
  useDecklistVersions: () => ({ data: versions }),
  useDecklistView: () => ({ data: view }),
}))

vi.mock('@/hooks/usePersonalDecks', () => ({
  usePersonalDecks: () => ({ data: [{ id: 'deck-mine', name: 'Mono Red' }] }),
  useDownloadDeckReport: () => ({
    mutate: downloadReportMutate,
    isPending: false,
  }),
}))

beforeEach(() => {
  activeDeckId = 'deck-mine'
  versions = []
  view = { commander_cards: [], library_cards: [], unparsed_lines: [] }
  downloadReportMutate.mockReset()
})

describe('CurrentDecklistSection — deck-level report download', () => {
  it("downloads the active deck's report", async () => {
    const user = userEvent.setup()
    render(<CurrentDecklistSection />)

    await user.click(screen.getByRole('button', { name: 'Download report (PDF)' }))

    expect(downloadReportMutate).toHaveBeenCalledWith({
      deckId: 'deck-mine',
      filename: 'deck-report-mono-red.pdf',
    })
  })

  it('renders nothing when no deck is active', () => {
    activeDeckId = null
    const { container } = render(<CurrentDecklistSection />)

    expect(container).toBeEmptyDOMElement()
  })
})
