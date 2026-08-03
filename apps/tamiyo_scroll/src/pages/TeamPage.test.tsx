import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TeamPage } from './TeamPage'

const removeMemberMutateAsync = vi.fn().mockResolvedValue(undefined)
const updateDescriptionMutate = vi.fn()
const enableThreadMutate = vi.fn()
const postMessageMutateAsync = vi.fn().mockResolvedValue(undefined)
const flagDeckMutate = vi.fn()
const unflagDeckMutate = vi.fn()
const downloadReportMutate = vi.fn()

const OWNER = {
  user_id: 'user-owner',
  email: 'owner@example.com',
  display_name: 'Olive',
  is_owner: true,
  joined_at: '2026-01-01T00:00:00Z',
  activity_count: 5,
}
const MEMBER = {
  user_id: 'user-member',
  email: 'member@example.com',
  display_name: null,
  is_owner: false,
  joined_at: '2026-02-01T00:00:00Z',
  activity_count: 2,
}

let currentUserId = 'user-owner'
let decks: {
  name_key: string
  deck_name: string
  owners: { deck_id: string; display: string }[]
  has_thread: boolean
}[] = []
let memberDecks: {
  id: string
  name: string
  owner_id: string
  owner_display: string
  is_flagged: boolean
}[] = []
let messages: {
  id: string
  thread_id: string
  author_id: string
  author_display: string
  body: string
  created_at: string
}[] = []

beforeEach(() => {
  currentUserId = 'user-owner'
  decks = []
  memberDecks = []
  messages = []
  removeMemberMutateAsync.mockClear()
  updateDescriptionMutate.mockClear()
  enableThreadMutate.mockClear()
  postMessageMutateAsync.mockClear()
  flagDeckMutate.mockClear()
  unflagDeckMutate.mockClear()
  downloadReportMutate.mockClear()
})

vi.mock('@/hooks/useAuth', () => ({
  useCurrentUser: () => ({ data: { id: currentUserId } }),
}))

vi.mock('@/hooks/useTeams', () => ({
  useTeam: () => ({
    data: {
      id: 'team-1',
      name: 'Dream Team',
      description: 'We test cards together.',
      invite_code: 'ABCD1234',
      owner_id: 'user-owner',
      created_at: '2026-01-01T00:00:00Z',
      members: [OWNER, MEMBER],
    },
  }),
  useTeamDecks: () => ({ data: decks }),
  useMemberDecks: () => ({ data: memberDecks }),
  useFlagTeamDeck: () => ({ mutate: flagDeckMutate, isPending: false }),
  useUnflagTeamDeck: () => ({ mutate: unflagDeckMutate, isPending: false }),
  useDownloadTeamDeckReport: () => ({ mutate: downloadReportMutate, isPending: false }),
  useRemoveTeamMember: () => ({
    mutateAsync: removeMemberMutateAsync,
    isPending: false,
  }),
  useUpdateTeamDescription: () => ({
    mutate: updateDescriptionMutate,
    isPending: false,
  }),
  useEnableTeamDeckThread: () => ({ mutate: enableThreadMutate, isPending: false }),
  useTeamDeckThreadMessages: () => ({ data: messages }),
  usePostTeamDeckThreadMessage: () => ({
    mutateAsync: postMessageMutateAsync,
    isPending: false,
  }),
}))

function renderTeamPage() {
  return render(
    <MemoryRouter initialEntries={['/app/team/team-1']}>
      <Routes>
        <Route path="/app/team/:teamId" element={<TeamPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('TeamPage', () => {
  it('renders the team name and member list', () => {
    renderTeamPage()
    expect(screen.getByText('Dream Team')).toBeInTheDocument()
    expect(screen.getByText('Olive')).toBeInTheDocument()
    expect(screen.getByText('member@example.com')).toBeInTheDocument()
  })

  it('lets the owner edit and save the description', async () => {
    const user = userEvent.setup()
    renderTeamPage()

    const textarea = screen.getByLabelText('Team description')
    await user.clear(textarea)
    await user.type(textarea, 'New description')
    await user.click(screen.getByRole('button', { name: 'Save description' }))

    expect(updateDescriptionMutate).toHaveBeenCalledWith({
      teamId: 'team-1',
      description: 'New description',
    })
  })

  it('shows the invite code to the owner, with a copy button', () => {
    renderTeamPage()
    expect(screen.getByText('ABCD1234')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Copy' })).toBeInTheDocument()
  })

  it('hides the invite code from a non-owner viewer', () => {
    currentUserId = 'user-member'
    renderTeamPage()
    expect(screen.queryByText('ABCD1234')).not.toBeInTheDocument()
  })

  it('shows a remove control only for non-owner rows, owner-only', () => {
    renderTeamPage()
    const memberRow = screen.getByText('member@example.com').closest('tr')
    expect(memberRow).not.toBeNull()
    expect(
      within(memberRow!).getByRole('button', { name: /remove/i }),
    ).toBeInTheDocument()

    const ownerRow = screen.getByText('Olive').closest('tr')
    expect(
      within(ownerRow!).queryByRole('button', { name: /remove/i }),
    ).not.toBeInTheDocument()
  })

  it('hides remove controls entirely for a non-owner viewer', () => {
    currentUserId = 'user-member'
    renderTeamPage()
    expect(screen.queryByRole('button', { name: /remove/i })).not.toBeInTheDocument()
  })

  it('opens an in-page dialog instead of window.confirm when removing a member', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm')
    const user = userEvent.setup()
    renderTeamPage()

    await user.click(screen.getByRole('button', { name: /remove member@example.com/i }))

    expect(confirmSpy).not.toHaveBeenCalled()
    expect(screen.getByText('Remove member@example.com?')).toBeInTheDocument()
    confirmSpy.mockRestore()
  })

  it('removes the member after confirming in the dialog', async () => {
    const user = userEvent.setup()
    renderTeamPage()

    await user.click(screen.getByRole('button', { name: /remove member@example.com/i }))
    await user.click(screen.getByRole('button', { name: 'Remove' }))

    expect(removeMemberMutateAsync).toHaveBeenCalledWith({
      teamId: 'team-1',
      userId: 'user-member',
    })
  })

  it('cancels member removal without calling the mutation', async () => {
    const user = userEvent.setup()
    renderTeamPage()

    await user.click(screen.getByRole('button', { name: /remove member@example.com/i }))
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(screen.queryByText('Remove member@example.com?')).not.toBeInTheDocument()
    expect(removeMemberMutateAsync).not.toHaveBeenCalled()
  })

  it('shows an empty state when no deck is flagged into the team', () => {
    renderTeamPage()
    expect(
      screen.getByText(/No deck has been flagged into this team yet/),
    ).toBeInTheDocument()
  })

  it('lets the owner enable a discussion thread for a flagged name', async () => {
    decks = [
      {
        name_key: "king t'challa",
        deck_name: "King T'Challa",
        owners: [{ deck_id: 'deck-1', display: 'Olive' }],
        has_thread: false,
      },
    ]
    const user = userEvent.setup()
    renderTeamPage()

    await user.click(screen.getByRole('button', { name: 'Enable discussion thread' }))

    expect(enableThreadMutate).toHaveBeenCalledWith({
      teamId: 'team-1',
      nameKey: "king t'challa",
    })
  })

  it('lets a member post a message once a thread is enabled', async () => {
    decks = [
      {
        name_key: "king t'challa",
        deck_name: "King T'Challa",
        owners: [{ deck_id: 'deck-1', display: 'Olive' }],
        has_thread: true,
      },
    ]
    const user = userEvent.setup()
    renderTeamPage()

    await user.type(screen.getByLabelText("Message for King T'Challa"), 'Nice list!')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(postMessageMutateAsync).toHaveBeenCalledWith({
      teamId: 'team-1',
      nameKey: "king t'challa",
      body: 'Nice list!',
    })
  })

  it('downloads the cumulative report for a flagged deck', async () => {
    decks = [
      {
        name_key: "king t'challa",
        deck_name: "King T'Challa",
        owners: [{ deck_id: 'deck-1', display: 'Olive' }],
        has_thread: false,
      },
    ]
    const user = userEvent.setup()
    renderTeamPage()

    await user.click(screen.getByRole('button', { name: 'Download report (PDF)' }))

    expect(downloadReportMutate).toHaveBeenCalledWith({
      teamId: 'team-1',
      nameKey: "king t'challa",
      filename: "team-deck-report-king-t'challa.pdf",
    })
  })
})

describe('TeamPage — Flag a deck (owner-only)', () => {
  it('is hidden from a non-owner viewer', () => {
    currentUserId = 'user-member'
    memberDecks = [
      {
        id: 'deck-1',
        name: 'Mono Red',
        owner_id: 'user-owner',
        owner_display: 'Olive',
        is_flagged: false,
      },
    ]
    renderTeamPage()
    expect(screen.queryByText('Flag a deck')).not.toBeInTheDocument()
  })

  it("lists every current member's decks with a flag toggle", () => {
    memberDecks = [
      {
        id: 'deck-1',
        name: 'Mono Red',
        owner_id: 'user-owner',
        owner_display: 'Olive',
        is_flagged: false,
      },
      {
        id: 'deck-2',
        name: 'Boros Aggro',
        owner_id: 'user-member',
        owner_display: 'member@example.com',
        is_flagged: true,
      },
    ]
    renderTeamPage()

    expect(screen.getByText('Mono Red')).toBeInTheDocument()
    expect(screen.getByText('Boros Aggro')).toBeInTheDocument()
    expect(
      screen.getByRole('switch', { name: 'Flag Mono Red into this team' }),
    ).toHaveAttribute('aria-checked', 'false')
    expect(
      screen.getByRole('switch', { name: 'Flag Boros Aggro into this team' }),
    ).toHaveAttribute('aria-checked', 'true')
  })

  it('flags a deck on toggle', async () => {
    memberDecks = [
      {
        id: 'deck-1',
        name: 'Mono Red',
        owner_id: 'user-owner',
        owner_display: 'Olive',
        is_flagged: false,
      },
    ]
    const user = userEvent.setup()
    renderTeamPage()

    await user.click(screen.getByRole('switch', { name: 'Flag Mono Red into this team' }))

    expect(flagDeckMutate).toHaveBeenCalledWith({ teamId: 'team-1', deckId: 'deck-1' })
  })

  it('unflags a deck on toggle off', async () => {
    memberDecks = [
      {
        id: 'deck-1',
        name: 'Mono Red',
        owner_id: 'user-owner',
        owner_display: 'Olive',
        is_flagged: true,
      },
    ]
    const user = userEvent.setup()
    renderTeamPage()

    await user.click(screen.getByRole('switch', { name: 'Flag Mono Red into this team' }))

    expect(unflagDeckMutate).toHaveBeenCalledWith({
      teamId: 'team-1',
      nameKey: 'mono red',
    })
  })
})
