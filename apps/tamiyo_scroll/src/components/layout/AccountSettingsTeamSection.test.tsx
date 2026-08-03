import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/api/client'
import { AccountSettingsTeamSection } from './AccountSettingsTeamSection'

const createTeamMutateAsync = vi.fn().mockResolvedValue(undefined)
const joinTeamMutateAsync = vi.fn().mockResolvedValue(undefined)
const leaveTeamMutateAsync = vi.fn().mockResolvedValue(undefined)
const deleteTeamMutateAsync = vi.fn().mockResolvedValue(undefined)

let myTeams: { id: string; name: string; is_owner: boolean }[] = []
let team:
  { id: string; name: string; invite_code: string; owner_id: string } | undefined =
  undefined

const CURRENT_USER_ID = 'user-alice'

beforeEach(() => {
  createTeamMutateAsync.mockClear()
  joinTeamMutateAsync.mockClear()
  leaveTeamMutateAsync.mockClear()
  deleteTeamMutateAsync.mockClear()
  myTeams = []
  team = undefined
})

vi.mock('@/hooks/useAuth', () => ({
  useCurrentUser: () => ({ data: { id: CURRENT_USER_ID, email: 'alice@example.com' } }),
}))

vi.mock('@/hooks/useTeams', () => ({
  useMyTeams: () => ({ data: myTeams }),
  useTeam: () => ({ data: team }),
  useCreateTeam: () => ({ mutateAsync: createTeamMutateAsync, isPending: false }),
  useJoinTeam: () => ({ mutateAsync: joinTeamMutateAsync, isPending: false }),
  useLeaveTeam: () => ({ mutateAsync: leaveTeamMutateAsync, isPending: false }),
  useDeleteTeam: () => ({ mutateAsync: deleteTeamMutateAsync, isPending: false }),
}))

function renderSection() {
  return render(
    <MemoryRouter>
      <AccountSettingsTeamSection onClose={vi.fn()} />
    </MemoryRouter>,
  )
}

describe('AccountSettingsTeamSection — no team', () => {
  it('renders the join/create picker', () => {
    renderSection()
    expect(screen.getByText('Join a team')).toBeInTheDocument()
    expect(screen.getByText('Create a team')).toBeInTheDocument()
  })

  it('joins a team via invite code', async () => {
    const user = userEvent.setup()
    renderSection()

    await user.click(screen.getByText('Join a team'))
    await user.type(screen.getByLabelText('Invite code'), 'abcd1234')
    await user.click(screen.getByRole('button', { name: 'Join' }))

    expect(joinTeamMutateAsync).toHaveBeenCalledWith('abcd1234')
  })

  it('shows the error message when joining fails', async () => {
    joinTeamMutateAsync.mockRejectedValueOnce(new ApiError(400, 'Invalid invite code.'))
    const user = userEvent.setup()
    renderSection()

    await user.click(screen.getByText('Join a team'))
    await user.type(screen.getByLabelText('Invite code'), 'WRONGCOD')
    await user.click(screen.getByRole('button', { name: 'Join' }))

    expect(await screen.findByText('Invalid invite code.')).toBeInTheDocument()
  })

  it('creates a team by name', async () => {
    const user = userEvent.setup()
    renderSection()

    await user.click(screen.getByText('Create a team'))
    await user.type(screen.getByLabelText('Team name'), 'Dream Team')
    await user.click(screen.getByRole('button', { name: 'Create' }))

    expect(createTeamMutateAsync).toHaveBeenCalledWith('Dream Team')
  })
})

describe('AccountSettingsTeamSection — member of a team', () => {
  beforeEach(() => {
    myTeams = [{ id: 'team-1', name: 'Dream Team', is_owner: false }]
    team = {
      id: 'team-1',
      name: 'Dream Team',
      invite_code: 'ABCD1234',
      owner_id: 'user-bob',
    }
  })

  it('shows the team name, a Member badge, and a leave button', () => {
    renderSection()
    expect(screen.getByText('Dream Team')).toBeInTheDocument()
    expect(screen.getByText('Member')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Leave team' })).toBeInTheDocument()
  })

  it('does not show the invite code to a non-owner', () => {
    renderSection()
    expect(screen.queryByText('ABCD1234')).not.toBeInTheDocument()
  })

  it('leaves the team on click', async () => {
    const user = userEvent.setup()
    renderSection()

    await user.click(screen.getByRole('button', { name: 'Leave team' }))

    expect(leaveTeamMutateAsync).toHaveBeenCalledWith('team-1')
  })
})

describe('AccountSettingsTeamSection — team owner', () => {
  beforeEach(() => {
    myTeams = [{ id: 'team-1', name: 'Dream Team', is_owner: true }]
    team = {
      id: 'team-1',
      name: 'Dream Team',
      invite_code: 'ABCD1234',
      owner_id: CURRENT_USER_ID,
    }
  })

  it('shows the Owner badge and the invite code', () => {
    renderSection()
    expect(screen.getByText('Owner')).toBeInTheDocument()
    expect(screen.getByText('ABCD1234')).toBeInTheDocument()
  })

  it('shows "Copied!" feedback after copying the invite code', async () => {
    const user = userEvent.setup()
    renderSection()

    await user.click(screen.getByRole('button', { name: 'Copy' }))

    expect(await screen.findByText('Copied!')).toBeInTheDocument()
  })

  it('opens an in-page dialog instead of window.confirm when deleting', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm')
    const user = userEvent.setup()
    renderSection()

    await user.click(screen.getByRole('button', { name: 'Delete team' }))

    expect(confirmSpy).not.toHaveBeenCalled()
    expect(screen.getByText('Delete "Dream Team"?')).toBeInTheDocument()
    confirmSpy.mockRestore()
  })

  it('requires the exact invite code before deleting', async () => {
    const user = userEvent.setup()
    renderSection()

    await user.click(screen.getByRole('button', { name: 'Delete team' }))
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    await user.type(
      screen.getByLabelText('Type the invite code to confirm deletion'),
      'ABCD1234',
    )
    await user.click(screen.getByRole('button', { name: 'Delete permanently' }))

    expect(deleteTeamMutateAsync).toHaveBeenCalledWith({
      teamId: 'team-1',
      inviteCode: 'ABCD1234',
    })
  })

  it('shows the error and keeps the dialog open when deletion fails', async () => {
    deleteTeamMutateAsync.mockRejectedValueOnce(
      new ApiError(400, 'Invite code does not match.'),
    )
    const user = userEvent.setup()
    renderSection()

    await user.click(screen.getByRole('button', { name: 'Delete team' }))
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    await user.type(
      screen.getByLabelText('Type the invite code to confirm deletion'),
      'WRONGCOD',
    )
    await user.click(screen.getByRole('button', { name: 'Delete permanently' }))

    expect(await screen.findByText('Invite code does not match.')).toBeInTheDocument()
  })

  it('cancels the delete dialog without deleting', async () => {
    const user = userEvent.setup()
    renderSection()

    await user.click(screen.getByRole('button', { name: 'Delete team' }))
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(screen.queryByText('Delete "Dream Team"?')).not.toBeInTheDocument()
    expect(deleteTeamMutateAsync).not.toHaveBeenCalled()
  })
})
