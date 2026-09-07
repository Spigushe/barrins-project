import { NodeGraph } from './NodeGraph'
import { karnTabletsEnabled } from '@/lib/featureFlags'
import type { Archetype } from '@/schemas/karnTablets'

// Literal hex, not CSS vars — passed into SVG `stop-color`/`stroke` attributes,
// which don't reliably resolve `var(--color-accent)` as a raw attribute value.
const ACCENT = '#7be0d6'
const ACCENT_SOFT = 'rgba(255,255,255,0.20)'

function Brackets() {
  const common = 'absolute size-3.5 border-foreground/40'
  return (
    <>
      <span className={`${common} top-0 left-0 border-t-[0.5px] border-l-[0.5px]`} />
      <span className={`${common} top-0 right-0 border-t-[0.5px] border-r-[0.5px]`} />
      <span className={`${common} bottom-0 left-0 border-b-[0.5px] border-l-[0.5px]`} />
      <span className={`${common} right-0 bottom-0 border-r-[0.5px] border-b-[0.5px]`} />
    </>
  )
}

function Callout({
  className,
  eyebrow,
  main,
  align = 'end',
}: {
  className: string
  eyebrow: string
  main: string
  align?: 'start' | 'end'
}) {
  return (
    <div
      className={`pointer-events-none absolute flex max-w-[46%] flex-col gap-1 ${align === 'start' ? 'items-start' : 'items-end'} ${className}`}
    >
      <span
        className={`font-mono text-[9.5px] tracking-[0.1em] text-muted-foreground uppercase ${align === 'start' ? 'text-left' : 'text-right'}`}
      >
        <span className="text-accent">—</span> {eyebrow}
      </span>
      <span className="font-serif text-lg tracking-[-0.01em] text-foreground italic">
        {main}
      </span>
    </div>
  )
}

/** The archetype's commander card name(s) for a callout label — a partner
 *  pair joins with " / ". Falls back to the archetype's display name when
 *  it has no commander (non-Duel-Commander data). */
function commanderLabel(archetype: Archetype): string {
  if (archetype.commanders.length === 0) return archetype.name
  return archetype.commanders.map((c) => c.name).join(' / ')
}

/**
 * The landing page's right-hand showpiece: corner brackets + the decorative
 * meta-graph + telemetry callouts. Per the design handoff, the graph mesh
 * itself is always decorative/procedural (no backend ever required for it
 * — see NodeGraph).
 *
 * The three floating callouts read as *specific* archetype-clustering
 * metrics and only render behind `VITE_FEATURE_KARN_TABLETS`:
 *  - top-left/right: the #1 archetype by deck share (`topArchetype`) and
 *    the fastest-rising archetype (`fastestRising`), both from
 *    `GET /bff/tolaria-news/metagame` (rolling 30-day window). The
 *    "fastest riser" ranking is backend-owned (`fastest_rising` on the
 *    response) — this component only renders what it is handed. Each
 *    hides itself when its datum is absent (no clustering run yet, or
 *    nothing rising).
 *  - bottom-left: `archetype · midrange-value / n = 286` is still static.
 *    Karn Tablets does not expose macro-archetype ("midrange", "control",
 *    …) definitions yet (constitution §45 future work), so there is no
 *    real number to show here; kept rather than invented.
 *
 * The "meta-graph" label's `seasonLabel` is real: the current banlist
 * season from `useTelemetry()`, threaded down from `LandingPage`. It is a
 * banlist-period label while the callouts describe a rolling 30-day
 * window — a deliberate mix (the season frames the page, the callouts
 * track the near term).
 */
export function VizPanel({
  seasonLabel,
  topArchetype,
  fastestRising,
}: {
  seasonLabel?: string
  topArchetype?: Archetype
  fastestRising?: Archetype
}) {
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[620px]">
      <Brackets />

      <div className="absolute inset-[18px]">
        <NodeGraph accent={ACCENT} accentSoft={ACCENT_SOFT} />
      </div>

      {karnTabletsEnabled && (
        <>
          {topArchetype && (
            <Callout
              className="top-[14%] right-[4%]"
              eyebrow={`cluster · ${commanderLabel(topArchetype)}`}
              main={`share ${(topArchetype.deck_share * 100).toFixed(1)}%`}
            />
          )}
          <Callout
            className="bottom-[18%] left-[2%]"
            eyebrow="archetype · midrange-value"
            main="n = 286"
            align="start"
          />
          {fastestRising && fastestRising.deck_share_delta !== null && (
            <Callout
              className="right-[8%] bottom-[6%]"
              eyebrow={`rising · ${commanderLabel(fastestRising)}`}
              main={`share ↑ ${(fastestRising.deck_share_delta * 100).toFixed(1)} pts`}
            />
          )}
        </>
      )}

      <div className="absolute top-0 left-0 font-mono text-[10.5px] tracking-[0.08em] text-muted-foreground uppercase">
        <span className="text-accent">◆</span> meta-graph
        {seasonLabel ? ` · ${seasonLabel}` : ''}
      </div>
      <div className="absolute top-0 right-0 font-mono text-[10.5px] tracking-[0.08em] text-muted-foreground uppercase">
        procedural · 80 nodes
      </div>
    </div>
  )
}
