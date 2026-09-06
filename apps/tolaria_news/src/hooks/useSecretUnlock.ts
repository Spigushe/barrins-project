import { useCallback, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

/** Unlisted route for the "Tolaria West" mana-source calculator easter egg. */
export const SECRET_PATH = '/west'

/** Typed anywhere outside a form field, this opens the hidden page — a third
 * way in alongside the Konami code and the seven-click "decoded." word in the
 * landing headline. */
const SECRET_WORD = 'manabase'

const KONAMI_SEQUENCE = [
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

/** Clicks this far apart (ms) or more restart the wordmark tap counter. */
const TAP_RESET_MS = 1500

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName
  return (
    tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable
  )
}

/**
 * Two keyboard paths to the hidden page: the Konami code, or typing the
 * secret word. Both are ignored while an input, textarea, select, or
 * contenteditable is focused, so they never interfere with the calculator's
 * own form. Mount once (in `AppShell`).
 */
export function useSecretUnlock() {
  const navigate = useNavigate()

  useEffect(() => {
    let konamiIndex = 0
    let typed = ''

    function handleKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented || isTypingTarget(event.target)) return

      konamiIndex = event.key === KONAMI_SEQUENCE[konamiIndex] ? konamiIndex + 1 : 0
      if (konamiIndex === KONAMI_SEQUENCE.length) {
        konamiIndex = 0
        navigate(SECRET_PATH)
        return
      }

      if (event.key.length === 1) {
        typed = (typed + event.key.toLowerCase()).slice(-SECRET_WORD.length)
        if (typed === SECRET_WORD) {
          typed = ''
          navigate(SECRET_PATH)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [navigate])
}

/**
 * Click handler for a repeated-tap trigger (the "decoded." word in the landing
 * headline): fire on the `threshold`-th click within {@link TAP_RESET_MS} of
 * the previous one, calling `preventDefault()` so the element's own click
 * action is suppressed only on the unlock.
 */
export function useTapUnlock(threshold = 7) {
  const navigate = useNavigate()
  const taps = useRef(0)
  const lastTapAt = useRef(0)

  return useCallback(
    (event: { preventDefault: () => void }) => {
      const now = Date.now()
      taps.current = now - lastTapAt.current < TAP_RESET_MS ? taps.current + 1 : 1
      lastTapAt.current = now

      if (taps.current >= threshold) {
        taps.current = 0
        event.preventDefault()
        navigate(SECRET_PATH)
      }
    },
    [navigate, threshold],
  )
}
