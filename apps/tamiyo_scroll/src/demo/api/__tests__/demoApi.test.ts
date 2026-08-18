import { beforeEach, describe, expect, it } from 'vitest'
import * as realCardTestsApi from '@/api/cardTests'
import * as realMatchesApi from '@/api/matches'
import * as realMetaDecksApi from '@/api/metaDecks'
import * as realPersonalDecksApi from '@/api/personalDecks'
import * as realSessionsApi from '@/api/sessions'
import * as realStatsApi from '@/api/stats'
import * as realTeamsApi from '@/api/teams'
import {
  archetypeSummarySchema,
  cardTestSchema,
  decklistVersionSchema,
  decklistViewSchema,
  matchSchema,
  matchupSummarySchema,
  memberDeckSchema,
  metaDeckSchema,
  personalDeckSchema,
  sessionComparisonSchema,
  sessionSchema,
  teamDeckMessageSchema,
  teamDeckSchema,
  teamSchema,
  teamSummarySchema,
} from '@/schemas/tamiyoScroll'
import { DEMO_CURRENT_USER_ID, resetDemoStore } from '../../demoStore'
import fixtures from '../../fixtures.json'
import * as demoCardTestsApi from '../cardTests'
import * as demoMatchesApi from '../matches'
import * as demoMetaDecksApi from '../metaDecks'
import * as demoPersonalDecksApi from '../personalDecks'
import * as demoSessionsApi from '../sessions'
import * as demoStatsApi from '../stats'
import * as demoTeamsApi from '../teams'

const DECK_ID = fixtures.personalDecks[0].id
const TEAM_ID = fixtures.teams[0].id

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
    ['sessions', realSessionsApi, demoSessionsApi],
    ['teams', realTeamsApi, demoTeamsApi],
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
    const view = await demoPersonalDecksApi.getDecklistView(DECK_ID)
    decklistViewSchema.parse(view)
    expect(view.library_cards.length).toBeGreaterThan(0)
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

  it('computes conversion as top8/presence on a 0-100 scale, always fresh from storage', async () => {
    const decks = await demoMetaDecksApi.listMetaDecks()
    const monoWhite = decks.find((deck) => deck.name === 'Mono White Aggro')
    expect(monoWhite).toBeDefined()
    expect(monoWhite?.conversion).toBeCloseTo(
      (monoWhite!.top8 / monoWhite!.presence) * 100,
      2,
    )
  })

  it('keeps the sum of seeded top8 counts at or under 8 (only 8 seats in a top 8)', async () => {
    const decks = await demoMetaDecksApi.listMetaDecks()
    const total = decks.reduce((sum, deck) => sum + deck.top8, 0)
    expect(total).toBeLessThanOrEqual(8)
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
      personal_deck_id: DECK_ID,
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
      personal_deck_id: DECK_ID,
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

  it('reports winrate as a 0-100 percentage (game-level tally, not match-level majority)', async () => {
    // f36f82f5.../4259faaa... (Boros vs. Golgari) is a single 2-0 match in the
    // fixtures: 2 decisive games, both wins — 100%, not the 0-1 fraction a
    // match-level-majority calculation used to produce.
    const summary = await demoStatsApi.getMatchupSummary({ personalDeckId: DECK_ID })
    const row = summary.rows.find(
      (r) => r.opponent_deck_id === '4259faaa-431d-4d0c-9b20-b70436558af4',
    )
    expect(row?.winrate_global).toBe(100)
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

describe('demo sessions api', () => {
  beforeEach(() => {
    resetDemoStore()
  })

  it('lists the seeded session, matching the real schema', async () => {
    const sessions = await demoSessionsApi.listSessions(DECK_ID)
    expect(sessions.length).toBeGreaterThan(0)
    for (const session of sessions) sessionSchema.parse(session)
  })

  it('creates, closes/reopens, and archives a session', async () => {
    const created = await demoSessionsApi.createSession({
      name: 'Regional Qualifier',
      type: 'tournament',
      personal_deck_id: DECK_ID,
    })
    sessionSchema.parse(created)
    expect(created.ended_at).toBeNull()

    const closed = await demoSessionsApi.updateSession(created.id, { close: true })
    expect(closed.ended_at).not.toBeNull()

    const reopened = await demoSessionsApi.updateSession(created.id, { reopen: true })
    expect(reopened.ended_at).toBeNull()

    await demoSessionsApi.archiveSession(created.id)
    const active = await demoSessionsApi.listSessions(DECK_ID)
    expect(active.find((session) => session.id === created.id)).toBeUndefined()
  })

  it('compares the seeded session against its baseline, matching the real schema', async () => {
    const [session] = await demoSessionsApi.listSessions(DECK_ID)
    const comparison = await demoSessionsApi.getSessionComparison(session.id)
    sessionComparisonSchema.parse(comparison)
    // The seeded session has 2 logged matches (see fixtures.json).
    expect(comparison.session_match_count).toBe(2)
  })

  it('returns a downloadable blob for the session report', async () => {
    const [session] = await demoSessionsApi.listSessions(DECK_ID)
    const blob = await demoSessionsApi.getSessionReportPdf(session.id)
    expect(blob).toBeInstanceOf(Blob)
  })
})

describe('demo teams api', () => {
  beforeEach(() => {
    resetDemoStore()
  })

  it('lists the seeded team for the demo user, matching the real schema', async () => {
    const teams = await demoTeamsApi.listMyTeams()
    expect(teams.length).toBeGreaterThan(0)
    for (const team of teams) teamSummarySchema.parse(team)
    expect(teams.find((team) => team.id === TEAM_ID)?.is_owner).toBe(true)
  })

  it('gets the seeded team, matching the real schema', async () => {
    const team = await demoTeamsApi.getTeam(TEAM_ID)
    teamSchema.parse(team)
    expect(team.owner_id).toBe(DEMO_CURRENT_USER_ID)
    expect(team.members.length).toBeGreaterThan(1)
  })

  it('creates a team owned by the demo user', async () => {
    const created = await demoTeamsApi.createTeam('New Team')
    teamSchema.parse(created)
    expect(created.owner_id).toBe(DEMO_CURRENT_USER_ID)
    expect(created.members).toHaveLength(1)
  })

  it('joins a team by invite code', async () => {
    const other = await demoTeamsApi.createTeam('Other Team')
    // Simulate joining from scratch by removing self first.
    await demoTeamsApi.leaveTeam(other.id)
    const joined = await demoTeamsApi.joinTeam(other.invite_code)
    expect(joined.members.some((m) => m.user_id === DEMO_CURRENT_USER_ID)).toBe(true)
  })

  it('updates the team description', async () => {
    const updated = await demoTeamsApi.updateTeamDescription(TEAM_ID, 'New description')
    expect(updated.description).toBe('New description')
  })

  it('removes a member and leaves a team', async () => {
    const before = await demoTeamsApi.getTeam(TEAM_ID)
    const other = before.members.find((m) => m.user_id !== DEMO_CURRENT_USER_ID)
    expect(other).toBeDefined()

    await demoTeamsApi.removeTeamMember(TEAM_ID, other!.user_id)
    const afterRemove = await demoTeamsApi.getTeam(TEAM_ID)
    expect(afterRemove.members.find((m) => m.user_id === other!.user_id)).toBeUndefined()

    await demoTeamsApi.leaveTeam(TEAM_ID)
    const afterLeave = await demoTeamsApi.getTeam(TEAM_ID)
    expect(
      afterLeave.members.find((m) => m.user_id === DEMO_CURRENT_USER_ID),
    ).toBeUndefined()
  })

  it('deletes a team', async () => {
    const created = await demoTeamsApi.createTeam('Doomed Team')
    await demoTeamsApi.deleteTeam(created.id, created.invite_code)
    const teams = await demoTeamsApi.listMyTeams()
    expect(teams.find((team) => team.id === created.id)).toBeUndefined()
  })

  it('lists member decks and flagged team decks, matching the real schemas', async () => {
    const memberDecks = await demoTeamsApi.listMemberDecks(TEAM_ID)
    expect(memberDecks.length).toBeGreaterThan(0)
    for (const deck of memberDecks) memberDeckSchema.parse(deck)
    expect(memberDecks.filter((deck) => deck.is_flagged).length).toBeGreaterThan(0)

    const teamDecks = await demoTeamsApi.listTeamDecks(TEAM_ID)
    expect(teamDecks.length).toBeGreaterThan(0)
    for (const deck of teamDecks) teamDeckSchema.parse(deck)
  })

  it('flags and unflags a member deck', async () => {
    const memberDecks = await demoTeamsApi.listMemberDecks(TEAM_ID)
    const unflagged = memberDecks.find((deck) => !deck.is_flagged)
    expect(unflagged).toBeDefined()

    const flagged = await demoTeamsApi.flagTeamDeck(TEAM_ID, unflagged!.id)
    teamDeckSchema.parse(flagged)
    expect(flagged.name_key).toBe(unflagged!.name.trim().toLowerCase())

    await demoTeamsApi.unflagTeamDeck(TEAM_ID, flagged.name_key)
    const teamDecks = await demoTeamsApi.listTeamDecks(TEAM_ID)
    expect(teamDecks.find((deck) => deck.name_key === flagged.name_key)).toBeUndefined()
  })

  it('returns a downloadable blob for the team deck report', async () => {
    const [deck] = await demoTeamsApi.listTeamDecks(TEAM_ID)
    const blob = await demoTeamsApi.getTeamDeckReportPdf(TEAM_ID, deck.name_key)
    expect(blob).toBeInstanceOf(Blob)
  })

  it('enables a discussion thread and posts/lists messages', async () => {
    const memberDecks = await demoTeamsApi.listMemberDecks(TEAM_ID)
    const flaggedNoThread = memberDecks.find((deck) => deck.is_flagged)
    expect(flaggedNoThread).toBeDefined()
    const nameKey = flaggedNoThread!.name.trim().toLowerCase()

    let teamDecks = await demoTeamsApi.listTeamDecks(TEAM_ID)
    const beforeThread = teamDecks.find((deck) => deck.name_key === nameKey)
    if (!beforeThread?.has_thread) {
      await demoTeamsApi.enableTeamDeckThread(TEAM_ID, nameKey)
    }

    const posted = await demoTeamsApi.postTeamDeckThreadMessage(
      TEAM_ID,
      nameKey,
      'Nice line last round.',
    )
    teamDeckMessageSchema.parse(posted)
    expect(posted.author_id).toBe(DEMO_CURRENT_USER_ID)

    const messages = await demoTeamsApi.listTeamDeckThreadMessages(TEAM_ID, nameKey)
    expect(messages.some((m) => m.id === posted.id)).toBe(true)

    teamDecks = await demoTeamsApi.listTeamDecks(TEAM_ID)
    expect(teamDecks.find((deck) => deck.name_key === nameKey)?.has_thread).toBe(true)
  })
})
