import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { API_BASE_URL } from '@/api/client'
import type { StapleRow, StaplesResponse } from '@/schemas/tolariaNews'

function StapleTile({ row }: { row: StapleRow }) {
  const detail = `${row.name} — ${row.deck_count.toString()} decks (${row.percentage.toString()}%)`

  return (
    <div className="flex flex-col gap-1">
      {row.scryfall_id ? (
        <img
          src={`${API_BASE_URL}/api/v1/cards/${row.scryfall_id}/image`}
          alt={row.name}
          title={detail}
          className="w-full rounded-(--radius-input)"
        />
      ) : (
        <div
          title={detail}
          className="flex aspect-[5/7] items-center justify-center rounded-(--radius-input) border border-border bg-input p-2 text-center text-xs text-muted-foreground"
        >
          {row.name}
        </div>
      )}
      <span className="text-center text-xs text-muted-foreground">
        {row.percentage}% of decks
      </span>
    </div>
  )
}

/** Metagame-wide card frequency, pooled across every qualifying
 * tournament in the caller's window -- not scoped to a single
 * tournament (see `app.services.tolaria_news.decks.list_staples`'s
 * docstring for the tournament-pooling rule), unless `data.commander` is
 * set, in which case it's scoped to decks piloting that commander.
 * Shared by `TournamentListPage` (metagame-wide) and `DecklistsPage`
 * (commander-scoped) rather than duplicated between them.
 *
 * Rendered as a grid of card images (up to 6 per row) rather than a
 * table -- each tile shows its play-rate percentage below the image;
 * name/deck-count are still available via the tile's `title`/`alt`
 * text on hover, just not shown as visible columns. */
export function StaplesSection({
  data,
  isLoading,
  isError,
}: {
  data: StaplesResponse | undefined
  isLoading: boolean
  isError: boolean
}) {
  if (isLoading) return <Skeleton className="h-40 w-full" />

  if (isError) {
    return (
      <Card className="border-destructive/40 text-destructive">
        Failed to load staples.
      </Card>
    )
  }

  if (!data) return null

  if (data.rows.length === 0) {
    return (
      <Card className="text-center text-muted-foreground">
        No card is played in at least {data.min_percentage}% of decks for this window.
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
      {data.rows.map((row) => (
        <StapleTile key={row.name} row={row} />
      ))}
    </div>
  )
}
