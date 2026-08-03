import { useCallback, useEffect, useState } from 'react'

function readFlag(key: string, defaultValue: boolean): boolean {
  const stored = localStorage.getItem(key)
  if (stored === null) return defaultValue
  return stored === 'true'
}

/**
 * Small opt-in/opt-out display preference backed by `localStorage` (S12
 * items 8-11) — never round-tripped through the backend, unlike
 * `useMySettings`/`useUpdateMySettings`.
 *
 * Every component reading the same `key` stays in sync within the
 * current tab via a custom `window` event: the browser's own `storage`
 * event only fires in *other* tabs, but toggling a preference in
 * `AccountSettingsDialog`'s "Display" section must update tables
 * rendered underneath the still-open dialog (e.g.
 * `MatchupSummarySection`, `MetaDecksRosterSection`) immediately.
 */
export function useLocalStorageFlag(
  key: string,
  defaultValue: boolean,
): readonly [boolean, (next: boolean) => void] {
  const [value, setValue] = useState(() => readFlag(key, defaultValue))

  useEffect(() => {
    setValue(readFlag(key, defaultValue))
    const eventName = `ts-local-storage-flag:${key}`
    function handleChange() {
      setValue(readFlag(key, defaultValue))
    }
    window.addEventListener(eventName, handleChange)
    return () => {
      window.removeEventListener(eventName, handleChange)
    }
  }, [key, defaultValue])

  const setFlag = useCallback(
    (next: boolean) => {
      localStorage.setItem(key, String(next))
      window.dispatchEvent(new Event(`ts-local-storage-flag:${key}`))
    },
    [key],
  )

  return [value, setFlag] as const
}
