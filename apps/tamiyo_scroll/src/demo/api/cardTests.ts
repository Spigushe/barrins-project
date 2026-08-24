import type {
  CardTest,
  CardTestEvaluation,
  CardTestEvaluationWrite,
  CardTestWrite,
} from '@/schemas/tamiyoScroll'
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
    removed_card_name: payload.removed_card_name,
    added_card_name: payload.added_card_name,
    notes: payload.notes ?? null,
    created_at: nowIso(),
    evaluations: [],
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
  test.removed_card_name = payload.removed_card_name
  test.added_card_name = payload.added_card_name
  test.notes = payload.notes ?? null
  return Promise.resolve(structuredClone(test))
}

export function deleteCardTest(testId: string): Promise<void> {
  const store = getStore()
  store.cardTests = store.cardTests.filter((test) => test.id !== testId)
  return Promise.resolve()
}

/** Demo mode has no decklist-diff computation, so it can't tell a matched
 * card test from an unmatched one — returns the deck's full list, same as
 * `listCardTests`. */
export function listCardTestChangeLog(personalDeckId: string): Promise<CardTest[]> {
  return listCardTests({ personalDeckId })
}

function findTest(testId: string): CardTest {
  const test = getStore().cardTests.find((candidate) => candidate.id === testId)
  if (!test) throw new Error(`Demo card test not found: ${testId}`)
  return test
}

export function createCardTestEvaluation(
  testId: string,
  payload: CardTestEvaluationWrite,
): Promise<CardTestEvaluation> {
  const test = findTest(testId)
  const evaluation: CardTestEvaluation = {
    id: nextId(),
    test_id: testId,
    opponent_deck_id: payload.opponent_deck_id,
    rating: payload.rating,
    notes: payload.notes ?? null,
    created_at: nowIso(),
  }
  test.evaluations.push(evaluation)
  return Promise.resolve(structuredClone(evaluation))
}

export function updateCardTestEvaluation(
  testId: string,
  evaluationId: string,
  payload: CardTestEvaluationWrite,
): Promise<CardTestEvaluation> {
  const test = findTest(testId)
  const evaluation = test.evaluations.find((candidate) => candidate.id === evaluationId)
  if (!evaluation) throw new Error(`Demo card test evaluation not found: ${evaluationId}`)
  evaluation.opponent_deck_id = payload.opponent_deck_id
  evaluation.rating = payload.rating
  evaluation.notes = payload.notes ?? null
  return Promise.resolve(structuredClone(evaluation))
}

export function deleteCardTestEvaluation(
  testId: string,
  evaluationId: string,
): Promise<void> {
  const test = findTest(testId)
  test.evaluations = test.evaluations.filter(
    (evaluation) => evaluation.id !== evaluationId,
  )
  return Promise.resolve()
}
