import { Card, CardTitle } from '@/components/ui/card'
import { Eyebrow } from '@/components/ui/eyebrow'

// No methodology write-up exists yet -- the archive prototype's own
// "Read the methodology" button had no destination either. This is a
// real page (not a dead link), with placeholder copy until there's an
// actual methodology to document.
export function MethodologyPage() {
  return (
    <div className="flex max-w-[720px] flex-col gap-4">
      <Eyebrow>Duel Commander · Methodology</Eyebrow>
      <CardTitle>How Tolaria News reads the metagame.</CardTitle>
      <Card>
        <p className="text-[15px] leading-relaxed text-muted-foreground">
          Tolaria News aggregates scraped Duel Commander tournament results — decklists,
          standings, and brackets — from public sources. A full write-up of the scraping,
          parsing, and aggregation methodology is coming soon.
        </p>
      </Card>
    </div>
  )
}
