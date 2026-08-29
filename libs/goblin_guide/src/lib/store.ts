/**
 * Small generic pub-sub store, compatible with `useSyncExternalStore`.
 *
 * Mirrors the helper of the same name in `apps/tamiyo_scroll` — the token
 * store (and any host-supplied replacement) is read outside React by the
 * fetch client and subscribed to reactively from React.
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
      return () => {
        listeners.delete(listener)
      }
    },
  }
}
