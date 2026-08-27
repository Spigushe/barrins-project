/**
 * Categorical chart palette -- 10 series, built for this app's Midnight
 * background (`--color-background: #0b1220`). Plain hex constants, not
 * Tailwind `@theme` CSS variables: a `--chart-1`..`--chart-10` (and,
 * renamed, `--color-chart-1`..`--color-chart-10`) numeric scale placed in
 * `@theme` was silently pruned by Tailwind v4's theme compiler down to
 * just its first and last entries in the generated `:root` block -- 8 of
 * 10 series resolved `var(--chart-N)` to nothing and rendered with
 * `stroke: none`, invisible despite real, non-null data. Nothing consumes
 * these as Tailwind utility classes (no `bg-chart-3` anywhere) -- they're
 * only ever read via this array, so a plain TS constant is the one source
 * of truth. Ordered so the first 3-4 are the most distinct -- used in
 * order, one per series.
 */
export const CHART_PALETTE = [
  '#7be0d6',
  '#c7a455',
  '#8fa8ff',
  '#e08a6a',
  '#a8d46f',
  '#d986c4',
  '#5fb4d8',
  '#e5c978',
  '#9c8fe0',
  '#6fcfa8',
]

export function seriesStroke(index: number): string {
  return CHART_PALETTE[index % CHART_PALETTE.length]
}
