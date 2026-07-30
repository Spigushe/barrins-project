import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AccountSettingsDialog } from './AccountSettingsDialog'

const updateProfileMutateAsync = vi.fn().mockResolvedValue(undefined)
const updateSettingsMutateAsync = vi.fn().mockResolvedValue(undefined)

beforeEach(() => {
  updateProfileMutateAsync.mockClear()
  updateSettingsMutateAsync.mockClear()
})

vi.mock('@/hooks/useAuth', () => ({
  useCurrentUser: () => ({
    data: { email: 'alice@example.com', display_name: 'Alice' },
  }),
  useUpdateProfile: () => ({ mutateAsync: updateProfileMutateAsync, isPending: false }),
}))

vi.mock('@/hooks/useSettings', () => ({
  useMySettings: () => ({ data: { data_shared: true, receive_shared_data: false } }),
  useUpdateMySettings: () => ({ mutateAsync: updateSettingsMutateAsync, isPending: false }),
}))

describe('AccountSettingsDialog', () => {
  it('renders nothing when closed', () => {
    render(<AccountSettingsDialog open={false} onOpenChange={vi.fn()} />)
    expect(screen.queryByText('Account settings')).not.toBeInTheDocument()
  })

  it('explains that sharing is matched by deck name', () => {
    render(<AccountSettingsDialog open onOpenChange={vi.fn()} />)
    expect(screen.getByText(/matched by deck name/)).toBeInTheDocument()
  })

  it('pre-fills display name and toggle state from current data', () => {
    render(<AccountSettingsDialog open onOpenChange={vi.fn()} />)

    expect(screen.getByLabelText('Display name')).toHaveValue('Alice')
    expect(screen.getByRole('switch', { name: 'Share my data' })).toHaveAttribute(
      'aria-checked',
      'true',
    )
    expect(screen.getByRole('switch', { name: 'Receive shared data' })).toHaveAttribute(
      'aria-checked',
      'false',
    )
  })

  it('does not render the team section (deferred until S2 is implemented)', () => {
    render(<AccountSettingsDialog open onOpenChange={vi.fn()} />)
    expect(screen.queryByText(/team/i)).not.toBeInTheDocument()
  })

  it('renders a separator between the display name and sharing sections', () => {
    render(<AccountSettingsDialog open onOpenChange={vi.fn()} />)
    expect(screen.getByRole('separator')).toBeInTheDocument()
  })

  it('disables and unchecks receive when share is turned off', async () => {
    const user = userEvent.setup()
    render(<AccountSettingsDialog open onOpenChange={vi.fn()} />)

    await user.click(screen.getByRole('switch', { name: 'Receive shared data' }))
    expect(screen.getByRole('switch', { name: 'Receive shared data' })).toHaveAttribute(
      'aria-checked',
      'true',
    )

    await user.click(screen.getByRole('switch', { name: 'Share my data' }))

    const receiveSwitch = screen.getByRole('switch', { name: 'Receive shared data' })
    expect(receiveSwitch).toHaveAttribute('aria-checked', 'false')
    expect(receiveSwitch).toBeDisabled()
  })

  it('does not toggle receive while disabled', async () => {
    const user = userEvent.setup()
    render(<AccountSettingsDialog open onOpenChange={vi.fn()} />)

    await user.click(screen.getByRole('switch', { name: 'Share my data' }))
    const receiveSwitch = screen.getByRole('switch', { name: 'Receive shared data' })
    await user.click(receiveSwitch)

    expect(receiveSwitch).toHaveAttribute('aria-checked', 'false')
  })

  it('saves the display name and both toggles together', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    render(<AccountSettingsDialog open onOpenChange={onOpenChange} />)

    await user.clear(screen.getByLabelText('Display name'))
    await user.type(screen.getByLabelText('Display name'), 'Jace')
    await user.click(screen.getByRole('switch', { name: 'Receive shared data' }))
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(updateProfileMutateAsync).toHaveBeenCalledWith({ display_name: 'Jace' })
    expect(updateSettingsMutateAsync).toHaveBeenCalledWith({
      data_shared: true,
      receive_shared_data: true,
    })
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('clears the display name to null when left empty', async () => {
    const user = userEvent.setup()
    render(<AccountSettingsDialog open onOpenChange={vi.fn()} />)

    await user.clear(screen.getByLabelText('Display name'))
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(updateProfileMutateAsync).toHaveBeenCalledWith({ display_name: null })
  })

  it('closes without saving on Cancel', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    render(<AccountSettingsDialog open onOpenChange={onOpenChange} />)

    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(onOpenChange).toHaveBeenCalledWith(false)
    expect(updateProfileMutateAsync).not.toHaveBeenCalled()
    expect(updateSettingsMutateAsync).not.toHaveBeenCalled()
  })
})
