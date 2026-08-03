import type { CardTest, CardTestWrite } from '@/schemas/tamiyoScroll'
import { getStore, nextId, nowIso } from '../demoStore'

/** Mirrors `src/api/cardTests.ts` — see `../api/types.ts` for the compile-time proof. */

export function listCardTests(
  options: { personalDeckId?: string } = {},
): Promise<CardTest[]> {
  const store = getStore()
  const tests =
    options.personalDeckId === undefined
      ? store.cardTests
      : store.cardTests.filter((test) => test.personal_deck_id === options.personalDeckId)
  return Promise.resolve(structuredClone(tests))
}

export function createCardTest(payload: CardTestWrite): Promise<CardTest> {
  const store = getStore()
  const test: CardTest = {
    id: nextId(),
    personal_deck_id: payload.personal_deck_id,
    tester: payload.tester,
    card_name: payload.card_name,
    opponent_deck_id: payload.opponent_deck_id ?? null,
    rating: payload.rating,
    notes: payload.notes ?? null,
    created_at: nowIso(),
  }
  store.cardTests.push(test)
  return Promise.resolve(structuredClone(test))
}

export function updateCardTest(
  testId: string,
  payload: CardTestWrite,
): Promise<CardTest> {
  const store = getStore()
  const test = store.cardTests.find((candidate) => candidate.id === testId)
  if (!test) throw new Error(`Demo card test not found: ${testId}`)
  test.personal_deck_id = payload.personal_deck_id
  test.tester = payload.tester
  test.card_name = payload.card_name
  test.opponent_deck_id = payload.opponent_deck_id ?? null
  test.rating = payload.rating
  test.notes = payload.notes ?? null
  return Promise.resolve(structuredClone(test))
}

export function deleteCardTest(testId: string): Promise<void> {
  const store = getStore()
  store.cardTests = store.cardTests.filter((test) => test.id !== testId)
  return Promise.resolve()
}
