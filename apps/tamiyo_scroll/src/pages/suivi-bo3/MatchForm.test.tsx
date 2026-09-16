import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Match } from '@/schemas/tamiyoScroll'
import {
  applyDerivedOnPlay,
  draftFromMatch,
  emptyMatchDraft,
  GAME_NOT_PLAYED,
  matchDraftIsValid,
  matchDraftToWrite,
  type MatchDraft,
  MatchFormFields,
} from './MatchForm'

const baseMatch: Match = {
  id: 'match-1',
  date: '2026-07-15',
  personal_deck_id: 'deck-mine',
  opponent_deck_id: 'deck-theirs',
  decklist_version_id: 'version-2',
  session_id: null,
  // Game 3 is deliberately absent — #123/#124's "one entry per game
  // actually played/being played" (never a fixed-length 3-tuple).
  games: [
    {
      game_number: 1,
      on_play: true,
      result: 'win',
      player_mulligans: null,
      opponent_mulligans: null,
      player_misplays: null,
      opponent_misplays: null,
    },
    {
      game_number: 2,
      on_play: false,
      result: 'loss',
      player_mulligans: [{ id: 'event-1', comment: 'Kept a risky one-lander' }],
      opponent_mulligans: [],
      player_misplays: [
        { id: 'event-2', comment: 'Missed a combat trick' },
        { id: 'event-3', comment: null },
      ],
      opponent_misplays: [],
    },
  ],
  opening_hand: 'Two lands, Bolt',
  turning_point: null,
  final_turn: null,
  created_at: '2026-07-15T12:00:00+00:00',
  is_readonly: false,
  shared_by: null,
}

describe('emptyMatchDraft', () => {
  it('defaults personalDeckId to the provided active deck', () => {
    const draft = emptyMatchDraft('deck-mine')
    expect(draft.personalDeckId).toBe('deck-mine')
    expect(draft.opponentDeckId).toBe('')
    expect(draft.games[0].onPlay).toBe(true)
    expect(draft.games[0].result).toBe(GAME_NOT_PLAYED)
  })

  it('leaves personalDeckId empty when there is no active deck', () => {
    expect(emptyMatchDraft(null).personalDeckId).toBe('')
  })

  it('never guesses a decklist version — the backend auto-stamps it on create', () => {
    expect(emptyMatchDraft('deck-mine').decklistVersionId).toBeNull()
  })

  it('leaves every gated event list empty, until touched', () => {
    const draft = emptyMatchDraft('deck-mine')
    for (const game of draft.games) {
      expect(game.playerMulligans).toEqual([])
      expect(game.opponentMulligans).toEqual([])
      expect(game.playerMisplays).toEqual([])
      expect(game.opponentMisplays).toEqual([])
    }
  })
})

describe('draftFromMatch / matchDraftToWrite round-trip', () => {
  it('preserves per-game results, on_play, gated event lists, and the free-text fields', () => {
    const draft = draftFromMatch(baseMatch)
    expect(draft.decklistVersionId).toBe('version-2')
    expect(draft.games[0].result).toBe('win')
    expect(draft.games[0].onPlay).toBe(true)
    expect(draft.games[1].result).toBe('loss')
    expect(draft.games[1].onPlay).toBe(false)
    expect(draft.games[1].playerMulligans).toEqual([
      { id: 'event-1', comment: 'Kept a risky one-lander' },
    ])
    expect(draft.games[1].playerMisplays).toEqual([
      { id: 'event-2', comment: 'Missed a combat trick' },
      { id: 'event-3', comment: '' },
    ])
    // Game 3 was never entered — a fresh, untouched slot in the draft.
    expect(draft.games[2].result).toBe(GAME_NOT_PLAYED)
    expect(draft.games[2].playerMulligans).toEqual([])
    expect(draft.openingHand).toBe('Two lands, Bolt')

    const write = matchDraftToWrite(draft)
    expect(write).toEqual({
      personal_deck_id: 'deck-mine',
      opponent_deck_id: 'deck-theirs',
      decklist_version_id: 'version-2',
      session_id: null,
      games: [
        {
          game_number: 1,
          on_play: true,
          result: 'win',
          player_mulligans: [],
          opponent_mulligans: [],
          player_misplays: [],
          opponent_misplays: [],
        },
        {
          game_number: 2,
          on_play: false,
          result: 'loss',
          player_mulligans: [{ comment: 'Kept a risky one-lander' }],
          opponent_mulligans: [],
          player_misplays: [{ comment: 'Missed a combat trick' }, { comment: null }],
          opponent_misplays: [],
        },
      ],
      opening_hand: 'Two lands, Bolt',
      turning_point: null,
      final_turn: null,
    })
  })

  it('maps the "not played" sentinel to null, never as a literal string', () => {
    const draft = emptyMatchDraft('deck-mine')
    draft.opponentDeckId = 'deck-theirs'
    const write = matchDraftToWrite(draft)
    // Game 1 is always included (mirrors the old always-present match-level
    // `on_play`); games 2/3 were never touched, so they're absent entirely —
    // not present-with-empty-lists.
    expect(write.games).toHaveLength(1)
    expect(write.games[0].result).toBeNull()
  })

  it('only includes a game once something was entered for it (partial entry, D8)', () => {
    const draft = emptyMatchDraft('deck-mine')
    draft.opponentDeckId = 'deck-theirs'
    draft.games[0].result = 'win'
    draft.games[1].playerMisplays = [{ comment: '' }]
    // Game 3 stays completely untouched.
    const write = matchDraftToWrite(draft)
    expect(write.games.map((game) => game.game_number)).toEqual([1, 2])
  })

  it('trims free-text fields and converts blanks to null', () => {
    const draft = emptyMatchDraft('deck-mine')
    draft.opponentDeckId = 'deck-theirs'
    draft.openingHand = '   '
    draft.turningPoint = '  Attacked turn 3  '
    const write = matchDraftToWrite(draft)
    expect(write.opening_hand).toBeNull()
    expect(write.turning_point).toBe('Attacked turn 3')
  })
})

describe('matchDraftIsValid', () => {
  it('requires both a personal deck and an opponent deck', () => {
    expect(matchDraftIsValid(emptyMatchDraft(null))).toBe(false)
    expect(matchDraftIsValid(emptyMatchDraft('deck-mine'))).toBe(false)

    const draft = emptyMatchDraft('deck-mine')
    draft.opponentDeckId = 'deck-theirs'
    expect(matchDraftIsValid(draft)).toBe(true)
  })
})

describe('applyDerivedOnPlay — loser-chooses-play convention for games 2/3', () => {
  it('derives On the Play for game 2 after a game 1 loss', () => {
    const draft = emptyMatchDraft('deck-mine')
    draft.games[0].result = 'loss'
    const games = applyDerivedOnPlay(draft.games)
    expect(games[1].onPlay).toBe(true)
    expect(games[1].onPlayTouched).toBe(false)
  })

  it('derives On the Draw for game 2 after a game 1 win', () => {
    const draft = emptyMatchDraft('deck-mine')
    draft.games[0].result = 'win'
    expect(applyDerivedOnPlay(draft.games)[1].onPlay).toBe(false)
  })

  it('leaves game 2 unknown after a game 1 draw — no loser to make the choice', () => {
    const draft = emptyMatchDraft('deck-mine')
    draft.games[0].result = 'draw'
    expect(applyDerivedOnPlay(draft.games)[1].onPlay).toBeNull()
  })

  it('leaves game 2 unknown while game 1 has no result yet', () => {
    const draft = emptyMatchDraft('deck-mine')
    expect(applyDerivedOnPlay(draft.games)[1].onPlay).toBeNull()
  })

  it('never overrides a manually chosen onPlay', () => {
    const draft = emptyMatchDraft('deck-mine')
    draft.games[0].result = 'loss'
    draft.games[1] = { ...draft.games[1], onPlay: false, onPlayTouched: true }
    const games = applyDerivedOnPlay(draft.games)
    expect(games[1].onPlay).toBe(false)
  })

  it("cascades independently — game 3 derives from game 2's own result", () => {
    const draft = emptyMatchDraft('deck-mine')
    draft.games[0].result = 'loss'
    draft.games[1].result = 'win'
    const games = applyDerivedOnPlay(draft.games)
    expect(games[1].onPlay).toBe(true)
    expect(games[2].onPlay).toBe(false)
  })
})

// #123/#124 D2/D7: the mulligan/misplay stepper + per-event comment rows
// are a client-side UX convenience gated to a `moderator`+ `currentUser` —
// the backend's field-level 403 in `_apply_payload` is the real boundary.
let currentUserRole: string | undefined

vi.mock('@barrins/goblin-guide', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@barrins/goblin-guide')>()
  return {
    ...actual,
    useCurrentUser: () => ({
      data: currentUserRole ? { role: currentUserRole } : undefined,
    }),
  }
})

vi.mock('@/hooks/useMetaDecks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/useMetaDecks')>()
  return {
    ...actual,
    useCreateMetaDeck: () => ({ mutateAsync: vi.fn(), isPending: false }),
  }
})

vi.mock('@/hooks/useSessions', () => ({
  useSessions: () => ({ data: [] }),
  useCreateSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

/** A real, re-rendering controlled-component harness — required for the
 * "+1"/edit tests below, where each interaction must build on the DOM's
 * current state rather than a draft object frozen at render time. */
function renderFields(role: string | undefined) {
  currentUserRole = role
  const initialDraft = emptyMatchDraft('deck-mine')
  initialDraft.opponentDeckId = 'deck-theirs'
  const holder: { draft: MatchDraft } = { draft: initialDraft }

  function Harness() {
    const [draft, setDraft] = useState(initialDraft)
    holder.draft = draft
    return (
      <MatchFormFields
        draft={draft}
        onChange={setDraft}
        personalDeckOptions={[{ id: 'deck-mine', name: 'Mono Red' }]}
        metaDeckOptions={[{ id: 'deck-theirs', name: 'Boros Energy' }]}
      />
    )
  }

  render(<Harness />)
  return {
    getLatestDraft: () => holder.draft,
  }
}

describe('MatchFormFields — role-gated stepper/event-list rows (D2/D7)', () => {
  it('hides the stepper/event-list rows for a plain `user`', () => {
    renderFields('user')
    expect(screen.queryByText('Mulligans')).not.toBeInTheDocument()
    expect(screen.queryByText('Misplays')).not.toBeInTheDocument()
  })

  it('hides the stepper/event-list rows while the current user is still unresolved', () => {
    renderFields(undefined)
    expect(screen.queryByText('Mulligans')).not.toBeInTheDocument()
  })

  it('renders the current form exactly as before for a sub-moderator user (D7)', () => {
    renderFields('user')
    // The base, ungated controls are still there — three game columns, each
    // with a result select, a per-game Play/Draw select, and its Notes box.
    expect(screen.getByText('Game 1')).toBeInTheDocument()
    expect(screen.getByText('Game 2')).toBeInTheDocument()
    expect(screen.getByText('Game 3')).toBeInTheDocument()
    expect(screen.getByLabelText('Game 1 Notes')).toBeInTheDocument()
    expect(screen.getAllByText('Play/Draw')).toHaveLength(3)
  })

  it('shows the stepper/event-list group for a moderator', () => {
    renderFields('moderator')
    expect(screen.getAllByText('Mulligans').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Misplays').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Player').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Opponent').length).toBeGreaterThan(0)
  })

  it('shows the stepper/event-list rows for ml_developer (ordinal check, not exact-match)', () => {
    renderFields('ml_developer')
    expect(screen.getAllByText('Mulligans').length).toBeGreaterThan(0)
  })

  it('shows the stepper/event-list rows for admin (top of the hierarchy)', () => {
    renderFields('admin')
    expect(screen.getAllByText('Mulligans').length).toBeGreaterThan(0)
  })

  it('clicking "+1" immediately logs a blank-comment event and the count reflects the array length', async () => {
    const user = userEvent.setup()
    const { getLatestDraft } = renderFields('moderator')

    const addButtons = screen.getAllByRole('button', {
      name: 'Log a new mulligan (+1)',
    })
    // Game 1's Player-side Mulligans "+1" is the first one in document order.
    await user.click(addButtons[0])

    const draft = getLatestDraft()
    expect(draft.games[0].playerMulligans).toEqual([{ comment: '' }])
  })

  it('editing one event\'s comment does not touch any other event', async () => {
    const user = userEvent.setup()
    const { getLatestDraft } = renderFields('moderator')

    const addButtons = screen.getAllByRole('button', {
      name: 'Log a new mulligan (+1)',
    })
    await user.click(addButtons[0])
    await user.click(addButtons[0])

    let draft = getLatestDraft()
    expect(draft.games[0].playerMulligans).toHaveLength(2)

    const commentInputs = screen.getAllByLabelText('Mulligan #1 comment')
    await user.type(commentInputs[0], 'Kept a slow six')

    draft = getLatestDraft()
    expect(draft.games[0].playerMulligans[0].comment).toBe('Kept a slow six')
    // The second logged event is untouched.
    expect(draft.games[0].playerMulligans[1].comment).toBe('')
  })
})
