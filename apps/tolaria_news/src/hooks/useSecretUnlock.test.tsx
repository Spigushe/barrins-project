import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useSecretUnlock, useTapUnlock } from './useSecretUnlock'

const KONAMI = [
  'ArrowUp',
  'ArrowUp',
  'ArrowDown',
  'ArrowDown',
  'ArrowLeft',
  'ArrowRight',
  'ArrowLeft',
  'ArrowRight',
  'b',
  'a',
]

function KeyboardHarness() {
  useSecretUnlock()
  return (
    <Routes>
      <Route path="/" element={<input aria-label="pilot" />} />
      <Route path="/west" element={<div>Tolaria West</div>} />
    </Routes>
  )
}

function renderKeyboardHarness() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <KeyboardHarness />
    </MemoryRouter>,
  )
}

function TapHarness() {
  const onClick = useTapUnlock()
  return (
    <Routes>
      <Route
        path="/"
        element={
          <em onClick={onClick} data-testid="word">
            decoded.
          </em>
        }
      />
      <Route path="/west" element={<div>Tolaria West</div>} />
    </Routes>
  )
}

function renderTapHarness() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <TapHarness />
    </MemoryRouter>,
  )
}

afterEach(() => {
  vi.useRealTimers()
})

describe('useSecretUnlock', () => {
  it('navigates to /west on the Konami code', async () => {
    renderKeyboardHarness()
    for (const key of KONAMI) fireEvent.keyDown(document, { key })
    expect(await screen.findByText('Tolaria West')).toBeInTheDocument()
  })

  it('navigates to /west when the secret word "manabase" is typed', async () => {
    renderKeyboardHarness()
    for (const ch of 'manabase') fireEvent.keyDown(document, { key: ch })
    expect(await screen.findByText('Tolaria West')).toBeInTheDocument()
  })

  it('ignores the sequence while a text input is focused', () => {
    renderKeyboardHarness()
    const input = screen.getByLabelText('pilot')
    input.focus()
    for (const key of KONAMI) fireEvent.keyDown(input, { key })
    expect(screen.queryByText('Tolaria West')).not.toBeInTheDocument()
  })
})

describe('useTapUnlock', () => {
  it('navigates on the seventh consecutive click', async () => {
    renderTapHarness()
    const word = screen.getByTestId('word')
    for (let i = 0; i < 7; i++) fireEvent.click(word)
    expect(await screen.findByText('Tolaria West')).toBeInTheDocument()
  })

  it('does nothing before the seventh click', () => {
    renderTapHarness()
    const word = screen.getByTestId('word')
    for (let i = 0; i < 6; i++) fireEvent.click(word)
    expect(screen.queryByText('Tolaria West')).not.toBeInTheDocument()
  })

  it('restarts the count when clicks are spaced too far apart', () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    renderTapHarness()
    const word = screen.getByTestId('word')
    for (let i = 0; i < 6; i++) fireEvent.click(word)
    vi.advanceTimersByTime(2000)
    fireEvent.click(word)
    expect(screen.queryByText('Tolaria West')).not.toBeInTheDocument()
  })
})
