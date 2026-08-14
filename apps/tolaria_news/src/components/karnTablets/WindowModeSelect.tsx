import type { WindowMode } from '@/schemas/karnTablets'

const OPTIONS: { value: WindowMode; label: string }[] = [
  { value: 'rolling_30d', label: 'Rolling 30 days' },
  { value: 'banlist_period', label: 'Banlist period' },
]

export function WindowModeSelect({
  value,
  onChange,
}: {
  value: WindowMode
  onChange: (mode: WindowMode) => void
}) {
  return (
    <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
      Window
      <select
        className="h-9 rounded-(--radius-input) border border-border bg-input px-2 text-sm text-foreground"
        value={value}
        onChange={(e) => {
          onChange(e.target.value as WindowMode)
        }}
      >
        {OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  )
}
