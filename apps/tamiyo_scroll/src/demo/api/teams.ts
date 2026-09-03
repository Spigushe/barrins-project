import type {
  MemberDeck,
  Team,
  TeamDeck,
  TeamDeckMessage,
  TeamSummary,
} from '@/schemas/tamiyoScroll'
import {
  DEMO_CURRENT_USER_ID,
  type DemoTeam,
  getStore,
  nextId,
  nowIso,
} from '../demoStore'

/** Mirrors `src/api/teams.ts` — see `../api/types.ts` for the compile-time proof. */

function nameKeyOf(name: string): string {
  return name.trim().toLowerCase()
}

function findTeam(teamId: string): DemoTeam {
  const team = getStore().teams.find((candidate) => candidate.id === teamId)
  if (!team) throw new Error(`Demo team not found: ${teamId}`)
  return team
}

function toTeam(team: DemoTeam): Team {
  return {
    id: team.id,
    name: team.name,
    description: team.description,
    invite_code: team.invite_code,
    owner_id: team.owner_id,
    created_at: team.created_at,
    members: structuredClone(team.members),
  }
}

function teamDeckRow(team: DemoTeam, nameKey: string): TeamDeck {
  const owners = team.memberDecks.filter((deck) => nameKeyOf(deck.name) === nameKey)
  return {
    name_key: nameKey,
    deck_name: owners[0]?.name ?? nameKey,
    owners: owners.map((deck) => ({ deck_id: deck.id, display: deck.owner_display })),
    has_thread: nameKey in team.threads,
  }
}

export function listMyTeams(): Promise<TeamSummary[]> {
  const teams = getStore().teams.filter((team) =>
    team.members.some((member) => member.user_id === DEMO_CURRENT_USER_ID),
  )
  return Promise.resolve(
    teams.map((team) => ({
      id: team.id,
      name: team.name,
      is_owner: team.owner_id === DEMO_CURRENT_USER_ID,
      invite_code: team.invite_code,
    })),
  )
}

export function getTeam(teamId: string): Promise<Team> {
  return Promise.resolve(toTeam(findTeam(teamId)))
}

export function getTeamByCode(inviteCode: string): Promise<Team> {
  const code = inviteCode.trim().toUpperCase().replace(/-/g, '')
  const team = getStore().teams.find((candidate) => candidate.invite_code === code)
  if (!team) throw new Error(`Demo team not found for code: ${inviteCode}`)
  return Promise.resolve(toTeam(team))
}

export function createTeam(name: string): Promise<Team> {
  const store = getStore()
  const currentUser = store.teams
    .flatMap((team) => team.members)
    .find((member) => member.user_id === DEMO_CURRENT_USER_ID)
  const team: DemoTeam = {
    id: nextId(),
    name,
    description: null,
    invite_code: nextId().slice(0, 8).toUpperCase(),
    owner_id: DEMO_CURRENT_USER_ID,
    created_at: nowIso(),
    members: [
      {
        user_id: DEMO_CURRENT_USER_ID,
        username: currentUser?.username ?? 'you_demo',
        display_name: currentUser?.display_name ?? 'You (Demo)',
        is_owner: true,
        joined_at: nowIso(),
        activity_count: 0,
      },
    ],
    memberDecks: [],
    flaggedNameKeys: [],
    threads: {},
  }
  store.teams.push(team)
  return Promise.resolve(toTeam(team))
}

export function joinTeam(inviteCode: string): Promise<Team> {
  const store = getStore()
  const team = store.teams.find((candidate) => candidate.invite_code === inviteCode)
  if (!team) throw new Error(`Demo team not found for invite code: ${inviteCode}`)
  if (!team.members.some((member) => member.user_id === DEMO_CURRENT_USER_ID)) {
    team.members.push({
      user_id: DEMO_CURRENT_USER_ID,
      username: 'you_demo',
      display_name: 'You (Demo)',
      is_owner: false,
      joined_at: nowIso(),
      activity_count: 0,
    })
  }
  return Promise.resolve(toTeam(team))
}

export function updateTeamDescription(
  teamId: string,
  description: string | null,
): Promise<Team> {
  const team = findTeam(teamId)
  team.description = description
  return Promise.resolve(toTeam(team))
}

export function deleteTeam(teamId: string, _inviteCode: string): Promise<void> {
  const store = getStore()
  store.teams = store.teams.filter((team) => team.id !== teamId)
  return Promise.resolve()
}

export function leaveTeam(teamId: string): Promise<void> {
  const team = findTeam(teamId)
  team.members = team.members.filter((member) => member.user_id !== DEMO_CURRENT_USER_ID)
  return Promise.resolve()
}

export function removeTeamMember(teamId: string, userId: string): Promise<void> {
  const team = findTeam(teamId)
  team.members = team.members.filter((member) => member.user_id !== userId)
  return Promise.resolve()
}

export function listTeamDecks(teamId: string): Promise<TeamDeck[]> {
  const team = findTeam(teamId)
  return Promise.resolve(
    team.flaggedNameKeys.map((nameKey) => teamDeckRow(team, nameKey)),
  )
}

export function listMemberDecks(teamId: string): Promise<MemberDeck[]> {
  const team = findTeam(teamId)
  return Promise.resolve(
    team.memberDecks.map((deck) => ({
      id: deck.id,
      name: deck.name,
      owner_id: deck.owner_id,
      owner_display: deck.owner_display,
      is_flagged: team.flaggedNameKeys.includes(nameKeyOf(deck.name)),
    })),
  )
}

export function flagTeamDeck(teamId: string, deckId: string): Promise<TeamDeck> {
  const team = findTeam(teamId)
  const deck = team.memberDecks.find((candidate) => candidate.id === deckId)
  if (!deck) throw new Error(`Demo member deck not found: ${deckId}`)
  const nameKey = nameKeyOf(deck.name)
  if (!team.flaggedNameKeys.includes(nameKey)) team.flaggedNameKeys.push(nameKey)
  return Promise.resolve(teamDeckRow(team, nameKey))
}

export function unflagTeamDeck(teamId: string, nameKey: string): Promise<void> {
  const team = findTeam(teamId)
  team.flaggedNameKeys = team.flaggedNameKeys.filter((key) => key !== nameKey)
  return Promise.resolve()
}

/** Placeholder PDF blob — no WeasyPrint call, no network, just enough for the "Download report" button to work. */
export function getTeamDeckReportPdf(_teamId: string, _nameKey: string): Promise<Blob> {
  return Promise.resolve(
    new Blob(['Demo mode — no real report is generated.'], { type: 'application/pdf' }),
  )
}

export function enableTeamDeckThread(teamId: string, nameKey: string): Promise<void> {
  const team = findTeam(teamId)
  if (!(nameKey in team.threads)) team.threads[nameKey] = []
  return Promise.resolve()
}

export function listTeamDeckThreadMessages(
  teamId: string,
  nameKey: string,
): Promise<TeamDeckMessage[]> {
  const team = findTeam(teamId)
  return Promise.resolve(structuredClone(team.threads[nameKey] ?? []))
}

export function postTeamDeckThreadMessage(
  teamId: string,
  nameKey: string,
  body: string,
): Promise<TeamDeckMessage> {
  const team = findTeam(teamId)
  const author = team.members.find((member) => member.user_id === DEMO_CURRENT_USER_ID)
  const message: TeamDeckMessage = {
    id: nextId(),
    thread_id: nextId(),
    author_id: DEMO_CURRENT_USER_ID,
    author_display: author?.display_name ?? author?.username ?? 'You (Demo)',
    body,
    created_at: nowIso(),
  }
  const thread = team.threads[nameKey] ?? []
  thread.push(message)
  team.threads[nameKey] = thread
  return Promise.resolve(structuredClone(message))
}
