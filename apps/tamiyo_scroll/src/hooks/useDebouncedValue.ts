import { useEffect, useState } from 'react'

/** Delays reflecting `value` until it's stopped changing for `delayMs` —
 * used to avoid firing a network request on every keystroke. */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timeout = setTimeout(() => {
      setDebounced(value)
    }, delayMs)
    return () => {
      clearTimeout(timeout)
    }
  }, [value, delayMs])

  return debounced
}
