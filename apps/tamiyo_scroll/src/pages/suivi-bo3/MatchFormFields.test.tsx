import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { emptyMatchDraft, MatchFormFields } from './MatchForm'

const createMetaDeckMutateAsync = vi.fn()

vi.mock('@/hooks/useMetaDecks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/useMetaDecks')>()
  return {
    ...actual,
    useCreateMetaDeck: () => ({ mutateAsync: createMetaDeckMutateAsync }),
  }
})

let sessions: { id: string; name: string; closed_at: string | null }[] = []
const createSessionMutateAsync = vi.fn()

vi.mock('@/hooks/useSessions', () => ({
  useSessions: () => ({ data: sessions }),
  useCreateSession: () => ({ mutateAsync: createSessionMutateAsync, isPending: false }),
}))

const personalDeckOptions = [{ id: 'deck-mine', name: 'Mono Red' }]
const metaDeckOptions = [{ id: 'deck-theirs', name: 'Azorius Control' }]

describe('MatchFormFields — opponent deck field', () => {
  it('selects an existing opponent deck', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <MatchFormFields
        draft={emptyMatchDraft('deck-mine')}
        onChange={onChange}
        personalDeckOptions={personalDeckOptions}
        metaDeckOptions={metaDeckOptions}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Opponent' }))
    await user.click(screen.getByText('Azorius Control'))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ opponentDeckId: 'deck-theirs' }),
    )
  })

  it('creates a new opponent deck with tier/category and honest defaults for the rest', async () => {
    createMetaDeckMutateAsync.mockResolvedValue({ id: 'deck-new', name: 'Boros Energy' })
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <MatchFormFields
        draft={emptyMatchDraft('deck-mine')}
        onChange={onChange}
        personalDeckOptions={personalDeckOptions}
        metaDeckOptions={metaDeckOptions}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Opponent' }))
    await user.type(screen.getByPlaceholderText('Search or create…'), 'Boros Energy')
    await user.click(screen.getByText('Create "Boros Energy"'))

    // Quick-create dialog: only name (shown), tier, category are chosen —
    // no expected/top8/presence inputs (matches the Roster quick-add form).
    expect(screen.getByText('Boros Energy')).toBeInTheDocument()
    expect(screen.queryByText('Expected')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Create' }))

    expect(createMetaDeckMutateAsync).toHaveBeenCalledWith({
      name: 'Boros Energy',
      tier: 1,
      category: 'midrange',
      decklist_notes: null,
      top8: 0,
      presence: 0,
      expected: 'as_expected',
      tests_status: null,
      personal_deck_id: 'deck-mine',
    })
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ opponentDeckId: 'deck-new' }),
    )
  })
})

describe('MatchFormFields — session field', () => {
  it('selects an existing session, same combobox shape as the opponent field', async () => {
    sessions = [{ id: 'session-1', name: 'RC Toronto 2026', closed_at: null }]
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <MatchFormFields
        draft={emptyMatchDraft('deck-mine')}
        onChange={onChange}
        personalDeckOptions={personalDeckOptions}
        metaDeckOptions={metaDeckOptions}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Session' }))
    await user.click(screen.getByText('RC Toronto 2026'))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ sessionId: 'session-1' }),
    )
  })

  it('creates a new session via the inline "Create" item', async () => {
    sessions = []
    createSessionMutateAsync.mockResolvedValue({
      id: 'session-new',
      name: 'Weekly Training',
    })
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <MatchFormFields
        draft={emptyMatchDraft('deck-mine')}
        onChange={onChange}
        personalDeckOptions={personalDeckOptions}
        metaDeckOptions={metaDeckOptions}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Session' }))
    await user.type(screen.getByPlaceholderText('Search or create…'), 'Weekly Training')
    await user.click(screen.getByText('Create "Weekly Training"'))

    expect(screen.getByText('Weekly Training')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Create' }))

    expect(createSessionMutateAsync).toHaveBeenCalledWith({
      name: 'Weekly Training',
      type: 'training',
      personal_deck_id: 'deck-mine',
    })
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ sessionId: 'session-new' }),
    )
  })

  it('does not offer a closed session as selectable, but still shows its name if already assigned', async () => {
    sessions = [
      { id: 'session-open', name: 'Open Session', closed_at: null },
      { id: 'session-closed', name: 'Closed Session', closed_at: '2026-07-01T00:00:00Z' },
    ]
    const onChange = vi.fn()
    const user = userEvent.setup()
    const draft = { ...emptyMatchDraft('deck-mine'), sessionId: 'session-closed' }
    render(
      <MatchFormFields
        draft={draft}
        onChange={onChange}
        personalDeckOptions={personalDeckOptions}
        metaDeckOptions={metaDeckOptions}
      />,
    )

    // The trigger still shows the closed session's name...
    expect(screen.getByRole('button', { name: 'Session' })).toHaveTextContent(
      'Closed Session',
    )

    // ...but it isn't offered again in the picker, only the open one is.
    // ("Closed Session" still appears once — the trigger's own label.)
    await user.click(screen.getByRole('button', { name: 'Session' }))
    expect(screen.getByText('Open Session')).toBeInTheDocument()
    expect(screen.getAllByText('Closed Session')).toHaveLength(1)
  })
})
