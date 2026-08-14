import { NodeGraph } from './NodeGraph'
import { karnTabletsEnabled } from '@/lib/featureFlags'

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
      className={`pointer-events-none absolute flex flex-col gap-1 ${align === 'start' ? 'items-start' : 'items-end'} ${className}`}
    >
      <span className="font-mono text-[9.5px] tracking-[0.1em] text-muted-foreground uppercase">
        <span className="text-accent">—</span> {eyebrow}
      </span>
      <span className="font-serif text-lg tracking-[-0.01em] text-foreground italic">
        {main}
      </span>
    </div>
  )
}

/**
 * The landing page's right-hand showpiece: corner brackets + the decorative
 * meta-graph + telemetry callouts. Per the design handoff, the graph itself
 * is always decorative/procedural (no backend ever required for it — see
 * NodeGraph). The three floating callouts, though, read as *specific*
 * archetype-clustering metrics (cluster share, sample size, winrate delta)
 * — those are Karn Tablets data (T4 iteration 2 / T6, not shipped), so they
 * only render behind `VITE_FEATURE_KARN_TABLETS` rather than showing
 * invented numbers.
 */
export function VizPanel() {
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[620px]">
      <Brackets />

      <div className="absolute inset-[18px]">
        <NodeGraph accent={ACCENT} accentSoft={ACCENT_SOFT} />
      </div>

      {karnTabletsEnabled && (
        <>
          <Callout
            className="top-[14%] right-[4%]"
            eyebrow="cluster · tymna / thrasios"
            main="share 11.4%"
          />
          <Callout
            className="bottom-[18%] left-[2%]"
            eyebrow="archetype · midrange-value"
            main="n = 286"
            align="start"
          />
          <Callout
            className="right-[8%] bottom-[6%]"
            eyebrow="format · duel commander"
            main="winrate ↑ 2.4%"
          />
        </>
      )}

      <div className="absolute top-0 left-0 font-mono text-[10.5px] tracking-[0.08em] text-muted-foreground uppercase">
        <span className="text-accent">◆</span> meta-graph · dc.001
      </div>
      <div className="absolute top-0 right-0 font-mono text-[10.5px] tracking-[0.08em] text-muted-foreground uppercase">
        procedural · 80 nodes
      </div>
    </div>
  )
}
