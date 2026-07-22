/**
 * Small generic pub-sub store, compatible with useSyncExternalStore.
 * Used for session state and "shared view" state — read outside of
 * React (in the HTTP client) and reactively subscribed to from React.
 */
export interface Store<T> {
  get: () => T
  set: (next: T) => void
  subscribe: (listener: () => void) => () => void
}

export function createStore<T>(initial: T): Store<T> {
  let state = initial
  const listeners = new Set<() => void>()

  return {
    get: () => state,
    set: (next: T) => {
      state = next
      for (const listener of listeners) listener()
    },
    subscribe: (listener: () => void) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
  }
}
