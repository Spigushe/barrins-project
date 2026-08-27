import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { WindowStepper } from './WindowStepper'
import type { Window } from '@/schemas/karnTablets'

function banlist(label: string): Window {
  return { kind: 'banlist_period', label, date_from: '2026-01-27', date_to: '2026-03-30' }
}

describe('WindowStepper', () => {
  it('shows the current window as a date range and both steppers enabled', () => {
    render(
      <WindowStepper
        window={banlist('banlist_period:mid')}
        previousWindow={banlist('banlist_period:old')}
        nextWindow={banlist('banlist_period:new')}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('2026-01-27 → 2026-03-30')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '← Previous period' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Next period →' })).toBeEnabled()
  })

  it('selects the previous / next window label on click', async () => {
    const onSelect = vi.fn()
    const user = userEvent.setup()
    render(
      <WindowStepper
        window={banlist('banlist_period:mid')}
        previousWindow={banlist('banlist_period:old')}
        nextWindow={banlist('banlist_period:new')}
        onSelect={onSelect}
      />,
    )
    await user.click(screen.getByRole('button', { name: '← Previous period' }))
    expect(onSelect).toHaveBeenCalledWith('banlist_period:old')

    await user.click(screen.getByRole('button', { name: 'Next period →' }))
    expect(onSelect).toHaveBeenCalledWith('banlist_period:new')
  })

  it('disables a stepper when that neighbour is null', () => {
    render(
      <WindowStepper
        window={banlist('banlist_period:latest')}
        previousWindow={banlist('banlist_period:old')}
        nextWindow={null}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: 'Next period →' })).toBeDisabled()
  })
})
