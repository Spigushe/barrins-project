import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AccountSettingsDialog } from './AccountSettingsDialog'

const updateSettingsMutateAsync = vi.fn().mockResolvedValue(undefined)

beforeEach(() => {
  updateSettingsMutateAsync.mockClear()
})

// Identity-owned account management (display name / email / delete) is the
// shared Goblin Guide `<AccountScreen>` — stubbed here so this test stays
// on the Tamiyo-only sections below it. `useCurrentUser` is consumed by the
// nested `AccountSettingsTeamSection` for the owner check.
vi.mock('@barrins/goblin-guide', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@barrins/goblin-guide')>()),
  AccountScreen: () => <div>Barrin&rsquo;s account (managed screen)</div>,
  useCurrentUser: () => ({
    data: { id: 'user-alice', email: 'alice@example.com', display_name: 'Alice' },
  }),
}))

vi.mock('@/hooks/useSettings', () => ({
  useMySettings: () => ({
    data: {
      data_shared: true,
      receive_shared_data: false,
      metagame_roster_scope: 'game',
      auto_archive_stale_sessions: false,
      auto_archive_decklist_version_gap: 3,
      show_decklist_version_diff: true,
      validate_removed_card_in_decklist: true,
      validate_added_card_exists: false,
      show_decklist_change_log: false,
    },
  }),
  useUpdateMySettings: () => ({
    mutateAsync: updateSettingsMutateAsync,
    isPending: false,
  }),
}))

function renderDialog(props: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return render(
    <MemoryRouter>
      <AccountSettingsDialog {...props} />
    </MemoryRouter>,
  )
}

describe('AccountSettingsDialog', () => {
  it('renders nothing when closed', () => {
    renderDialog({ open: false, onOpenChange: vi.fn() })
    expect(screen.queryByText('Account settings')).not.toBeInTheDocument()
  })

  it('embeds the shared Barrin’s account screen', () => {
    renderDialog({ open: true, onOpenChange: vi.fn() })
    expect(screen.getByText(/managed screen/)).toBeInTheDocument()
  })

  it('explains that sharing is matched by deck name', () => {
    renderDialog({ open: true, onOpenChange: vi.fn() })
    expect(screen.getByText(/matched by deck name/)).toBeInTheDocument()
  })

  it('pre-fills the sharing toggle state from current data', () => {
    renderDialog({ open: true, onOpenChange: vi.fn() })

    expect(screen.getByRole('switch', { name: 'Share my data' })).toHaveAttribute(
      'aria-checked',
      'true',
    )
    expect(screen.getByRole('switch', { name: 'Receive shared data' })).toHaveAttribute(
      'aria-checked',
      'false',
    )
  })

  it('renders separators between the display name, sharing, roster scope, auto-archive, version diff, card-test validation/change-log and display sections', () => {
    renderDialog({ open: true, onOpenChange: vi.fn() })
    // Barrin's account (managed screen) / Share my data / Roster scope (F10) /
    // Auto-archive (S14) / Version diff (S15) / Card-test validation + change
    // log (S16) / Display (S12).
    expect(screen.getAllByRole('separator')).toHaveLength(6)
  })

  it('disables and unchecks receive when share is turned off', async () => {
    const user = userEvent.setup()
    renderDialog({ open: true, onOpenChange: vi.fn() })

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
    renderDialog({ open: true, onOpenChange: vi.fn() })

    await user.click(screen.getByRole('switch', { name: 'Share my data' }))
    const receiveSwitch = screen.getByRole('switch', { name: 'Receive shared data' })
    await user.click(receiveSwitch)

    expect(receiveSwitch).toHaveAttribute('aria-checked', 'false')
  })

  it('saves both sharing toggles together and closes', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    renderDialog({ open: true, onOpenChange })

    await user.click(screen.getByRole('switch', { name: 'Receive shared data' }))
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(updateSettingsMutateAsync).toHaveBeenCalledWith({
      data_shared: true,
      receive_shared_data: true,
      metagame_roster_scope: 'game',
      auto_archive_stale_sessions: false,
      auto_archive_decklist_version_gap: 3,
      show_decklist_version_diff: true,
      validate_removed_card_in_decklist: true,
      validate_added_card_exists: false,
      show_decklist_change_log: false,
    })
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('saves the auto-archive toggle and threshold', async () => {
    const user = userEvent.setup()
    renderDialog({ open: true, onOpenChange: vi.fn() })

    await user.click(screen.getByRole('switch', { name: 'Auto-archive stale sessions' }))
    const gapInput = screen.getByLabelText('Version gap')
    await user.clear(gapInput)
    await user.type(gapInput, '5')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(updateSettingsMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({
        auto_archive_stale_sessions: true,
        auto_archive_decklist_version_gap: 5,
      }),
    )
  })

  it('pre-fills the version diff toggle from current data', () => {
    renderDialog({ open: true, onOpenChange: vi.fn() })
    expect(screen.getByRole('switch', { name: 'Decklist version diff' })).toHaveAttribute(
      'aria-checked',
      'true',
    )
  })

  it('saves the version diff toggle', async () => {
    const user = userEvent.setup()
    renderDialog({ open: true, onOpenChange: vi.fn() })

    await user.click(screen.getByRole('switch', { name: 'Decklist version diff' }))
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(updateSettingsMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ show_decklist_version_diff: false }),
    )
  })

  it('pre-fills the card-test validation and change-log toggles from current data', () => {
    renderDialog({ open: true, onOpenChange: vi.fn() })
    expect(
      screen.getByRole('switch', { name: 'Validate removed card is in decklist' }),
    ).toHaveAttribute('aria-checked', 'true')
    expect(
      screen.getByRole('switch', { name: 'Validate added card exists' }),
    ).toHaveAttribute('aria-checked', 'false')
    expect(
      screen.getByRole('switch', { name: 'Show decklist change log' }),
    ).toHaveAttribute('aria-checked', 'false')
  })

  it('saves the card-test validation and change-log toggles', async () => {
    const user = userEvent.setup()
    renderDialog({ open: true, onOpenChange: vi.fn() })

    await user.click(
      screen.getByRole('switch', { name: 'Validate removed card is in decklist' }),
    )
    await user.click(screen.getByRole('switch', { name: 'Validate added card exists' }))
    await user.click(screen.getByRole('switch', { name: 'Show decklist change log' }))
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(updateSettingsMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({
        validate_removed_card_in_decklist: false,
        validate_added_card_exists: true,
        show_decklist_change_log: true,
      }),
    )
  })

  it('pre-fills the roster scope toggle from current data', () => {
    renderDialog({ open: true, onOpenChange: vi.fn() })
    expect(
      screen.getByRole('switch', { name: 'Store roster decks per game' }),
    ).toHaveAttribute('aria-checked', 'true')
  })

  it('saves the roster scope toggle', async () => {
    const user = userEvent.setup()
    renderDialog({ open: true, onOpenChange: vi.fn() })

    await user.click(screen.getByRole('switch', { name: 'Store roster decks per game' }))
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(updateSettingsMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ metagame_roster_scope: 'personal_deck' }),
    )
  })

  it('closes without saving on Cancel', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    renderDialog({ open: true, onOpenChange })

    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(onOpenChange).toHaveBeenCalledWith(false)
    expect(updateSettingsMutateAsync).not.toHaveBeenCalled()
  })
})

// S12 items 8-11: four `localStorage`-backed display preferences,
// independent from the Save/Cancel form above.
describe('AccountSettingsDialog — Display section', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('defaults row tint on, and the other three off', () => {
    renderDialog({ open: true, onOpenChange: vi.fn() })

    expect(screen.getByRole('switch', { name: 'Winrate row tint' })).toHaveAttribute(
      'aria-checked',
      'true',
    )
    expect(
      screen.getByRole('switch', { name: '"2W / 0L" result format' }),
    ).toHaveAttribute('aria-checked', 'false')
    expect(
      screen.getByRole('switch', { name: 'Colored archetype cell' }),
    ).toHaveAttribute('aria-checked', 'false')
    expect(screen.getByRole('switch', { name: 'Tier background color' })).toHaveAttribute(
      'aria-checked',
      'false',
    )
  })

  it('persists a toggle to localStorage immediately, not on Save', async () => {
    const user = userEvent.setup()
    renderDialog({ open: true, onOpenChange: vi.fn() })

    await user.click(screen.getByRole('switch', { name: '"2W / 0L" result format' }))

    expect(localStorage.getItem('ts-matchup-result-format-2w0l')).toBe('true')
    expect(updateSettingsMutateAsync).not.toHaveBeenCalled()
  })

  it('reads a previously stored preference over its default', () => {
    localStorage.setItem('ts-matchup-row-tint-enabled', 'false')
    renderDialog({ open: true, onOpenChange: vi.fn() })

    expect(screen.getByRole('switch', { name: 'Winrate row tint' })).toHaveAttribute(
      'aria-checked',
      'false',
    )
  })
})
