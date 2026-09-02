import { describe, expect, it, vi } from 'vitest'
import { createMemoryTokenStore } from './tokenStore'

describe('createMemoryTokenStore', () => {
  it('starts empty', () => {
    const store = createMemoryTokenStore()
    expect(store.getAccess()).toBeNull()
    expect(store.getRefresh()).toBeNull()
  })

  it('holds a pair after set() and drops it on clear()', () => {
    const store = createMemoryTokenStore()
    store.set({ access_token: 'a1', refresh_token: 'r1' })
    expect(store.getAccess()).toBe('a1')
    expect(store.getRefresh()).toBe('r1')

    store.clear()
    expect(store.getAccess()).toBeNull()
    expect(store.getRefresh()).toBeNull()
  })

  it('notifies subscribers on set and clear, and stops after unsubscribe', () => {
    const store = createMemoryTokenStore()
    const listener = vi.fn()
    const unsubscribe = store.subscribe(listener)

    store.set({ access_token: 'a', refresh_token: 'r' })
    store.clear()
    expect(listener).toHaveBeenCalledTimes(2)

    unsubscribe()
    store.set({ access_token: 'a2', refresh_token: 'r2' })
    expect(listener).toHaveBeenCalledTimes(2)
  })
})
