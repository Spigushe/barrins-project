import { cn } from '@/lib/utils'

const WUBRG = ['W', 'U', 'B', 'R', 'G'] as const

/**
 * Clickable WUBRG color-identity filter pips -- same visual language as
 * `ManaPips` (`components/mana-pips.tsx`, size-4 rounded badge) but
 * interactive: click toggles membership in `selected`, multiple pips can
 * be active at once.
 */
export function ColorIdentityPicker({
  selected,
  onToggle,
}: {
  selected: string[]
  onToggle: (color: string) => void
}) {
  return (
    <span className="flex gap-1">
      {WUBRG.map((color) => {
        const isSelected = selected.includes(color)
        return (
          <button
            key={color}
            type="button"
            aria-pressed={isSelected}
            aria-label={`Color identity: ${color}`}
            onClick={() => {
              onToggle(color)
            }}
            className={cn(
              'flex size-6 items-center justify-center rounded-full text-[11px] font-semibold transition-colors',
              isSelected
                ? 'bg-accent text-accent-foreground'
                : 'bg-input text-foreground hover:bg-border',
            )}
          >
            {color}
          </button>
        )
      })}
    </span>
  )
}
