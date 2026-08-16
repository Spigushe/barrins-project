import type { TrendWindowMode } from '@/schemas/tolariaNews'

export type WindowPreset =
  'current_season' | 'previous_season' | 'life_20' | 'all_time' | 'custom'

const PRESET_OPTIONS: { value: WindowPreset; label: string }[] = [
  { value: 'current_season', label: 'Current banlist season' },
  { value: 'previous_season', label: 'Previous banlist season' },
  { value: 'life_20', label: '20-life decks (2016–present)' },
  { value: 'all_time', label: 'All time' },
  { value: 'custom', label: 'Custom range' },
]

/** Duel Commander's starting life total changed from 30 to 20 on this
 * date (announced 2016-09-22) -- a strategic shift large enough that the
 * "20-life decks" preset excludes everything before it entirely, per the
 * format's own rules history. */
export const LIFE_20_RULE_CHANGE_DATE = '2016-11-11'

export interface ResolvedWindowParams {
  mode: TrendWindowMode
  periodOffset?: number
  dateFrom?: string
  dateTo?: string
}

/** Maps a preset (plus the custom-range inputs, only relevant for
 * `custom`) to the actual `/decks/commanders/trending` query params --
 * the single source of truth both the commander chips and (via the
 * resolved `window` the trending query returns) the tournament table
 * below it are driven from. */
export function resolveWindowParams(
  preset: WindowPreset,
  customDateFrom: string,
  customDateTo: string,
): ResolvedWindowParams {
  switch (preset) {
    case 'current_season':
      return { mode: 'banlist_period', periodOffset: 0 }
    case 'previous_season':
      return { mode: 'banlist_period', periodOffset: 1 }
    case 'life_20':
      return { mode: 'custom', dateFrom: LIFE_20_RULE_CHANGE_DATE }
    case 'all_time':
      return { mode: 'all_time' }
    case 'custom':
      return {
        mode: 'custom',
        dateFrom: customDateFrom || undefined,
        dateTo: customDateTo || undefined,
      }
  }
}

const inputClass =
  'h-9 rounded-(--radius-input) border border-border bg-input px-2 text-sm text-foreground'

/** Tournament-page window/date filter -- one control driving both the
 * commander-trend chips and the tournament table's own listing below it
 * (merged per the user's request; previously two independent controls:
 * the chips' window-mode select and the table's raw From/To inputs). */
export function TournamentWindowFilter({
  preset,
  onPresetChange,
  customDateFrom,
  customDateTo,
  onCustomDateFromChange,
  onCustomDateToChange,
}: {
  preset: WindowPreset
  onPresetChange: (preset: WindowPreset) => void
  customDateFrom: string
  customDateTo: string
  onCustomDateFromChange: (value: string) => void
  onCustomDateToChange: (value: string) => void
}) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
        Window
        <select
          className={inputClass}
          value={preset}
          onChange={(e) => {
            onPresetChange(e.target.value as WindowPreset)
          }}
        >
          {PRESET_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      {preset === 'custom' && (
        <>
          <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
            From
            <input
              type="date"
              className={inputClass}
              value={customDateFrom}
              onChange={(e) => {
                onCustomDateFromChange(e.target.value)
              }}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
            To
            <input
              type="date"
              className={inputClass}
              value={customDateTo}
              onChange={(e) => {
                onCustomDateToChange(e.target.value)
              }}
            />
          </label>
        </>
      )}
    </div>
  )
}
