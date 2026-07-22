import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ActiveDeckContext, useActiveDeck } from './active-deck-context'

describe('useActiveDeck', () => {
  it('throws when used outside an ActiveDeckContext.Provider', () => {
    expect(() => renderHook(() => useActiveDeck())).toThrow(
      'useActiveDeck must be used within AppShell',
    )
  })

  it('returns the provided value inside a Provider', () => {
    const { result } = renderHook(() => useActiveDeck(), {
      wrapper: ({ children }) => (
        <ActiveDeckContext.Provider value={{ activeDeckId: 'deck-1', canEdit: false }}>
          {children}
        </ActiveDeckContext.Provider>
      ),
    })
    expect(result.current).toEqual({ activeDeckId: 'deck-1', canEdit: false })
  })
})
