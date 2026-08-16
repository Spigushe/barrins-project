import { Button } from '@/components/ui/button'
import type { TrendWindowMode } from '@/schemas/tolariaNews'

const MODE_OPTIONS: { value: TrendWindowMode; label: string }[] = [
  { value: 'rolling_30d', label: 'Rolling 30 days' },
  { value: 'banlist_period', label: 'Banlist period' },
  { value: 'all_time', label: 'All time' },
]

const inputClass =
  'h-9 rounded-(--radius-input) border border-border bg-input px-2 text-sm text-foreground'

/** Window-mode select for the commander-trend chips, plus (only in
 * `banlist_period` mode) a stepper into earlier periods. Deliberately
 * separate from `karnTablets/WindowModeSelect.tsx` -- that component's
 * `WindowMode` type is scoped to the `VITE_FEATURE_KARN_TABLETS` flag's
 * own (not-yet-shipped) feature, and shouldn't gate this unrelated,
 * always-on commander aggregation. */
export function TrendWindowControls({
  mode,
  onModeChange,
  periodOffset,
  onPeriodOffsetChange,
}: {
  mode: TrendWindowMode
  onModeChange: (mode: TrendWindowMode) => void
  periodOffset: number
  onPeriodOffsetChange: (offset: number) => void
}) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
        Window
        <select
          className={inputClass}
          value={mode}
          onChange={(e) => {
            onModeChange(e.target.value as TrendWindowMode)
            onPeriodOffsetChange(0)
          }}
        >
          {MODE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      {mode === 'banlist_period' && (
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              onPeriodOffsetChange(periodOffset + 1)
            }}
          >
            ← Earlier period
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={periodOffset === 0}
            onClick={() => {
              onPeriodOffsetChange(Math.max(0, periodOffset - 1))
            }}
          >
            Later period →
          </Button>
        </div>
      )}
    </div>
  )
}
