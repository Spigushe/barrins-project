import { Button } from '@/components/ui/button'
import type { Window } from '@/schemas/karnTablets'

function windowLabel(w: Window): string {
  // Banlist periods read as a date range; a rolling window as its end date.
  return w.kind === 'banlist_period' ? `${w.date_from} → ${w.date_to}` : w.date_to
}

/** Prev/next navigation across the windows of one kind. `previousWindow` /
 * `nextWindow` come straight from the response (`null` at either end);
 * `onSelect` is called with the target window's `label`, or `undefined`
 * to jump back to the most recent window.
 *
 * PROVISIONAL — see src/schemas/karnTablets.ts. */
export function WindowStepper({
  window: current,
  previousWindow,
  nextWindow,
  onSelect,
}: {
  window: Window
  previousWindow: Window | null
  nextWindow: Window | null
  onSelect: (windowLabel: string | undefined) => void
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <Button
        variant="outline"
        size="sm"
        disabled={!previousWindow}
        onClick={() => {
          if (previousWindow) onSelect(previousWindow.label)
        }}
      >
        ← Previous period
      </Button>
      <span className="text-center font-mono text-xs text-muted-foreground">
        {windowLabel(current)}
      </span>
      <Button
        variant="outline"
        size="sm"
        disabled={!nextWindow}
        onClick={() => {
          onSelect(nextWindow ? nextWindow.label : undefined)
        }}
      >
        Next period →
      </Button>
    </div>
  )
}
