/** Shared by both footer rows (`AppShell`'s static branding row and
 * `BottomRail`'s telemetry row) so their three columns line up exactly --
 * a fixed 3-column grid, not `justify-between`, since that sizes each
 * row's columns independently off its own content width and the two rows
 * never have matching text lengths. In its own module (not exported from
 * either component file) so the two don't import from each other. */
export const FOOTER_ROW_CLASS =
  'mx-auto grid max-w-[1440px] grid-cols-1 gap-1 px-6 py-3 font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted-foreground sm:grid-cols-3 sm:items-baseline md:px-14'
