import { Card, CardTitle } from '@/components/ui/card'
import { Eyebrow } from '@/components/ui/eyebrow'

// The archive prototype's own "Read the methodology" button had no
// destination either. This is a real page (not a dead link) -- the
// scraping/parsing pipeline itself still doesn't have a full write-up,
// but the rules that affect how to *read* the trend chips and staples
// tables (pooling, thresholds, the default date floor) are documented
// below, since those are exactly what a reader needs to interpret those
// two sections correctly (see the "methodology" link on the tournaments
// page).
export function MethodologyPage() {
  return (
    <div className="flex max-w-[720px] flex-col gap-4">
      <Eyebrow>Duel Commander · Methodology</Eyebrow>
      <CardTitle>How Tolaria News reads the metagame.</CardTitle>
      <Card className="flex flex-col gap-4">
        <p className="text-[15px] leading-relaxed text-muted-foreground">
          Tolaria News aggregates scraped Duel Commander tournament results — decklists,
          standings, and brackets — from public sources (MTGO and MTGTop8). A full
          write-up of the scraping and parsing pipeline is coming soon; the rules below
          cover how the trend chips and staples tables on the tournaments page are
          computed.
        </p>

        <div className="flex flex-col gap-1">
          <h2 className="text-sm font-semibold text-foreground">Default date range</h2>
          <p className="text-[15px] leading-relaxed text-muted-foreground">
            Every view excludes data before 2015-11-01 (before the first MTGO Duel
            Commander events) by default — old enough to skew trends without being
            representative of the current metagame. Picking a custom date range overrides
            this floor, including a range that starts earlier.
          </p>
        </div>

        <div className="flex flex-col gap-1">
          <h2 className="text-sm font-semibold text-foreground">Tournament pooling</h2>
          <p className="text-[15px] leading-relaxed text-muted-foreground">
            Staples are pooled across every qualifying tournament in the selected window,
            not one tournament&apos;s own decks. A window under 65 days pools every
            tournament in range; 65 days or wider, only "major" tournaments qualify —
            MTGTop8 events with more than 80 players, or any MTGO-sourced event (including
            leagues) — so a long or all-time window&apos;s pool doesn&apos;t fill up with
            every small local event ever recorded. MTGTop8 listings that mirror an MTGO
            event are excluded, since the underlying decks are already counted once via
            the native MTGO-sourced tournament.
          </p>
        </div>

        <div className="flex flex-col gap-1">
          <h2 className="text-sm font-semibold text-foreground">Staples threshold</h2>
          <p className="text-[15px] leading-relaxed text-muted-foreground">
            A card counts as a "staple" once it appears in at least 65% of the pooled
            decks. If that leaves no rows for a window, the threshold falls back to 45%
            once before giving up. Sideboard cards (the commander, for Duel Commander) and
            lands are excluded from staples entirely.
          </p>
        </div>
      </Card>
    </div>
  )
}
