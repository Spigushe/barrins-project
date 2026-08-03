import { type FormEvent, useState } from 'react'
import { useActiveDeck } from '@/contexts/active-deck-context'
import { usePersonalDecks } from '@/hooks/usePersonalDecks'
import {
  useArchiveSession,
  useCreateSession,
  useDownloadSessionReport,
  useSessionComparison,
  useSessions,
  useUpdateSession,
} from '@/hooks/useSessions'
import type { MatchupRow, Session, SessionType } from '@/schemas/tamiyoScroll'
import {
  formatDateTime,
  formatPercent,
  SESSION_TYPE_BADGE_VARIANT,
  SESSION_TYPE_LABELS,
  sessionReportFilename,
} from '@/lib/mtg-format'
import { cn } from '@/lib/utils'
import { FilePdfIcon } from '@/components/icons'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ExpectedMetagameSection } from '../metagame/MetaDecksSections'

function sessionPeriodLabel(session: Pick<Session, 'created_at' | 'ended_at'>): string {
  return session.ended_at === null
    ? `Since ${formatDateTime(session.created_at)}`
    : `${formatDateTime(session.created_at)} → ${formatDateTime(session.ended_at)}`
}

/** `+X.X pts` / `-X.X pts` / `—` — shared by the summary's delta tile and
 * the per-matchup comparison table below. */
function deltaOf(a: number | null, b: number | null): number | null {
  return a !== null && b !== null ? a - b : null
}

function formatDeltaPts(delta: number | null): string {
  if (delta === null) return '—'
  const rounded = Math.round(delta * 10) / 10
  return `${rounded >= 0 ? '+' : ''}${rounded.toString()} pts`
}

function deltaColorClass(delta: number | null): string {
  if (delta === null) return 'text-muted-foreground'
  return delta >= 0 ? 'text-success' : 'text-destructive'
}

function StatTile({
  label,
  value,
  valueClassName,
}: {
  label: string
  value: string
  valueClassName?: string
}) {
  return (
    <div className="rounded-(--radius-card) bg-input p-4">
      <div className="text-[11.5px] font-semibold tracking-[0.04em] text-subtle-foreground uppercase">
        {label}
      </div>
      <div className={cn('font-mono text-xl font-extrabold', valueClassName)}>{value}</div>
    </div>
  )
}

/**
 * Per-opponent-deck winrate comparison (session vs. the deck's history
 * before it) — every deck faced during the session, each row's baseline
 * looked up by `opponent_deck_id` from the baseline matchup summary
 * (absent baseline = first time facing that deck, columns show "—").
 * Reuses the comparison endpoint's already-computed matchup rows — no
 * new calculation.
 */
function MatchupComparisonTable({
  sessionRows,
  baselineRows,
}: {
  sessionRows: MatchupRow[]
  baselineRows: MatchupRow[]
}) {
  if (sessionRows.length === 0) return null

  const baselineByOpponent = new Map(
    baselineRows.map((row) => [row.opponent_deck_id, row]),
  )

  return (
    <div className="mt-5">
      <div className="mb-2 text-sm font-semibold text-foreground">Matchup comparison</div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Deck</TableHead>
            <TableHead>W/R global</TableHead>
            <TableHead>W/R session</TableHead>
            <TableHead>Delta</TableHead>
            <TableHead>Delta OTP</TableHead>
            <TableHead>Delta OTD</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sessionRows.map((row) => {
            const baseline = baselineByOpponent.get(row.opponent_deck_id)
            const delta = deltaOf(row.winrate_global, baseline?.winrate_global ?? null)
            const deltaOtp = deltaOf(row.winrate_otp, baseline?.winrate_otp ?? null)
            const deltaOtd = deltaOf(row.winrate_otd, baseline?.winrate_otd ?? null)
            return (
              <TableRow key={row.opponent_deck_id}>
                <TableCell className="font-semibold text-foreground">
                  {row.opponent_deck_name}
                </TableCell>
                <TableCell>{formatPercent(baseline?.winrate_global ?? null)}</TableCell>
                <TableCell>{formatPercent(row.winrate_global)}</TableCell>
                <TableCell className={deltaColorClass(delta)}>
                  {formatDeltaPts(delta)}
                </TableCell>
                <TableCell className={deltaColorClass(deltaOtp)}>
                  {formatDeltaPts(deltaOtp)}
                </TableCell>
                <TableCell className={deltaColorClass(deltaOtd)}>
                  {formatDeltaPts(deltaOtd)}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}

/**
 * "Résumé de la session" — reads the backend's comparison endpoint
 * directly (winrate/W-L already computed server-side, per Constitution
 * §4.1/§4.2, no client-side recalculation).
 */
function SessionSummarySection({
  sessionId,
  deckNameById,
}: {
  sessionId: string | null
  deckNameById: Map<string, string>
}) {
  const { data: comparison } = useSessionComparison(sessionId)
  const downloadReport = useDownloadSessionReport()

  if (sessionId === null || !comparison) {
    return (
      <Card>
        <CardTitle>Session summary</CardTitle>
        <p className="mt-2 text-sm text-muted-foreground">
          Select a session above to show its summary.
        </p>
      </Card>
    )
  }

  const { session } = comparison
  const isActive = session.ended_at === null
  const sessionWinPct = comparison.session_matchup_summary.average_winrate
  const baselineWinPct = comparison.baseline_matchup_summary.average_winrate
  const delta = deltaOf(sessionWinPct, baselineWinPct)

  return (
    <Card>
      <div className="flex flex-wrap items-center gap-2">
        <CardTitle>{session.name}</CardTitle>
        <Badge variant={SESSION_TYPE_BADGE_VARIANT[session.type]}>
          {SESSION_TYPE_LABELS[session.type]}
        </Badge>
        <span
          className={cn(
            'text-[11.5px] font-bold',
            isActive ? 'text-accent' : 'text-muted-foreground',
          )}
        >
          {isActive ? 'Ongoing' : 'Closed'}
        </span>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="ml-auto"
          disabled={downloadReport.isPending}
          onClick={() => {
            downloadReport.mutate({
              sessionId: session.id,
              filename: sessionReportFilename(session),
            })
          }}
        >
          {downloadReport.isPending ? 'Generating…' : 'Download report (PDF)'}
        </Button>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        {sessionPeriodLabel(session)} · {deckNameById.get(session.personal_deck_id) ?? '—'}
      </p>
      <CardDescription className="mt-3">
        Comparison against the deck's history before the session started.
      </CardDescription>

      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Games" value={String(comparison.session_match_count)} />
        <StatTile
          label="Session winrate"
          value={formatPercent(sessionWinPct)}
          valueClassName="text-accent"
        />
        <StatTile
          label="Winrate before the session"
          value={formatPercent(baselineWinPct)}
        />
        <StatTile
          label="Delta"
          value={formatDeltaPts(delta)}
          valueClassName={deltaColorClass(delta)}
        />
      </div>
      <p className="mt-3 text-[12.5px] text-muted-foreground">
        W/L — session {comparison.session_wins}W / {comparison.session_losses}L · before
        the session {comparison.baseline_wins}W / {comparison.baseline_losses}L
      </p>

      {session.type === 'tournament' && (
        <div className="mt-5">
          <ExpectedMetagameSection />
        </div>
      )}

      <MatchupComparisonTable
        sessionRows={comparison.session_matchup_summary.rows}
        baselineRows={comparison.baseline_matchup_summary.rows}
      />
    </Card>
  )
}

/**
 * The Sessions tab (S9): a single sessions list (ongoing + closed
 * together, status shown per row — merged 2026-07-31 per the user, was
 * two separate "manage"/"review" blocks) and the summary of whichever
 * row is selected.
 */
export function SessionsOverviewSection() {
  const { canEdit, activeDeckId } = useActiveDeck()
  const { data: personalDecks } = usePersonalDecks()
  const { data: sessions } = useSessions(activeDeckId)
  const createSession = useCreateSession()
  const updateSession = useUpdateSession()
  const archiveSession = useArchiveSession()
  const downloadReport = useDownloadSessionReport()

  const [newName, setNewName] = useState('')
  const [newType, setNewType] = useState<SessionType>('training')
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)

  const deckNameById = new Map((personalDecks ?? []).map((deck) => [deck.id, deck.name]))
  // Non-archived sessions only — the archive action is a soft-delete that
  // drops a session out of this list (still queryable via its own
  // comparison route, just not surfaced in this tab).
  const nonArchivedSessions = (sessions ?? []).filter((s) => s.archived_at === null)

  if (activeDeckId === null) return null

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    if (!newName.trim() || activeDeckId === null) return
    const created = await createSession.mutateAsync({
      name: newName.trim(),
      type: newType,
      personal_deck_id: activeDeckId,
    })
    setNewName('')
    setNewType('training')
    setSelectedSessionId(created.id)
  }

  function handleClose(sessionId: string) {
    void updateSession.mutateAsync({ sessionId, payload: { close: true } })
  }

  function handleReopen(sessionId: string) {
    void updateSession.mutateAsync({ sessionId, payload: { reopen: true } })
  }

  function handleArchive(sessionId: string) {
    void archiveSession.mutateAsync(sessionId)
    if (selectedSessionId === sessionId) setSelectedSessionId(null)
  }

  function handleDownloadReport(session: Session) {
    downloadReport.mutate({
      sessionId: session.id,
      filename: sessionReportFilename(session),
    })
  }

  return (
    <>
      <Card>
        <CardTitle>Sessions</CardTitle>
        <CardDescription className="mt-1">
          Group this deck's games by tournament or training. Once created, a session is
          offered in the "New game" form on the BO3 Tracking tab. Select a row to show
          its summary below.
        </CardDescription>

        {canEdit && (
          <form
            className="mt-4 flex flex-wrap items-end gap-2 rounded-(--radius-input) border border-border-dashed p-3"
            onSubmit={(event) => {
              void handleCreate(event)
            }}
          >
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="new-session-name">Name</Label>
              <Input
                id="new-session-name"
                placeholder="e.g. RC Toronto 2026"
                value={newName}
                onChange={(event) => {
                  setNewName(event.target.value)
                }}
                className="w-48"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Type</Label>
              <Select
                value={newType}
                onValueChange={(value) => {
                  setNewType(value as SessionType)
                }}
              >
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(SESSION_TYPE_LABELS) as SessionType[]).map((type) => (
                    <SelectItem key={type} value={type}>
                      {SESSION_TYPE_LABELS[type]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="submit" disabled={createSession.isPending}>
              Create
            </Button>
          </form>
        )}

        <Table className="mt-3">
          <TableHeader>
            <TableRow>
              <TableHead>Session</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Period</TableHead>
              {canEdit && <TableHead className="w-52" />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {nonArchivedSessions.map((session) => {
              const ongoing = session.ended_at === null
              return (
                <TableRow
                  key={session.id}
                  className={cn(
                    'cursor-pointer',
                    selectedSessionId === session.id && 'bg-input-inline',
                  )}
                  onClick={() => {
                    setSelectedSessionId(session.id)
                  }}
                >
                  <TableCell>{session.name}</TableCell>
                  <TableCell>
                    <Badge variant={SESSION_TYPE_BADGE_VARIANT[session.type]}>
                      {SESSION_TYPE_LABELS[session.type]}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={ongoing ? 'accent' : 'default'}>
                      {ongoing ? 'Ongoing' : 'Closed'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {sessionPeriodLabel(session)}
                  </TableCell>
                  {canEdit && (
                    <TableCell
                      className="flex gap-2"
                      onClick={(event) => {
                        event.stopPropagation()
                      }}
                    >
                      {ongoing ? (
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            handleClose(session.id)
                          }}
                        >
                          Close
                        </Button>
                      ) : (
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            handleReopen(session.id)
                          }}
                        >
                          Reopen
                        </Button>
                      )}
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        title="Download report (PDF)"
                        aria-label="Download report (PDF)"
                        disabled={downloadReport.isPending}
                        onClick={() => {
                          handleDownloadReport(session)
                        }}
                      >
                        <FilePdfIcon className="size-4" />
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          handleArchive(session.id)
                        }}
                      >
                        ✕
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              )
            })}
            {nonArchivedSessions.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={canEdit ? 5 : 4}
                  className="text-center text-muted-foreground"
                >
                  No session yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>

      <SessionSummarySection
        sessionId={selectedSessionId}
        deckNameById={deckNameById}
      />
    </>
  )
}
