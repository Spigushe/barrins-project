import { cn } from '@/lib/utils'

const SIZE_BUCKETS = [
  { value: 'leagues', label: 'Leagues' },
  { value: 'small', label: '≤16' },
  { value: 'medium', label: '17-63' },
  { value: 'large', label: '64-99' },
  { value: 'major', label: '100+' },
] as const

/**
 * Clickable tournament-size chips -- additive, like
 * `ColorIdentityPicker`'s WUBRG pips (click toggles membership in
 * `selected`, multiple can be active at once), just with the five
 * player-count buckets instead of colors.
 */
export function TournamentSizeFilter({
  selected,
  onToggle,
}: {
  selected: string[]
  onToggle: (bucket: string) => void
}) {
  return (
    <span className="flex flex-wrap gap-1">
      {SIZE_BUCKETS.map((bucket) => {
        const isSelected = selected.includes(bucket.value)
        return (
          <button
            key={bucket.value}
            type="button"
            aria-pressed={isSelected}
            aria-label={`Tournament size: ${bucket.label}`}
            onClick={() => {
              onToggle(bucket.value)
            }}
            className={cn(
              'flex h-6 items-center justify-center rounded-full px-2 text-[11px] font-semibold transition-colors',
              isSelected
                ? 'bg-accent text-accent-foreground'
                : 'bg-input text-foreground hover:bg-border',
            )}
          >
            {bucket.label}
          </button>
        )
      })}
    </span>
  )
}
