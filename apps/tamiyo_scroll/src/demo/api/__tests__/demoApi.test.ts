import { beforeEach, describe, expect, it } from 'vitest'
import * as realCardTestsApi from '@/api/cardTests'
import * as realMatchesApi from '@/api/matches'
import * as realMetaDecksApi from '@/api/metaDecks'
import * as realPersonalDecksApi from '@/api/personalDecks'
import * as realStatsApi from '@/api/stats'
import {
  archetypeSummarySchema,
  cardTestSchema,
  decklistLineSchema,
  decklistVersionSchema,
  matchSchema,
  matchupSummarySchema,
  metaDeckSchema,
  personalDeckSchema,
} from '@/schemas/tamiyoScroll'
import { resetDemoStore } from '../../demoStore'
import fixtures from '../../fixtures.json'
import * as demoCardTestsApi from '../cardTests'
import * as demoMatchesApi from '../matches'
import * as demoMetaDecksApi from '../metaDecks'
import * as demoPersonalDecksApi from '../personalDecks'
import * as demoStatsApi from '../stats'

const DECK_ID = fixtures.personalDecks[0].id

// The compile-time proof lives in `../types.ts` + `../_typecheck.ts` (`tsc
// -b`, run by `npm run build`, fails if a signature drifts). This is the
// runtime companion: every demo module must export exactly the same
// function *names* as the real module it mirrors.
describe('demo api modules mirror the real api modules', () => {
  it.each([
    ['personalDecks', realPersonalDecksApi, demoPersonalDecksApi],
    ['matches', realMatchesApi, demoMatchesApi],
    ['metaDecks', realMetaDecksApi, demoMetaDecksApi],
    ['cardTests', realCardTestsApi, demoCardTestsApi],
    ['stats', realStatsApi, demoStatsApi],
  ])('%s exports the same function names as the real module', (_label, real, demo) => {
    expect(Object.keys(demo).sort()).toEqual(Object.keys(real).sort())
  })
})

describe('demo personalDecks api', () => {
  beforeEach(() => {
    resetDemoStore()
  })

  it('lists the seeded personal decks, matching the real schema', async () => {
    const decks = await demoPersonalDecksApi.listPersonalDecks()
    expect(decks.length).toBeGreaterThan(0)
    for (const deck of decks) personalDeckSchema.parse(deck)
  })

  it('creates, updates (rename/game/category) and archives a deck', async () => {
    const created = await demoPersonalDecksApi.createPersonalDeck({
      name: 'New Deck',
      game: 'magic',
      category: 'midrange',
    })
    personalDeckSchema.parse(created)

    const renamed = await demoPersonalDecksApi.updatePersonalDeck(created.id, {
      name: 'Renamed Deck',
    })
    expect(renamed.name).toBe('Renamed Deck')
    expect(renamed.category).toBe('midrange')

    const recategorized = await demoPersonalDecksApi.updatePersonalDeck(created.id, {
      category: 'control',
    })
    expect(recategorized.name).toBe('Renamed Deck')
    expect(recategorized.category).toBe('control')

    await demoPersonalDecksApi.archivePersonalDeck(created.id)
    const active = await demoPersonalDecksApi.listPersonalDecks()
    expect(active.find((deck) => deck.id === created.id)).toBeUndefined()

    const includingArchived = await demoPersonalDecksApi.listPersonalDecks({
      includeArchived: true,
    })
    expect(includingArchived.find((deck) => deck.id === created.id)).toBeDefined()
  })

  it('manages decklist versions for a deck', async () => {
    const versions = await demoPersonalDecksApi.listDecklistVersions(DECK_ID)
    expect(versions.length).toBeGreaterThan(0)
    for (const version of versions) decklistVersionSchema.parse(version)

    const created = await demoPersonalDecksApi.createDecklistVersion(
      DECK_ID,
      '1 Test Card',
    )
    expect(created.version).toBe(versions[0].version + 1)

    const imported = await demoPersonalDecksApi.importMoxfield(
      DECK_ID,
      'https://moxfield.com/decks/example',
    )
    expect(imported.source).toBe('moxfield_import')

    await demoPersonalDecksApi.deleteDecklistVersion(DECK_ID, created.id)
    const after = await demoPersonalDecksApi.listDecklistVersions(DECK_ID)
    expect(after.find((version) => version.id === created.id)).toBeUndefined()
  })

  it('returns the decklist view', async () => {
    const lines = await demoPersonalDecksApi.getDecklistView(DECK_ID)
    expect(lines.length).toBeGreaterThan(0)
    for (const line of lines) decklistLineSchema.parse(line)
  })

  it('returns a downloadable blob for the deck report', async () => {
    const blob = await demoPersonalDecksApi.getDeckReportPdf(DECK_ID)
    expect(blob).toBeInstanceOf(Blob)
  })

  it('resets to the original fixtures on resetDemoStore()', async () => {
    const before = await demoPersonalDecksApi.listPersonalDecks()
    await demoPersonalDecksApi.createPersonalDeck({
      name: 'Temporary',
      game: 'magic',
      category: 'midrange',
    })
    resetDemoStore()
    const after = await demoPersonalDecksApi.listPersonalDecks()
    expect(after).toEqual(before)
  })
})

describe('demo matches api', () => {
  beforeEach(() => {
    resetDemoStore()
  })

  it('lists matches for a personal deck, matching the real schema', async () => {
    const matches = await demoMatchesApi.listMatches(DECK_ID)
    expect(matches.length).toBeGreaterThan(0)
    for (const match of matches) matchSchema.parse(match)
  })

  it('creates, updates and deletes a match', async () => {
    const [opponent] = await demoMetaDecksApi.listMetaDecks()

    const created = await demoMatchesApi.createMatch({
      personal_deck_id: DECK_ID,
      opponent_deck_id: opponent.id,
      on_play: true,
      game1: 'win',
      game2: 'win',
      game3: null,
    })
    matchSchema.parse(created)

    const updated = await demoMatchesApi.updateMatch(created.id, {
      personal_deck_id: DECK_ID,
      opponent_deck_id: opponent.id,
      on_play: false,
      game1: 'loss',
      game2: 'loss',
      game3: null,
    })
    expect(updated.on_play).toBe(false)
    expect(updated.game1).toBe('loss')

    await demoMatchesApi.deleteMatch(created.id)
    const after = await demoMatchesApi.listMatches(DECK_ID)
    expect(after.find((match) => match.id === created.id)).toBeUndefined()
  })
})

describe('demo metaDecks api', () => {
  beforeEach(() => {
    resetDemoStore()
  })

  it('lists the seeded meta decks, matching the real schema', async () => {
    const decks = await demoMetaDecksApi.listMetaDecks()
    expect(decks.length).toBeGreaterThan(0)
    for (const deck of decks) metaDeckSchema.parse(deck)
  })

  it('creates, updates and archives a meta deck', async () => {
    const created = await demoMetaDecksApi.createMetaDeck({
      name: 'New Meta Deck',
      tier: 2,
      category: 'aggro',
      decklist_notes: null,
      top8: 1,
      presence: 2,
      expected: 'as_expected',
      tests_status: null,
    })
    metaDeckSchema.parse(created)

    const updated = await demoMetaDecksApi.updateMetaDeck(created.id, {
      name: 'New Meta Deck',
      tier: 1,
      category: 'aggro',
      decklist_notes: 'Updated notes',
      top8: 3,
      presence: 6,
      expected: 'more_expected',
      tests_status: null,
    })
    expect(updated.tier).toBe(1)
    expect(updated.decklist_notes).toBe('Updated notes')

    await demoMetaDecksApi.archiveMetaDeck(created.id)
    const active = await demoMetaDecksApi.listMetaDecks()
    expect(active.find((deck) => deck.id === created.id)).toBeUndefined()
  })
})

describe('demo cardTests api', () => {
  beforeEach(() => {
    resetDemoStore()
  })

  it('lists card tests for a personal deck, matching the real schema', async () => {
    const tests = await demoCardTestsApi.listCardTests({ personalDeckId: DECK_ID })
    expect(tests.length).toBeGreaterThan(0)
    for (const test of tests) cardTestSchema.parse(test)
  })

  it('creates, updates and deletes a card test', async () => {
    const created = await demoCardTestsApi.createCardTest({
      personal_deck_id: DECK_ID,
      tester: 'Demo tester',
      card_name: 'Test Card',
      opponent_deck_id: null,
      rating: 3,
      notes: null,
    })
    cardTestSchema.parse(created)

    const updated = await demoCardTestsApi.updateCardTest(created.id, {
      personal_deck_id: DECK_ID,
      tester: 'Demo tester',
      card_name: 'Test Card',
      opponent_deck_id: null,
      rating: 5,
      notes: 'Now excellent',
    })
    expect(updated.rating).toBe(5)

    await demoCardTestsApi.deleteCardTest(created.id)
    const after = await demoCardTestsApi.listCardTests({ personalDeckId: DECK_ID })
    expect(after.find((test) => test.id === created.id)).toBeUndefined()
  })
})

describe('demo stats api', () => {
  beforeEach(() => {
    resetDemoStore()
  })

  it('derives an archetype summary from the seeded matches, matching the real schema', async () => {
    const summary = await demoStatsApi.getArchetypeSummary({ personalDeckId: DECK_ID })
    expect(summary.length).toBeGreaterThan(0)
    for (const entry of summary) archetypeSummarySchema.parse(entry)
  })

  it('derives a matchup summary from the seeded matches, matching the real schema', async () => {
    const summary = await demoStatsApi.getMatchupSummary({ personalDeckId: DECK_ID })
    matchupSummarySchema.parse(summary)
    expect(summary.rows.length).toBeGreaterThan(0)
  })

  it('reacts to a newly logged match', async () => {
    const before = await demoStatsApi.getMatchupSummary({ personalDeckId: DECK_ID })
    const [opponent] = await demoMetaDecksApi.listMetaDecks()
    const beforeRow = before.rows.find((row) => row.opponent_deck_id === opponent.id)
    const beforeCount = beforeRow?.match_count ?? 0

    await demoMatchesApi.createMatch({
      personal_deck_id: DECK_ID,
      opponent_deck_id: opponent.id,
      on_play: true,
      game1: 'win',
      game2: 'win',
      game3: null,
    })

    const after = await demoStatsApi.getMatchupSummary({ personalDeckId: DECK_ID })
    const afterRow = after.rows.find((row) => row.opponent_deck_id === opponent.id)
    expect(afterRow?.match_count).toBe(beforeCount + 1)
  })
})
