import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SharingControls, SharingControlsContent } from './SharingControls'

const updateSettingsMutateAsync = vi.fn()
const setViewingOwnerMock = vi.fn()

vi.mock('@/hooks/useAuth', () => ({
  useCurrentUser: () => ({ data: { email: 'alice@example.com' } }),
}))

vi.mock('@/hooks/useSettings', () => ({
  useMySettings: () => ({ data: { data_shared: false, active_personal_deck_id: null } }),
  useSharedUsers: () => ({
    data: [{ id: 'user-2', display_name: 'Bob', email: 'bob@example.com' }],
  }),
  useUpdateMySettings: () => ({ mutateAsync: updateSettingsMutateAsync }),
}))

vi.mock('@/hooks/useViewingOwner', () => ({
  useViewingOwner: vi.fn(() => null),
}))

vi.mock('@/api/viewingOwner', () => ({
  setViewingOwner: (owner: unknown) => setViewingOwnerMock(owner),
}))

describe('SharingControls (SHARING_ENABLED gate)', () => {
  it('renders nothing — disabled for v1.0.0', () => {
    const { container } = render(<SharingControls />)
    expect(container).toBeEmptyDOMElement()
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
})
