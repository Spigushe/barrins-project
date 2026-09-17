import { type FormEvent, useState } from 'react'
import { useCurrentUser } from '@barrins/goblin-guide'
import { resolveMetaDeckOption, useCreateMetaDeck } from '@/hooks/useMetaDecks'
import { useCreateSession, useSessions } from '@/hooks/useSessions'
import type {
  ArchetypeCategory,
  GameResult,
  Match,
  MatchGame,
  MatchGameEvent,
  MatchGameEventWrite,
  MatchGameWrite,
  MatchWrite,
  SessionType,
} from '@/schemas/tamiyoScroll'
import { ARCHETYPE_LABELS, GAME_RESULT_LABELS } from '@/lib/mtg-format'
import { roleMeetsFloor } from '@/lib/roles'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'

const SESSION_TYPE_LABELS: Record<SessionType, string> = {
  tournament: 'Tournament',
  training: 'Training',
}

export const GAME_NOT_PLAYED = '__not_played__'
const GAME_OPTIONS = ['win', 'loss', 'draw'] as const
const TIERS = [0, 0.5, 1, 1.5, 2, 2.5, 3]
const ARCHETYPE_OPTIONS = Object.keys(ARCHETYPE_LABELS) as ArchetypeCategory[]
const CREATE_ITEM_VALUE = 'create-new-opponent-deck'

/**
 * One logged mulligan/misplay event's draft state (D2's second amendment —
 * per-event, not per-game×side, comments). `id` is only ever set for an
 * event that's already round-tripped through a save (used as the React
 * key); a brand-new event created client-side by "+1" has none yet, and
 * the write side never sends one back (an edit is matched to its existing
 * row by array position/sequence server-side, not by id).
 */
export interface MatchGameEventDraft {
  id?: string
  comment: string
}

/**
 * One game's draft state (#123/#124 — see
 * docs/project/issue-scoping/123-124-structured-match-log.md). `result`
 * stays a string carrying either a `GameResult` or the `GAME_NOT_PLAYED`
 * sentinel, same convention the old flat `game1/2/3` fields used.
 *
 * `playerMulligans`/`opponentMulligans`/`playerMisplays`/`opponentMisplays`
 * are the D2 gated event lists — kept empty (`[]`) until a `moderator`+
 * user actually clicks "+1", so an ordinary user's write payload never
 * sends a non-empty list there and never trips the backend's field-level
 * 403 backstop.
 */
export interface MatchGameDraft {
  /** `null` = not known — no prior game to derive from yet (or the prior
   * game was a draw, which has no loser to make the choice), and the user
   * hasn't manually chosen one either. */
  onPlay: boolean | null
  /** Whether the user explicitly chose `onPlay` (via the Play/Draw select)
   * rather than it being the derived default below — a manual choice is
   * never silently overwritten by a later edit to the previous game's
   * result. */
  onPlayTouched: boolean
  result: string
  playerMulligans: MatchGameEventDraft[]
  opponentMulligans: MatchGameEventDraft[]
  playerMisplays: MatchGameEventDraft[]
  opponentMisplays: MatchGameEventDraft[]
}

export type MatchGamesDraft = [MatchGameDraft, MatchGameDraft, MatchGameDraft]

/** Game 2/3's Play/Draw defaults from the previous game's result, per the
 * "loser chooses" convention (assumed to choose to play) — a default only,
 * applied by `applyDerivedOnPlay` below, never overriding a value the user
 * has explicitly set (`onPlayTouched`). No default when the previous game
 * was a draw (no loser) or hasn't been played yet — stays `null`/unknown,
 * same as a never-derived value. */
function deriveOnPlay(previousResult: string): boolean | null {
  if (previousResult === 'loss') return true
  if (previousResult === 'win') return false
  return null
}

/** Recomputes every untouched game's derived `onPlay` from the game before
 * it. Safe to call after any single-field change — it only ever touches
 * `onPlay` on a game whose `onPlayTouched` is still `false`. */
export function applyDerivedOnPlay(games: MatchGamesDraft): MatchGamesDraft {
  const next = [...games] as MatchGamesDraft
  for (const index of [1, 2] as const) {
    if (!next[index].onPlayTouched) {
      next[index] = { ...next[index], onPlay: deriveOnPlay(next[index - 1].result) }
    }
  }
  return next
}

export interface MatchDraft {
  personalDeckId: string
  opponentDeckId: string
  decklistVersionId: string | null
  sessionId: string | null
  /** Index 0 = game 1, index 1 = game 2, index 2 = game 3. */
  games: MatchGamesDraft
  openingHand: string
  turningPoint: string
  finalTurn: string
}

function emptyGameDraft(defaultOnPlay: boolean | null): MatchGameDraft {
  return {
    onPlay: defaultOnPlay,
    onPlayTouched: false,
    result: GAME_NOT_PLAYED,
    playerMulligans: [],
    opponentMulligans: [],
    playerMisplays: [],
    opponentMisplays: [],
  }
}

export function emptyMatchDraft(defaultPersonalDeckId: string | null): MatchDraft {
  return {
    personalDeckId: defaultPersonalDeckId ?? '',
    opponentDeckId: '',
    decklistVersionId: null,
    sessionId: null,
    // Game 1 has no previous game to derive from — it's the only one that
    // still needs an explicit starting default (the pre-existing "On the
    // Play" default). Games 2/3 start unknown until derived or chosen.
    games: [emptyGameDraft(true), emptyGameDraft(null), emptyGameDraft(null)],
    openingHand: '',
    turningPoint: '',
    finalTurn: '',
  }
}

/** `null` means "not tracked" (a sub-`moderator`'s game, or a pre-migration
 * historical row) — nothing to edit, same as an empty list. */
function eventDraftsFromMatchGame(events: MatchGameEvent[] | null): MatchGameEventDraft[] {
  if (!events) return []
  return events.map((event) => ({ id: event.id, comment: event.comment ?? '' }))
}

function gameDraftFromMatchGame(
  game: MatchGame | undefined,
  defaultOnPlay: boolean | null,
): MatchGameDraft {
  if (!game) return emptyGameDraft(defaultOnPlay)
  return {
    onPlay: game.on_play,
    // A concrete stored value is a fact the user (or a prior derivation
    // that got saved) already settled — never silently recomputed out from
    // under them. Only a genuinely unknown stored value stays open to the
    // live derivation below.
    onPlayTouched: game.on_play !== null,
    result: game.result ?? GAME_NOT_PLAYED,
    playerMulligans: eventDraftsFromMatchGame(game.player_mulligans),
    opponentMulligans: eventDraftsFromMatchGame(game.opponent_mulligans),
    playerMisplays: eventDraftsFromMatchGame(game.player_misplays),
    opponentMisplays: eventDraftsFromMatchGame(game.opponent_misplays),
  }
}

export function draftFromMatch(match: Match): MatchDraft {
  const byNumber = new Map(match.games.map((game) => [game.game_number, game]))
  const games = [1, 2, 3].map((gameNumber) =>
    gameDraftFromMatchGame(byNumber.get(gameNumber), gameNumber === 1 ? true : null),
  ) as MatchGamesDraft
  return {
    personalDeckId: match.personal_deck_id,
    opponentDeckId: match.opponent_deck_id,
    decklistVersionId: match.decklist_version_id,
    sessionId: match.session_id,
    // Re-derive on load too — an existing match whose game 2/3 was never
    // touched should already show the best default on open, not only after
    // the user re-edits game 1 in this session.
    games: applyDerivedOnPlay(games),
    openingHand: match.opening_hand ?? '',
    turningPoint: match.turning_point ?? '',
    finalTurn: match.final_turn ?? '',
  }
}

/** Whether this game has any data at all — used to decide whether it
 * belongs in the write payload (D8: a `ts_match_games` row is only created
 * once something is entered for that game). Game 1 is always included
 * (mirrors the old flat schema, which always recorded a match-level
 * `on_play` even before any game had a result), games 2/3 only once
 * touched. A merely-derived `onPlay` doesn't count as "touched" here — it's
 * a display default, not something the user actually entered. */
function gameDraftIsEntered(game: MatchGameDraft): boolean {
  return (
    game.result !== GAME_NOT_PLAYED ||
    game.onPlayTouched ||
    game.playerMulligans.length > 0 ||
    game.opponentMulligans.length > 0 ||
    game.playerMisplays.length > 0 ||
    game.opponentMisplays.length > 0
  )
}

/** No `id` sent back (see `MatchGameEventDraft`) — array position is the
 * event's sequence. */
function eventsToWrite(events: MatchGameEventDraft[]): MatchGameEventWrite[] {
  return events.map((event) => ({ comment: event.comment.trim() || null }))
}

function gameDraftToWrite(gameNumber: number, game: MatchGameDraft): MatchGameWrite {
  return {
    game_number: gameNumber,
    on_play: game.onPlay,
    result: game.result === GAME_NOT_PLAYED ? null : (game.result as GameResult),
    player_mulligans: eventsToWrite(game.playerMulligans),
    opponent_mulligans: eventsToWrite(game.opponentMulligans),
    player_misplays: eventsToWrite(game.playerMisplays),
    opponent_misplays: eventsToWrite(game.opponentMisplays),
  }
}

export function matchDraftToWrite(draft: MatchDraft): MatchWrite {
  const games = draft.games
    .map((game, index) => ({ gameNumber: index + 1, game }))
    .filter(({ gameNumber, game }) => gameNumber === 1 || gameDraftIsEntered(game))
    .map(({ gameNumber, game }) => gameDraftToWrite(gameNumber, game))

  return {
    personal_deck_id: draft.personalDeckId,
    opponent_deck_id: draft.opponentDeckId,
    decklist_version_id: draft.decklistVersionId,
    session_id: draft.sessionId,
    games,
    opening_hand: draft.openingHand.trim() || null,
    turning_point: draft.turningPoint.trim() || null,
    final_turn: draft.finalTurn.trim() || null,
  }
}

export function matchDraftIsValid(draft: MatchDraft): boolean {
  return draft.personalDeckId !== '' && draft.opponentDeckId !== ''
}

function GameResultSelect({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label>{label}</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-36">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={GAME_NOT_PLAYED}>— not played —</SelectItem>
          {GAME_OPTIONS.map((result) => (
            <SelectItem key={result} value={result}>
              {GAME_RESULT_LABELS[result]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

/**
 * D2's live "+1" counter, purpose-built rather than copying
 * `CardTestsSection.tsx`'s `<Select>` + pinned-add-row chrome (rejected —
 * see D2's amendment: this is bounded, high-frequency, live-during-play
 * entry, not an occasional unbounded list).
 *
 * Second amendment: "+1" doesn't just bump a number — it immediately
 * *logs a new event* (a blank-comment entry appended to `events`); the
 * visible count is simply `events.length`, so there is nothing else to
 * keep in sync. Below the "+1" button, every logged event renders as its
 * own numbered row ("Mulligan #1", "#2", …) with its own independently
 * editable comment, and can be removed individually.
 */
function EventList({
  label,
  itemLabel,
  events,
  onChange,
}: {
  /** Plural group label, e.g. "Mulligans". */
  label: string
  /** Singular label for each numbered row, e.g. "Mulligan". */
  itemLabel: string
  events: MatchGameEventDraft[]
  onChange: (next: MatchGameEventDraft[]) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2">
        <Label>{label}</Label>
        <span className="font-mono text-xs text-muted-foreground">
          ({String(events.length)})
        </span>
        <Button
          type="button"
          size="icon"
          aria-label={`Log a new ${itemLabel.toLowerCase()} (+1)`}
          onClick={() => {
            onChange([...events, { comment: '' }])
          }}
        >
          +1
        </Button>
      </div>
      {events.length > 0 && (
        <ol className="flex flex-col gap-1.5">
          {events.map((event, index) => (
            <li
              // Server-assigned ids are stable across renders; a brand-new,
              // not-yet-saved event has none yet, so its position in this
              // render pass is the only key available.
              key={event.id ?? index}
              className="flex items-center gap-2"
            >
              <span className="w-20 shrink-0 text-xs text-muted-foreground">
                {itemLabel} #{index + 1}
              </span>
              <Input
                aria-label={`${itemLabel} #${String(index + 1)} comment`}
                value={event.comment}
                onChange={(changeEvent) => {
                  const next = [...events]
                  next[index] = { ...event, comment: changeEvent.target.value }
                  onChange(next)
                }}
              />
              <Button
                type="button"
                size="icon"
                variant="ghost"
                aria-label={`Remove ${itemLabel} #${String(index + 1)}`}
                onClick={() => {
                  onChange(events.filter((_candidate, i) => i !== index))
                }}
              >
                ×
              </Button>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

/** D2's per-game×side group: mulligan + misplay event lists, placed beside
 * the game's other stepper controls and (by the caller) beside that same
 * game's existing Notes textarea. Only rendered for a `moderator`+
 * `currentUser` — see `MatchFormFields`. */
function SideEventGroup({
  sideLabel,
  mulligans,
  misplays,
  onMulligansChange,
  onMisplaysChange,
}: {
  sideLabel: string
  mulligans: MatchGameEventDraft[]
  misplays: MatchGameEventDraft[]
  onMulligansChange: (next: MatchGameEventDraft[]) => void
  onMisplaysChange: (next: MatchGameEventDraft[]) => void
}) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs font-semibold text-muted-foreground">{sideLabel}</span>
      <div className="flex flex-wrap gap-4">
        <EventList
          label="Mulligans"
          itemLabel="Mulligan"
          events={mulligans}
          onChange={onMulligansChange}
        />
        <EventList
          label="Misplays"
          itemLabel="Misplay"
          events={misplays}
          onChange={onMisplaysChange}
        />
      </div>
    </div>
  )
}

interface OpponentDeckOption {
  id: string
  name: string
  is_readonly?: boolean
  tier?: number
  category?: ArchetypeCategory
  merged_ids?: string[]
}

/**
 * Opponent deck field: search existing meta decks, or type a new name and
 * "Create" it without leaving this form. name/tier/category match exactly
 * what the existing quick-add form on the Metagame roster page collects
 * (`MetaDecksSections.tsx`) — top8/presence/expected default the same way
 * it does (0/0/'as_expected': a freshly-noted deck genuinely has zero
 * recorded Top 8s/presence so far, and hasn't been evaluated against
 * expectations yet).
 *
 * A `is_readonly` option (present only because a sharer's data merged it
 * in — see `sharing_merge.py`) can't be used as-is: it isn't owned by the
 * current user, so the backend 404s on it (`_validate_match_refs`).
 * Selecting one opens the same create dialog instead, pre-filled with the
 * shared tier/category as a starting point — submitting it creates the
 * user's own roster entry (same name, so future merges resolve to it per
 * the "own ranking wins" rule) and uses that as the opponent.
 */
function OpponentDeckField({
  value,
  onChange,
  options,
  personalDeckId,
}: {
  value: string
  onChange: (deckId: string) => void
  options: OpponentDeckOption[]
  /** The deck this match is being logged for — the new opponent entry is
   * created against it (required server-side, F10). */
  personalDeckId: string
}) {
  const createMetaDeck = useCreateMetaDeck()

  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [creating, setCreating] = useState(false)
  const [claimingShared, setClaimingShared] = useState(false)
  const [pendingName, setPendingName] = useState('')
  const [newTier, setNewTier] = useState(1)
  const [newCategory, setNewCategory] = useState<ArchetypeCategory>('midrange')

  const selected = resolveMetaDeckOption(options, value)
  const trimmedSearch = search.trim()
  const filtered = options.filter((deck) =>
    deck.name.toLowerCase().includes(trimmedSearch.toLowerCase()),
  )
  const hasExactMatch = options.some(
    (deck) => deck.name.toLowerCase() === trimmedSearch.toLowerCase(),
  )

  function selectDeck(deck: OpponentDeckOption) {
    if (deck.is_readonly) {
      setPendingName(deck.name)
      setNewTier(deck.tier ?? 1)
      setNewCategory(deck.category ?? 'midrange')
      setClaimingShared(true)
      setCreating(true)
      setOpen(false)
      setSearch('')
      return
    }
    onChange(deck.id)
    setOpen(false)
    setSearch('')
  }

  function openCreateDialog() {
    setPendingName(trimmedSearch)
    setNewTier(1)
    setNewCategory('midrange')
    setClaimingShared(false)
    setCreating(true)
    setOpen(false)
    setSearch('')
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    const created = await createMetaDeck.mutateAsync({
      name: pendingName,
      tier: newTier,
      category: newCategory,
      decklist_notes: null,
      top8: 0,
      presence: 0,
      expected: 'as_expected',
      tests_status: null,
      personal_deck_id: personalDeckId,
    })
    onChange(created.id)
    setCreating(false)
    setClaimingShared(false)
    setNewTier(1)
    setNewCategory('midrange')
  }

  return (
    <div className="flex flex-col gap-1.5">
      <Label id="opponent-deck-label">Opponent</Label>
      <Popover
        open={open}
        onOpenChange={(next) => {
          setOpen(next)
          if (!next) setSearch('')
        }}
      >
        <PopoverTrigger
          aria-labelledby="opponent-deck-label"
          className={cn(
            'flex h-9 w-52 items-center justify-between gap-2 rounded-(--radius-input) border border-border bg-input px-3 py-2 text-sm text-foreground outline-none transition-colors',
            'focus-visible:border-accent',
          )}
        >
          <span className="min-w-0 flex-1 truncate text-left">
            {selected?.name ?? '— select —'}
          </span>
        </PopoverTrigger>
        <PopoverContent className="p-0">
          <Command shouldFilter={false}>
            <CommandInput
              placeholder="Search or create…"
              value={search}
              onValueChange={setSearch}
            />
            <CommandList>
              {filtered.length === 0 && !trimmedSearch && (
                <CommandEmpty>No opponent decks yet.</CommandEmpty>
              )}
              <CommandGroup>
                {filtered.map((deck) => (
                  <CommandItem
                    key={deck.id}
                    value={deck.id}
                    onSelect={() => {
                      selectDeck(deck)
                    }}
                  >
                    <span className="flex min-w-0 flex-1 flex-col">
                      <span>
                        {deck.id === value || deck.merged_ids?.includes(value)
                          ? '✓ '
                          : ''}
                        {deck.name}
                      </span>
                      {deck.is_readonly && (
                        <span className="text-[11px] text-muted-foreground">
                          shared — tap to add to your roster
                        </span>
                      )}
                    </span>
                  </CommandItem>
                ))}
                {trimmedSearch && !hasExactMatch && (
                  <CommandItem
                    value={CREATE_ITEM_VALUE}
                    onSelect={() => {
                      openCreateDialog()
                    }}
                  >
                    Create "{trimmedSearch}"
                  </CommandItem>
                )}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent>
          <DialogTitle>
            {claimingShared ? 'Add shared deck to your roster' : 'Create opponent deck'}
          </DialogTitle>
          <form
            className="flex flex-col gap-3"
            onSubmit={(event) => {
              void handleCreate(event)
            }}
          >
            <div>
              <Label>Name</Label>
              <p className="mt-1 text-sm font-medium text-foreground">{pendingName}</p>
              {claimingShared && (
                <p className="mt-1 text-xs text-muted-foreground">
                  This deck exists via shared data. Confirm its tier and archetype to add
                  it to your own roster.
                </p>
              )}
            </div>
            <div className="flex flex-wrap gap-3">
              <div className="flex flex-col gap-1.5">
                <Label>Tier</Label>
                <Select
                  value={String(newTier)}
                  onValueChange={(v) => {
                    setNewTier(Number(v))
                  }}
                >
                  <SelectTrigger className="w-24">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TIERS.map((tier) => (
                      <SelectItem key={tier} value={String(tier)}>
                        {tier}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Category</Label>
                <Select
                  value={newCategory}
                  onValueChange={(v) => {
                    setNewCategory(v as ArchetypeCategory)
                  }}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ARCHETYPE_OPTIONS.map((category) => (
                      <SelectItem key={category} value={category}>
                        {ARCHETYPE_LABELS[category]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={createMetaDeck.isPending}>
                {claimingShared ? 'Add to roster' : 'Create'}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setCreating(false)
                  setClaimingShared(false)
                }}
              >
                Cancel
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

const NO_VERSION_VALUE = '__no_version__'
const NO_SESSION_LABEL = '— none —'
const CREATE_SESSION_ITEM_VALUE = 'create-new-session'

/**
 * Optional tournament/training session grouping (S9). Fetches sessions for
 * whatever deck is currently selected in the form. Same searchable
 * combobox + inline "Create" shape as `OpponentDeckField` above (per the
 * user, 2026-07-30) — a "— none —" entry at the top of the list is the
 * only addition, since unlike the opponent a session is optional.
 */
function SessionField({
  personalDeckId,
  value,
  onChange,
}: {
  personalDeckId: string
  value: string | null
  onChange: (sessionId: string | null) => void
}) {
  const { data: sessions } = useSessions(personalDeckId || null)
  const createSession = useCreateSession()

  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [creating, setCreating] = useState(false)
  const [pendingName, setPendingName] = useState('')
  const [newType, setNewType] = useState<SessionType>('training')

  const allSessions = sessions ?? []
  // A closed session can't be picked for a new/changed match — but if the
  // match is already tied to one (logged before it closed), its name must
  // still resolve correctly rather than falling back to "— none —".
  const selectableSessions = allSessions.filter((session) => session.closed_at === null)
  const selected = allSessions.find((session) => session.id === value)
  const trimmedSearch = search.trim()
  const filtered = selectableSessions.filter((session) =>
    session.name.toLowerCase().includes(trimmedSearch.toLowerCase()),
  )
  const hasExactMatch = selectableSessions.some(
    (session) => session.name.toLowerCase() === trimmedSearch.toLowerCase(),
  )

  function selectSession(sessionId: string | null) {
    onChange(sessionId)
    setOpen(false)
    setSearch('')
  }

  function openCreateDialog() {
    setPendingName(trimmedSearch)
    setNewType('training')
    setCreating(true)
    setOpen(false)
    setSearch('')
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    const created = await createSession.mutateAsync({
      name: pendingName,
      type: newType,
      personal_deck_id: personalDeckId,
    })
    onChange(created.id)
    setCreating(false)
    setNewType('training')
  }

  return (
    <div className="flex flex-col gap-1.5">
      <Label id="session-label">Session</Label>
      <Popover
        open={open}
        onOpenChange={(next) => {
          setOpen(next)
          if (!next) setSearch('')
        }}
      >
        <PopoverTrigger
          aria-labelledby="session-label"
          disabled={!personalDeckId}
          className={cn(
            'flex h-9 w-52 items-center justify-between gap-2 rounded-(--radius-input) border border-border bg-input px-3 py-2 text-sm text-foreground outline-none transition-colors',
            'focus-visible:border-accent',
          )}
        >
          <span className="min-w-0 flex-1 truncate text-left">
            {selected?.name ?? NO_SESSION_LABEL}
          </span>
        </PopoverTrigger>
        <PopoverContent className="p-0">
          <Command shouldFilter={false}>
            <CommandInput
              placeholder="Search or create…"
              value={search}
              onValueChange={setSearch}
            />
            <CommandList>
              <CommandGroup>
                <CommandItem
                  value={NO_SESSION_LABEL}
                  onSelect={() => {
                    selectSession(null)
                  }}
                >
                  {value === null ? '✓ ' : ''}
                  {NO_SESSION_LABEL}
                </CommandItem>
                {filtered.map((session) => (
                  <CommandItem
                    key={session.id}
                    value={session.id}
                    onSelect={() => {
                      selectSession(session.id)
                    }}
                  >
                    {session.id === value ? '✓ ' : ''}
                    {session.name}
                  </CommandItem>
                ))}
                {trimmedSearch && !hasExactMatch && (
                  <CommandItem
                    value={CREATE_SESSION_ITEM_VALUE}
                    onSelect={() => {
                      openCreateDialog()
                    }}
                  >
                    Create "{trimmedSearch}"
                  </CommandItem>
                )}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent>
          <DialogTitle>Create session</DialogTitle>
          <form
            className="flex flex-col gap-3"
            onSubmit={(event) => {
              void handleCreate(event)
            }}
          >
            <div>
              <Label>Name</Label>
              <p className="mt-1 text-sm font-medium text-foreground">{pendingName}</p>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Type</Label>
              <Select
                value={newType}
                onValueChange={(v) => {
                  setNewType(v as SessionType)
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
            <div className="flex gap-2">
              <Button type="submit" disabled={createSession.isPending}>
                Create
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setCreating(false)
                }}
              >
                Cancel
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

/** One game's column: header + per-game "Play/Draw"/result selects
 * (ungated — every user can already submit these, D7), that game's
 * existing free-text Notes textarea (D3, unchanged), and — only for a
 * `moderator`+ `currentUser` — the D2 mulligan/misplay stepper rows,
 * placed directly beside the stepper's own comment input and beside this
 * same game's Notes textarea, per game number (not a detached section). */
function GameColumn({
  gameNumber,
  game,
  onGameChange,
  notesLabel,
  notesId,
  notesValue,
  onNotesChange,
  canEditGatedFields,
}: {
  gameNumber: number
  game: MatchGameDraft
  onGameChange: (next: MatchGameDraft) => void
  notesLabel: string
  notesId: string
  notesValue: string
  onNotesChange: (value: string) => void
  canEditGatedFields: boolean
}) {
  return (
    <div className="flex flex-col gap-3 rounded-(--radius-input) border border-border p-3">
      <div className="flex flex-wrap items-end gap-3">
        <GameResultSelect
          label={`Game ${String(gameNumber)}`}
          value={game.result}
          onChange={(value) => {
            onGameChange({ ...game, result: value })
          }}
        />
        <div className="flex flex-col gap-1.5">
          <Label>Play/Draw</Label>
          <Select
            value={game.onPlay === null ? undefined : game.onPlay ? 'otp' : 'otd'}
            onValueChange={(value) => {
              // A manual choice always wins — mark it touched so a later
              // edit to the previous game's result never overwrites it
              // (see `applyDerivedOnPlay`).
              onGameChange({ ...game, onPlay: value === 'otp', onPlayTouched: true })
            }}
          >
            <SelectTrigger className="w-36">
              <SelectValue placeholder="— unknown —" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="otp">On the Play</SelectItem>
              <SelectItem value="otd">On the Draw</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor={notesId}>{notesLabel}</Label>
        <Textarea
          id={notesId}
          rows={3}
          value={notesValue}
          onChange={(event) => {
            onNotesChange(event.target.value)
          }}
        />
      </div>

      {canEditGatedFields && (
        <div className="flex flex-col gap-3 border-t border-border pt-3">
          <SideEventGroup
            sideLabel="Player"
            mulligans={game.playerMulligans}
            misplays={game.playerMisplays}
            onMulligansChange={(next) => {
              onGameChange({ ...game, playerMulligans: next })
            }}
            onMisplaysChange={(next) => {
              onGameChange({ ...game, playerMisplays: next })
            }}
          />
          <SideEventGroup
            sideLabel="Opponent"
            mulligans={game.opponentMulligans}
            misplays={game.opponentMisplays}
            onMulligansChange={(next) => {
              onGameChange({ ...game, opponentMulligans: next })
            }}
            onMisplaysChange={(next) => {
              onGameChange({ ...game, opponentMisplays: next })
            }}
          />
        </div>
      )}
    </div>
  )
}

export function MatchFormFields({
  draft,
  onChange,
  personalDeckOptions,
  metaDeckOptions,
  decklistVersionOptions,
}: {
  draft: MatchDraft
  onChange: (next: MatchDraft) => void
  personalDeckOptions: { id: string; name: string }[]
  metaDeckOptions: OpponentDeckOption[]
  /** Only passed (and rendered) by the edit flow — never on match creation,
   * which always auto-stamps the deck's current version server-side. */
  decklistVersionOptions?: { id: string; version: number }[]
}) {
  // D7/D2: the stepper+comment rows are a static `moderator`+ floor,
  // client-side UX convenience only — the backend's field-level 403 on
  // `_apply_payload` is the real boundary. Below that floor, the form
  // renders exactly as it did before this feature (D7).
  const { data: currentUser } = useCurrentUser()
  const canEditGatedFields = roleMeetsFloor(currentUser?.role, 'moderator')

  function updateGame(index: 0 | 1 | 2, next: MatchGameDraft) {
    const games = [...draft.games] as MatchGamesDraft
    games[index] = next
    onChange({ ...draft, games: applyDerivedOnPlay(games) })
  }
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-3">
        <div className="flex flex-col gap-1.5">
          <Label>My deck</Label>
          <Select
            value={draft.personalDeckId}
            onValueChange={(value) => {
              // A session belongs to one deck — switching decks invalidates
              // whatever session was selected for the previous one.
              onChange({ ...draft, personalDeckId: value, sessionId: null })
            }}
          >
            <SelectTrigger className="w-52">
              <SelectValue placeholder="— select —" />
            </SelectTrigger>
            <SelectContent>
              {personalDeckOptions.map((deck) => (
                <SelectItem key={deck.id} value={deck.id}>
                  {deck.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {decklistVersionOptions && decklistVersionOptions.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <Label>Decklist version</Label>
            <Select
              value={draft.decklistVersionId ?? NO_VERSION_VALUE}
              onValueChange={(value) => {
                onChange({
                  ...draft,
                  decklistVersionId: value === NO_VERSION_VALUE ? null : value,
                })
              }}
            >
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_VERSION_VALUE}>— none —</SelectItem>
                {decklistVersionOptions.map((version) => (
                  <SelectItem key={version.id} value={version.id}>
                    v{version.version}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
        <OpponentDeckField
          value={draft.opponentDeckId}
          onChange={(deckId) => {
            onChange({ ...draft, opponentDeckId: deckId })
          }}
          options={metaDeckOptions}
          personalDeckId={draft.personalDeckId}
        />
        {draft.personalDeckId && (
          <SessionField
            personalDeckId={draft.personalDeckId}
            value={draft.sessionId}
            onChange={(sessionId) => {
              onChange({ ...draft, sessionId })
            }}
          />
        )}
      </div>

      {/* Per game: result + Play/Draw (now per-game, D1's "Full"
          normalization — every user can set these, unchanged from before
          except that Play/Draw is no longer one match-wide choice), that
          game's existing free-text Notes (D3), and — moderator+ only —
          the D2 mulligan/misplay steppers. */}
      <div className="grid gap-3 md:grid-cols-3">
        {/* S12 item 3: the three labels below ("Game 1/2/3 Notes") are a
            label-only rename of "Opening hand"/"Turning point"/"Final
            turn" — `openingHand`/`turningPoint`/`finalTurn` and their
            wire names are unchanged (D3). */}
        <GameColumn
          gameNumber={1}
          game={draft.games[0]}
          onGameChange={(next) => {
            updateGame(0, next)
          }}
          notesLabel="Game 1 Notes"
          notesId="opening-hand"
          notesValue={draft.openingHand}
          onNotesChange={(value) => {
            onChange({ ...draft, openingHand: value })
          }}
          canEditGatedFields={canEditGatedFields}
        />
        <GameColumn
          gameNumber={2}
          game={draft.games[1]}
          onGameChange={(next) => {
            updateGame(1, next)
          }}
          notesLabel="Game 2 Notes"
          notesId="turning-point"
          notesValue={draft.turningPoint}
          onNotesChange={(value) => {
            onChange({ ...draft, turningPoint: value })
          }}
          canEditGatedFields={canEditGatedFields}
        />
        <GameColumn
          gameNumber={3}
          game={draft.games[2]}
          onGameChange={(next) => {
            updateGame(2, next)
          }}
          notesLabel="Game 3 Notes"
          notesId="final-turn"
          notesValue={draft.finalTurn}
          onNotesChange={(value) => {
            onChange({ ...draft, finalTurn: value })
          }}
          canEditGatedFields={canEditGatedFields}
        />
      </div>
    </div>
  )
}
