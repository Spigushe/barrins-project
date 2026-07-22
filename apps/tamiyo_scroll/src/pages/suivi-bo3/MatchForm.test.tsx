import { describe, expect, it } from 'vitest'
import type { Match } from '@/schemas/tamiyoScroll'
import {
  draftFromMatch,
  emptyMatchDraft,
  GAME_NOT_PLAYED,
  matchDraftIsValid,
  matchDraftToWrite,
} from './MatchForm'

const baseMatch: Match = {
  id: 'match-1',
  date: '2026-07-15',
  personal_deck_id: 'deck-mine',
  opponent_deck_id: 'deck-theirs',
  on_play: true,
  game1: 'win',
  game2: 'loss',
  game3: null,
  opening_hand: 'Two lands, Bolt',
  turning_point: null,
  final_turn: null,
  created_at: '2026-07-15T12:00:00+00:00',
}

describe('emptyMatchDraft', () => {
  it('defaults personalDeckId to the provided active deck', () => {
    const draft = emptyMatchDraft('deck-mine')
    expect(draft.personalDeckId).toBe('deck-mine')
    expect(draft.opponentDeckId).toBe('')
    expect(draft.onPlay).toBe(true)
    expect(draft.game1).toBe(GAME_NOT_PLAYED)
  })

  it('leaves personalDeckId empty when there is no active deck', () => {
    expect(emptyMatchDraft(null).personalDeckId).toBe('')
  })
})

describe('draftFromMatch / matchDraftToWrite round-trip', () => {
  it('preserves games, on_play, and free-text fields', () => {
    const draft = draftFromMatch(baseMatch)
    expect(draft.game1).toBe('win')
    expect(draft.game2).toBe('loss')
    expect(draft.game3).toBe(GAME_NOT_PLAYED)
    expect(draft.openingHand).toBe('Two lands, Bolt')

    const write = matchDraftToWrite(draft)
    expect(write).toEqual({
      personal_deck_id: 'deck-mine',
      opponent_deck_id: 'deck-theirs',
      on_play: true,
      game1: 'win',
      game2: 'loss',
      game3: null,
      opening_hand: 'Two lands, Bolt',
      turning_point: null,
      final_turn: null,
    })
  })

  it('maps the "not played" sentinel to null, never as a literal string', () => {
    const draft = emptyMatchDraft('deck-mine')
    draft.opponentDeckId = 'deck-theirs'
    const write = matchDraftToWrite(draft)
    expect(write.game1).toBeNull()
    expect(write.game2).toBeNull()
    expect(write.game3).toBeNull()
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
