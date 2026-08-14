import { useParams, Link } from 'react-router-dom'
import {
  useTournament,
  useTournamentDecks,
  useTournamentStandings,
  useTournamentBracket,
} from '@/hooks/useTournaments'
import { Card, CardTitle, CardDescription } from '@/components/ui/card'
import { Eyebrow } from '@/components/ui/eyebrow'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
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

function DecksTab({ tournamentId }: { tournamentId: string }) {
  const { data, isLoading } = useTournamentDecks(tournamentId)

  if (isLoading) return <Skeleton className="h-40 w-full" />

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Player</TableHead>
          <TableHead>Result</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data?.data.map((deck) => (
          <TableRow key={deck.id}>
            <TableCell>
              <Link
                to={`/decks/${deck.id}`}
                className="font-semibold text-foreground hover:text-accent"
              >
                {deck.player}
              </Link>
            </TableCell>
            <TableCell>{deck.result ?? '—'}</TableCell>
          </TableRow>
        ))}
        {data?.data.length === 0 && (
          <TableRow>
            <TableCell colSpan={2} className="text-center text-muted-foreground">
              No decks recorded for this tournament.
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  )
}

function StandingsTab({ tournamentId }: { tournamentId: string }) {
  const { data, isLoading } = useTournamentStandings(tournamentId)

  if (isLoading) return <Skeleton className="h-40 w-full" />

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Rank</TableHead>
          <TableHead>Player</TableHead>
          <TableHead>Points</TableHead>
          <TableHead>W-L-D</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data?.data.map((standing) => (
          <TableRow key={`${String(standing.rank)}-${standing.player}`}>
            <TableCell>{standing.rank}</TableCell>
            <TableCell>{standing.player}</TableCell>
            <TableCell>{standing.points}</TableCell>
            <TableCell>
              {standing.wins}-{standing.losses}-{standing.draws}
            </TableCell>
          </TableRow>
        ))}
        {data?.data.length === 0 && (
          <TableRow>
            <TableCell colSpan={4} className="text-center text-muted-foreground">
              No standings recorded for this tournament.
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  )
}

function BracketTab({ tournamentId }: { tournamentId: string }) {
  const { data, isLoading } = useTournamentBracket(tournamentId)

  if (isLoading) return <Skeleton className="h-40 w-full" />

  if (!data || data.data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No elimination bracket for this tournament (Swiss-only event).
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {data.data.map((round) => (
        <div key={round.round_name}>
          <h3 className="mb-2 text-sm font-semibold text-foreground">
            {round.round_name}
          </h3>
          <ul className="flex flex-col gap-1">
            {round.matches.map((match, index) => (
              <li key={index} className="text-sm text-muted-foreground">
                {match.player_1} vs {match.player_2} — {match.result}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}

export function TournamentDetailPage() {
  const { id = '' } = useParams<{ id: string }>()
  const { data, isLoading, isError } = useTournament(id)

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-6 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <Card className="border-destructive/40 text-destructive">
        Failed to load this tournament.
      </Card>
    )
  }

  const tournament = data.data

  return (
    <div className="flex flex-col gap-4">
      <div>
        <Link
          to="/tournaments"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Back to tournaments
        </Link>
        <Eyebrow className="mt-2">{tournament.format}</Eyebrow>
        <CardTitle className="mt-2">{tournament.name}</CardTitle>
        <CardDescription>
          {tournament.date} — {tournament.format} — {tournament.players} players
        </CardDescription>
        <div className="mt-2 flex gap-2">
          <Badge variant="accent">{tournament.source}</Badge>
          <Badge>{tournament.deck_count} decks</Badge>
          <Badge>{tournament.standing_count} standings</Badge>
        </div>
      </div>

      <Tabs defaultValue="decks">
        <TabsList>
          <TabsTrigger value="decks">Decks</TabsTrigger>
          <TabsTrigger value="standings">Standings</TabsTrigger>
          <TabsTrigger value="bracket">Bracket</TabsTrigger>
        </TabsList>
        <TabsContent value="decks" className="pt-4">
          <DecksTab tournamentId={id} />
        </TabsContent>
        <TabsContent value="standings" className="pt-4">
          <StandingsTab tournamentId={id} />
        </TabsContent>
        <TabsContent value="bracket" className="pt-4">
          <BracketTab tournamentId={id} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
