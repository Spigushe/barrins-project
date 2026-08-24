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
import type { Session, SessionPatch, SessionType } from '@/schemas/tamiyoScroll'
import type { MatchupRow } from '@/schemas/tamiyoScroll'
import {
  formatDateTime,
  formatPercent,
  SESSION_TYPE_LABELS,
  sessionReportFilename,
} from '@/lib/mtg-format'
import { cn } from '@/lib/utils'
import { FilePdfIcon } from '@/components/icons'
import { SessionTypeBadge } from '@/components/session/SessionTypeBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
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
import { Textarea } from '@/components/ui/textarea'
import { ExpectedMetagameSection } from '../metagame/MetaDecksSections'

const PAGE_SIZE = 10
type SortField = 'name' | 'type' | 'started_at' | 'status'
type SortDir = 'asc' | 'desc'

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
      <div className={cn('font-mono text-xl font-extrabold', valueClassName)}>
        {value}
      </div>
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
  const isActive = session.closed_at === null
  const sessionWinPct = comparison.session_matchup_summary.average_winrate
  const baselineWinPct = comparison.baseline_matchup_summary.average_winrate
  const delta = deltaOf(sessionWinPct, baselineWinPct)

  return (
    <Card>
      <div className="flex flex-wrap items-center gap-2">
        <CardTitle>{session.name}</CardTitle>
        <SessionTypeBadge session={session} />
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
        {session.started_at
          ? `Since ${formatDateTime(session.started_at)}`
          : 'No start date'}
        {session.location && ` · ${session.location}`} ·{' '}
        {deckNameById.get(session.personal_deck_id) ?? '—'}
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

interface SessionDraft {
  name: string
  location: string
  notes: string
  startedAt: string
  endedAt: string
  hue: number | null
}

function toDatetimeLocal(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${String(d.getFullYear())}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function draftFromSession(session: Session): SessionDraft {
  return {
    name: session.name,
    location: session.location ?? '',
    notes: session.notes ?? '',
    startedAt: toDatetimeLocal(session.started_at),
    endedAt: toDatetimeLocal(session.ended_at),
    hue: session.hue,
  }
}

function draftToPatch(draft: SessionDraft): SessionPatch {
  return {
    name: draft.name.trim(),
    location: draft.location.trim() === '' ? null : draft.location.trim(),
    notes: draft.notes.trim() === '' ? null : draft.notes.trim(),
    started_at: draft.startedAt === '' ? null : new Date(draft.startedAt).toISOString(),
    ended_at: draft.endedAt === '' ? null : new Date(draft.endedAt).toISOString(),
    hue: draft.hue,
  }
}

/**
 * Inline edit form for a session (S14 tasks 1/2/6 + location) — used both
 * in the main table and the archived-sessions dialog. Editable regardless
 * of the session's status (ongoing/closed/archived); nothing here gates
 * on `closed_at`/`archived_at`.
 */
function SessionEditFields({
  draft,
  onChange,
  idPrefix,
}: {
  draft: SessionDraft
  onChange: (draft: SessionDraft) => void
  idPrefix: string
}) {
  const swatchColor =
    draft.hue === null ? undefined : `hsl(${draft.hue.toString()} 70% 50%)`
  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor={`${idPrefix}-name`}>Name</Label>
          <Input
            id={`${idPrefix}-name`}
            value={draft.name}
            onChange={(event) => {
              onChange({ ...draft, name: event.target.value })
            }}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor={`${idPrefix}-location`}>Location</Label>
          <Input
            id={`${idPrefix}-location`}
            placeholder="e.g. Toronto, ON"
            value={draft.location}
            onChange={(event) => {
              onChange({ ...draft, location: event.target.value })
            }}
          />
        </div>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor={`${idPrefix}-started`}>Started at</Label>
          <Input
            id={`${idPrefix}-started`}
            type="datetime-local"
            value={draft.startedAt}
            onChange={(event) => {
              onChange({ ...draft, startedAt: event.target.value })
            }}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor={`${idPrefix}-ended`}>Ended at</Label>
          <Input
            id={`${idPrefix}-ended`}
            type="datetime-local"
            value={draft.endedAt}
            onChange={(event) => {
              onChange({ ...draft, endedAt: event.target.value })
            }}
          />
          <p className="text-[11px] text-muted-foreground">
            Informational only — independent of Close/Reopen below.
          </p>
        </div>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor={`${idPrefix}-notes`}>Notes</Label>
        <Textarea
          id={`${idPrefix}-notes`}
          value={draft.notes}
          onChange={(event) => {
            onChange({ ...draft, notes: event.target.value })
          }}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor={`${idPrefix}-hue`}>Color</Label>
        <div className="flex items-center gap-3">
          <input
            id={`${idPrefix}-hue`}
            type="range"
            min={0}
            max={359}
            value={draft.hue ?? 0}
            onChange={(event) => {
              onChange({ ...draft, hue: Number(event.target.value) })
            }}
            className="h-2 flex-1 cursor-pointer appearance-none rounded-full bg-input accent-current"
            style={{ color: swatchColor ?? 'var(--accent)' }}
          />
          <span
            aria-hidden
            className="size-6 shrink-0 rounded-full border border-border"
            style={{ backgroundColor: swatchColor ?? 'transparent' }}
          />
          {draft.hue !== null && (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => {
                onChange({ ...draft, hue: null })
              }}
            >
              Clear
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * The Sessions tab (S9): a single sessions list (ongoing + closed
 * together, status shown per row — merged 2026-07-31 per the user, was
 * two separate "manage"/"review" blocks) and the summary of whichever
 * row is selected. S14: sortable/paginated columns, inline edit
 * (name/location/notes/dates/hue), and an archived-sessions dialog.
 */
export function SessionsOverviewSection() {
  const { canEdit, activeDeckId } = useActiveDeck()
  const { data: personalDecks } = usePersonalDecks()
  const [sortBy, setSortBy] = useState<SortField | undefined>(undefined)
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [page, setPage] = useState(0)
  const { data: sessionsPage } = useSessions(activeDeckId, false, {
    sortBy,
    sortDir,
    limit: PAGE_SIZE + 1,
    offset: page * PAGE_SIZE,
  })
  const createSession = useCreateSession()
  const updateSession = useUpdateSession()
  const archiveSession = useArchiveSession()
  const downloadReport = useDownloadSessionReport()

  const [newName, setNewName] = useState('')
  const [newType, setNewType] = useState<SessionType>('training')
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [pendingArchive, setPendingArchive] = useState<Session | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<SessionDraft | null>(null)
  const [archivedOpen, setArchivedOpen] = useState(false)

  const deckNameById = new Map((personalDecks ?? []).map((deck) => [deck.id, deck.name]))
  const sessions = (sessionsPage ?? []).slice(0, PAGE_SIZE)
  const hasNextPage = (sessionsPage ?? []).length > PAGE_SIZE

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

  function startEdit(session: Session) {
    setEditingId(session.id)
    setEditDraft(draftFromSession(session))
  }

  function cancelEdit() {
    setEditingId(null)
    setEditDraft(null)
  }

  async function handleSaveEdit(sessionId: string) {
    if (!editDraft || !editDraft.name.trim()) return
    await updateSession.mutateAsync({ sessionId, payload: draftToPatch(editDraft) })
    cancelEdit()
  }

  function toggleSort(field: SortField) {
    setPage(0)
    if (sortBy === field) {
      setSortDir((dir) => (dir === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(field)
      setSortDir('asc')
    }
  }

  function sortIndicator(field: SortField) {
    if (sortBy !== field) return null
    return <span className="ml-1">{sortDir === 'asc' ? '▲' : '▼'}</span>
  }

  return (
    <>
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>Sessions</CardTitle>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => {
              setArchivedOpen(true)
            }}
          >
            See archived
          </Button>
        </div>
        <CardDescription className="mt-1">
          Group this deck's games by tournament or training. Once created, a session is
          offered in the "New game" form on the BO3 Tracking tab. Select a row to show its
          summary below.
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
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => {
                  toggleSort('name')
                }}
              >
                Session{sortIndicator('name')}
              </TableHead>
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => {
                  toggleSort('type')
                }}
              >
                Type{sortIndicator('type')}
              </TableHead>
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => {
                  toggleSort('status')
                }}
              >
                Status{sortIndicator('status')}
              </TableHead>
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => {
                  toggleSort('started_at')
                }}
              >
                Starting date{sortIndicator('started_at')}
              </TableHead>
              {canEdit && <TableHead className="w-64" />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {sessions.map((session) => {
              const ongoing = session.closed_at === null

              if (editingId === session.id && editDraft) {
                return (
                  <TableRow key={session.id}>
                    <TableCell colSpan={canEdit ? 5 : 4}>
                      <div className="rounded-(--radius-input) border border-border bg-input-inline p-4">
                        <SessionEditFields
                          draft={editDraft}
                          onChange={setEditDraft}
                          idPrefix={`session-edit-${session.id}`}
                        />
                        <div className="mt-4 flex gap-2">
                          <Button
                            type="button"
                            disabled={!editDraft.name.trim() || updateSession.isPending}
                            onClick={() => {
                              void handleSaveEdit(session.id)
                            }}
                          >
                            Save
                          </Button>
                          <Button type="button" variant="outline" onClick={cancelEdit}>
                            Cancel
                          </Button>
                        </div>
                      </div>
                    </TableCell>
                  </TableRow>
                )
              }

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
                    <SessionTypeBadge session={session} />
                  </TableCell>
                  <TableCell>
                    <Badge variant={ongoing ? 'accent' : 'default'}>
                      {ongoing ? 'Ongoing' : 'Closed'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {session.started_at ? formatDateTime(session.started_at) : '—'}
                  </TableCell>
                  {canEdit && (
                    <TableCell
                      className="flex flex-wrap gap-2"
                      onClick={(event) => {
                        event.stopPropagation()
                      }}
                    >
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          startEdit(session)
                        }}
                      >
                        Edit
                      </Button>
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
                          setPendingArchive(session)
                        }}
                      >
                        ✕
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              )
            })}
            {sessions.length === 0 && (
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

        <div className="mt-3 flex items-center justify-between">
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={page === 0}
            onClick={() => {
              setPage((p) => p - 1)
            }}
          >
            Prev
          </Button>
          <span className="text-xs text-muted-foreground">Page {page + 1}</span>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={!hasNextPage}
            onClick={() => {
              setPage((p) => p + 1)
            }}
          >
            Next
          </Button>
        </div>
      </Card>

      <SessionSummarySection sessionId={selectedSessionId} deckNameById={deckNameById} />

      <ConfirmDialog
        open={pendingArchive !== null}
        onOpenChange={(next) => {
          if (!next) setPendingArchive(null)
        }}
        title={pendingArchive ? `Archive "${pendingArchive.name}"?` : ''}
        description="It will disappear from this list. This can't be undone."
        confirmLabel="Archive"
        confirmDisabled={archiveSession.isPending}
        onConfirm={() => {
          if (!pendingArchive) return
          handleArchive(pendingArchive.id)
          setPendingArchive(null)
        }}
      />

      <Dialog open={archivedOpen} onOpenChange={setArchivedOpen}>
        {archivedOpen && (
          <DialogContent className="max-w-160">
            <DialogTitle>Archived sessions</DialogTitle>
            <ArchivedSessionsSection activeDeckId={activeDeckId} canEdit={canEdit} />
          </DialogContent>
        )}
      </Dialog>
    </>
  )
}

/** S14 item 8: archived-sessions search + restore tool, behind the "See
 * archived" button above. Edit is available here too (S14, "editable
 * regardless of status") via the same `SessionEditFields`. */
function ArchivedSessionsSection({
  activeDeckId,
  canEdit,
}: {
  activeDeckId: string | null
  canEdit: boolean
}) {
  const [search, setSearch] = useState('')
  const { data: allSessions } = useSessions(activeDeckId, true, { search })
  const updateSession = useUpdateSession()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<SessionDraft | null>(null)

  const archivedSessions = (allSessions ?? []).filter((s) => s.archived_at !== null)

  function startEdit(session: Session) {
    setEditingId(session.id)
    setEditDraft(draftFromSession(session))
  }

  function cancelEdit() {
    setEditingId(null)
    setEditDraft(null)
  }

  async function handleSaveEdit(sessionId: string) {
    if (!editDraft || !editDraft.name.trim()) return
    await updateSession.mutateAsync({ sessionId, payload: draftToPatch(editDraft) })
    cancelEdit()
  }

  function handleRestore(sessionId: string) {
    void updateSession.mutateAsync({ sessionId, payload: { restore: true } })
  }

  return (
    <div className="flex flex-col gap-3">
      <Input
        placeholder="Search by name…"
        value={search}
        onChange={(event) => {
          setSearch(event.target.value)
        }}
      />
      <div className="flex flex-col gap-2">
        {archivedSessions.map((session) => {
          if (editingId === session.id && editDraft) {
            return (
              <div
                key={session.id}
                className="rounded-(--radius-input) border border-border bg-input-inline p-4"
              >
                <SessionEditFields
                  draft={editDraft}
                  onChange={setEditDraft}
                  idPrefix={`archived-session-edit-${session.id}`}
                />
                <div className="mt-4 flex gap-2">
                  <Button
                    type="button"
                    disabled={!editDraft.name.trim() || updateSession.isPending}
                    onClick={() => {
                      void handleSaveEdit(session.id)
                    }}
                  >
                    Save
                  </Button>
                  <Button type="button" variant="outline" onClick={cancelEdit}>
                    Cancel
                  </Button>
                </div>
              </div>
            )
          }
          return (
            <div
              key={session.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-(--radius-input) border border-border bg-input-inline p-3"
            >
              <div className="flex items-center gap-2">
                <span className="font-semibold text-foreground">{session.name}</span>
                <SessionTypeBadge session={session} />
              </div>
              {canEdit && (
                <div className="flex gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      startEdit(session)
                    }}
                  >
                    Edit
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => {
                      handleRestore(session.id)
                    }}
                  >
                    Restore
                  </Button>
                </div>
              )}
            </div>
          )
        })}
        {archivedSessions.length === 0 && (
          <p className="text-center text-sm text-muted-foreground">
            No archived session{search ? ' matches your search' : ''}.
          </p>
        )}
      </div>
    </div>
  )
}
