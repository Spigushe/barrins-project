/**
 * Petit store pub-sub générique, compatible useSyncExternalStore.
 * Utilisé pour l'état de session et l'état "vue partagée" — lus en dehors
 * de React (dans le client HTTP) et suivis en réactivité depuis React.
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
