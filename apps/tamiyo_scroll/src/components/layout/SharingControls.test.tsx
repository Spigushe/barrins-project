import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SharingControls, SharingControlsContent } from './SharingControls'

const updateSettingsMutateAsync = vi.fn()
const setViewingOwnerMock = vi.fn()
const createReceiveOptInMutateAsync = vi.fn()
const deleteReceiveOptInMutateAsync = vi.fn()

vi.mock('@/hooks/useAuth', () => ({
  useCurrentUser: () => ({ data: { email: 'alice@example.com' } }),
}))

vi.mock('@/hooks/useSettings', () => ({
  useMySettings: () => ({ data: { data_shared: false, active_personal_deck_id: null } }),
  useSharedUsers: () => ({
    data: [{ id: 'user-2', display_name: 'Bob', email: 'bob@example.com' }],
  }),
  useAvailableSharers: () => ({
    data: [
      { id: 'user-2', display_name: 'Bob', email: 'bob@example.com', opted_in: true },
      { id: 'user-3', display_name: null, email: 'carol@example.com', opted_in: false },
    ],
  }),
  useUpdateMySettings: () => ({ mutateAsync: updateSettingsMutateAsync }),
  useCreateReceiveOptIn: () => ({ mutateAsync: createReceiveOptInMutateAsync }),
  useDeleteReceiveOptIn: () => ({ mutateAsync: deleteReceiveOptInMutateAsync }),
}))

vi.mock('@/hooks/useViewingOwner', () => ({
  useViewingOwner: vi.fn(() => null),
}))

vi.mock('@/api/viewingOwner', () => ({
  setViewingOwner: (owner: unknown) => setViewingOwnerMock(owner),
}))

describe('SharingControls', () => {
  it('renders the sharing UI', () => {
    render(<SharingControls />)
    expect(screen.getByText('Share my data')).toBeInTheDocument()
  })
})

describe('SharingControlsContent', () => {
  it('lists "My account" and every shared user in the viewing selector', async () => {
    const user = userEvent.setup()
    render(<SharingControlsContent />)

    await user.click(screen.getByRole('combobox'))

    expect(
      screen.getByRole('option', { name: 'My account (alice@example.com)' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'View: Bob' })).toBeInTheDocument()
  })

  it('toggles data_shared when the checkbox is checked', async () => {
    const user = userEvent.setup()
    render(<SharingControlsContent />)

    await user.click(screen.getByRole('checkbox', { name: 'Share my data' }))

    expect(updateSettingsMutateAsync).toHaveBeenCalledWith({ data_shared: true })
  })

  it('shows the read-only badge when viewing a shared user', async () => {
    const { useViewingOwner } = await import('@/hooks/useViewingOwner')
    vi.mocked(useViewingOwner).mockReturnValue({ id: 'user-2', label: 'Bob' })

    render(<SharingControlsContent />)

    expect(screen.getByText('Viewing: Bob · read only')).toBeInTheDocument()
  })

  it('lists every available sharer with their current opt-in state', () => {
    render(<SharingControlsContent />)

    expect(screen.getByText('Receive shared data from:')).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Bob' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'carol@example.com' })).not.toBeChecked()
  })

  it('opts in to receive from a sharer when its checkbox is checked', async () => {
    const user = userEvent.setup()
    render(<SharingControlsContent />)

    await user.click(screen.getByRole('checkbox', { name: 'carol@example.com' }))

    expect(createReceiveOptInMutateAsync).toHaveBeenCalledWith('user-3')
  })

  it('opts out of receiving from a sharer when its checkbox is unchecked', async () => {
    const user = userEvent.setup()
    render(<SharingControlsContent />)

    await user.click(screen.getByRole('checkbox', { name: 'Bob' }))

    expect(deleteReceiveOptInMutateAsync).toHaveBeenCalledWith('user-2')
  })
})
