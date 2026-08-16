import { useParams, Link } from 'react-router-dom'
import { useDeck } from '@/hooks/useDecks'
import { CardNameCell } from '@/components/card-name-cell'
import { ManaPips } from '@/components/mana-pips'
import { Card, CardTitle, CardDescription } from '@/components/ui/card'
import { Eyebrow } from '@/components/ui/eyebrow'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import { Skeleton } from '@/components/ui/skeleton'
import type { CommanderRef, DeckCardCategory, DeckCardOut } from '@/schemas/tolariaNews'

/** Section header labels for the mainboard's type-grouped card list (e.g. "Creatures (14)" — the count is appended by the component, not here). */
const DECK_CARD_CATEGORY_LABELS: Record<DeckCardCategory, string> = {
  planeswalker: 'Planeswalkers',
  battle: 'Battles',
  creature: 'Creatures',
  instant: 'Instants',
  sorcery: 'Sorceries',
  artifact: 'Artifacts',
  enchantment: 'Enchantments',
  land: 'Lands',
  other: 'Other',
}

function CardInfoCell({
  card,
}: {
  card: Pick<DeckCardOut, 'name' | 'text' | 'keywords'>
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label={`${card.name} info`}
        >
          ⓘ
        </Button>
      </PopoverTrigger>
      <PopoverContent className="p-3">
        {card.keywords.length > 0 && (
          <div className="my-2 flex flex-wrap gap-1">
            {card.keywords.map((keyword) => (
              <Badge key={keyword} variant="accent">
                {keyword}
              </Badge>
            ))}
          </div>
        )}
        <p className="text-sm whitespace-pre-line">{card.text ?? 'No oracle text.'}</p>
      </PopoverContent>
    </Popover>
  )
}

export function DeckDetailPage() {
  const { id = '' } = useParams<{ id: string }>()
  const { data, isLoading, isError } = useDeck(id)

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-6 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <Card className="border-destructive/40 text-destructive">
        Failed to load this deck.
      </Card>
    )
  }

  const deck = data.data

  return (
    <div className="flex flex-col gap-4">
      <div>
        <Link
          to={`/tournaments/${deck.tournament_id}`}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Back to tournament
        </Link>
        <Eyebrow className="mt-2">Decklist</Eyebrow>
        <CardTitle className="mt-2">{deck.player}</CardTitle>
        <CardDescription>
          {deck.date}
          {deck.result ? ` — ${deck.result}` : ''}
        </CardDescription>
      </div>

      {deck.commanders.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {deck.commanders.map((commander) => (
            <Badge key={commander.name} variant="accent">
              {commander.name}
            </Badge>
          ))}
        </div>
      )}

      {deck.notes && <Card>{deck.notes}</Card>}

      {deck.commanders.length > 0 && (
        <Card className="p-0">
          <p className="px-4 pt-4 text-[11.5px] font-semibold uppercase tracking-[0.04em] text-muted-foreground">
            Commander ({deck.commanders.length})
          </p>
          <Table className="table-fixed">
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">Qty</TableHead>
                <TableHead className="w-64">Name</TableHead>
                <TableHead className="w-16">Color pips</TableHead>
                <TableHead className="w-16">Popover</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {deck.commanders.map((commander: CommanderRef) => (
                <TableRow key={commander.name}>
                  <TableCell>1</TableCell>
                  <TableCell>
                    <CardNameCell card={commander} />
                  </TableCell>
                  <TableCell>
                    <ManaPips manaCost={commander.mana_cost} />
                  </TableCell>
                  <TableCell>
                    <CardInfoCell card={commander} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {deck.mainboard.map((group) => (
        <Card key={group.category} className="p-0">
          <p className="px-4 pt-4 text-[11.5px] font-semibold uppercase tracking-[0.04em] text-muted-foreground">
            {DECK_CARD_CATEGORY_LABELS[group.category]} ({group.count})
          </p>
          <Table className="table-fixed">
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">Qty</TableHead>
                <TableHead className="w-64">Name</TableHead>
                <TableHead className="w-16">Color pips</TableHead>
                <TableHead className="w-16">Popover</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {group.cards.map((card, index) => (
                <TableRow key={`${card.name}-${String(index)}`}>
                  <TableCell>{card.qty}</TableCell>
                  <TableCell>
                    <CardNameCell card={card} />
                  </TableCell>
                  <TableCell>
                    <ManaPips manaCost={card.mana_cost} />
                  </TableCell>
                  <TableCell>
                    <CardInfoCell card={card} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      ))}
    </div>
  )
}
