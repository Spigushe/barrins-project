import { useParams, Link } from 'react-router-dom'
import { useDeck } from '@/hooks/useDecks'
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
import { Skeleton } from '@/components/ui/skeleton'

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

      <Card className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Qty</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>CMC</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {deck.mainboard.map((card, index) => (
              <TableRow key={`${card.name}-${String(index)}`}>
                <TableCell>{card.qty}</TableCell>
                <TableCell>{card.name}</TableCell>
                <TableCell>{card.type_line ?? '—'}</TableCell>
                <TableCell>{card.cmc ?? '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
