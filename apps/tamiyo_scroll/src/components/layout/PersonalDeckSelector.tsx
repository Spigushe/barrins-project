import { useState } from 'react'
import {
  useArchivePersonalDeck,
  useCreatePersonalDeck,
  usePersonalDecks,
  useUpdatePersonalDeck,
} from '@/hooks/usePersonalDecks'
import { useMySettings, useUpdateMySettings } from '@/hooks/useSettings'
import type { ArchetypeCategory, CardGame } from '@/schemas/tamiyoScroll'
import { ARCHETYPE_LABELS, CARD_GAME_LABELS } from '@/lib/mtg-format'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
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
import { cn } from '@/lib/utils'
import { personalDeckNeedsSetup, PersonalDeckSetupControl } from './PersonalDeckSetupControl'

const CARD_GAME_OPTIONS = Object.keys(CARD_GAME_LABELS) as CardGame[]
const ARCHETYPE_OPTIONS = Object.keys(ARCHETYPE_LABELS) as ArchetypeCategory[]
const GAME_CATEGORY_NOTICE_KEY = 'ts-game-category-migration-notice-dismissed'

/**
 * Single combined control replacing the old "My personal deck" select +
 * "New personal deck name" input/button pair: type to search existing
 * decks, or type a new name and select "Create" to make one — which
 * immediately becomes the active deck (no separate manual reselect step).
 */
export function PersonalDeckSelector() {
  const { data: personalDecks } = usePersonalDecks()
  const { data: settings } = useMySettings()
  const updateSettings = useUpdateMySettings()
  const createDeck = useCreatePersonalDeck()
  const archiveDeck = useArchivePersonalDeck()
  const updateDeck = useUpdatePersonalDeck()

  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [newGame, setNewGame] = useState<CardGame | ''>('')
  const [newCategory, setNewCategory] = useState<ArchetypeCategory | ''>('')
  const [pendingArchive, setPendingArchive] = useState<{
    id: string
    name: string
  } | null>(null)
  const [pendingRename, setPendingRename] = useState<{
    id: string
    name: string
  } | null>(null)
  const [renameDraft, setRenameDraft] = useState('')
  const [noticeDismissed, setNoticeDismissed] = useState(
    () => localStorage.getItem(GAME_CATEGORY_NOTICE_KEY) === 'true',
  )

  const activeDeckId = settings?.active_personal_deck_id ?? null
  const activeDeck = personalDecks?.find((deck) => deck.id === activeDeckId)
  const hasHistoricalDeckNeedingSetup = personalDecks?.some(personalDeckNeedsSetup) ?? false

  const trimmedSearch = search.trim()
  const filteredDecks = (
    personalDecks?.filter((deck) =>
      deck.name.toLowerCase().includes(trimmedSearch.toLowerCase()),
    ) ?? []
  ).sort((a, b) => a.name.localeCompare(b.name))
  const hasExactMatch = personalDecks?.some(
    (deck) => deck.name.toLowerCase() === trimmedSearch.toLowerCase(),
  )

  function closeAndReset() {
    setOpen(false)
    setSearch('')
    setNewGame('')
    setNewCategory('')
  }

  function dismissNotice() {
    localStorage.setItem(GAME_CATEGORY_NOTICE_KEY, 'true')
    setNoticeDismissed(true)
  }

  async function selectDeck(deckId: string) {
    await updateSettings.mutateAsync({ active_personal_deck_id: deckId })
    closeAndReset()
  }

  async function createAndSelect() {
    if (!trimmedSearch || !newGame || !newCategory) return
    const created = await createDeck.mutateAsync({
      name: trimmedSearch,
      game: newGame,
      category: newCategory,
    })
    await updateSettings.mutateAsync({ active_personal_deck_id: created.id })
    closeAndReset()
  }

  async function confirmArchive() {
    if (!pendingArchive) return
    const { id: deckId } = pendingArchive
    await archiveDeck.mutateAsync(deckId)
    if (deckId === activeDeckId) {
      await updateSettings.mutateAsync({ active_personal_deck_id: null })
    }
    setPendingArchive(null)
  }

  async function confirmRename() {
    if (!pendingRename || !renameDraft.trim()) return
    await updateDeck.mutateAsync({ deckId: pendingRename.id, name: renameDraft.trim() })
    setPendingRename(null)
  }

  return (
    <div className="flex flex-col gap-1.5">
      <Label id="personal-deck-label">My personal deck</Label>
      <Popover
        open={open}
        onOpenChange={(next) => {
          setOpen(next)
          if (!next) setSearch('')
        }}
      >
        <PopoverTrigger
          aria-labelledby="personal-deck-label"
          className={cn(
            'flex h-9 w-64 items-center justify-between gap-2 rounded-(--radius-input) border border-border bg-input px-3 py-2 text-sm text-foreground outline-none transition-colors',
            'focus-visible:border-accent',
          )}
        >
          <span className="min-w-0 flex-1 truncate text-left">
            {activeDeck?.name ?? '— none selected —'}
          </span>
        </PopoverTrigger>
        <PopoverContent className="p-0">
          <Command shouldFilter={false}>
            <CommandInput
              placeholder="Search or create a deck…"
              value={search}
              onValueChange={setSearch}
            />
            <CommandList>
              {filteredDecks.length === 0 && !trimmedSearch && (
                <CommandEmpty>No personal decks yet.</CommandEmpty>
              )}
              <CommandGroup>
                {filteredDecks.map((deck) => (
                  <CommandItem
                    key={deck.id}
                    value={deck.id}
                    onSelect={() => {
                      void selectDeck(deck.id)
                    }}
                    className="justify-between"
                  >
                    <span className="min-w-0 truncate">
                      {deck.id === activeDeckId ? '✓ ' : ''}
                      {deck.name}
                    </span>
                    <span className="flex shrink-0 items-center gap-1">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="size-6 shrink-0"
                        aria-label={`Rename ${deck.name}`}
                        onClick={(event) => {
                          event.stopPropagation()
                          setRenameDraft(deck.name)
                          setPendingRename({ id: deck.id, name: deck.name })
                        }}
                      >
                        ✎
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="size-6 shrink-0"
                        aria-label={`Archive ${deck.name}`}
                        onClick={(event) => {
                          event.stopPropagation()
                          setPendingArchive({ id: deck.id, name: deck.name })
                        }}
                      >
                        ✕
                      </Button>
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
            {trimmedSearch && !hasExactMatch && (
              <div className="flex flex-col gap-2 border-t border-border p-2">
                <p className="text-xs text-muted-foreground">
                  Create "{trimmedSearch}" — <span className="text-success">[new]</span>
                </p>
                <div className="flex flex-wrap gap-2">
                  <Select
                    value={newGame}
                    onValueChange={(v) => {
                      setNewGame(v as CardGame)
                    }}
                  >
                    <SelectTrigger className="h-8 w-40 text-xs">
                      <SelectValue placeholder="Game — required" />
                    </SelectTrigger>
                    <SelectContent>
                      {CARD_GAME_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {CARD_GAME_LABELS[option]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select
                    value={newCategory}
                    onValueChange={(v) => {
                      setNewCategory(v as ArchetypeCategory)
                    }}
                  >
                    <SelectTrigger className="h-8 w-36 text-xs">
                      <SelectValue placeholder="Archetype — required" />
                    </SelectTrigger>
                    <SelectContent>
                      {ARCHETYPE_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {ARCHETYPE_LABELS[option]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button
                  type="button"
                  size="sm"
                  disabled={!newGame || !newCategory || createDeck.isPending}
                  onClick={() => {
                    void createAndSelect()
                  }}
                >
                  Create
                </Button>
              </div>
            )}
          </Command>
        </PopoverContent>
      </Popover>

      {!noticeDismissed && hasHistoricalDeckNeedingSetup && (
        <div className="flex items-center justify-between gap-2 rounded-(--radius-input) border border-warning/40 bg-warning/10 p-2 text-xs text-muted-foreground">
          <span>
            v2 requires a game and archetype per deck — set them on your
            existing decks before logging new results.
          </span>
          <Button type="button" variant="ghost" size="sm" onClick={dismissNotice}>
            Dismiss
          </Button>
        </div>
      )}

      {activeDeck && <PersonalDeckSetupControl deck={activeDeck} />}

      <ConfirmDialog
        open={pendingArchive !== null}
        onOpenChange={(next) => {
          if (!next) setPendingArchive(null)
        }}
        title={pendingArchive ? `Archive "${pendingArchive.name}"?` : ''}
        description="It will disappear from your deck list. This can't be undone."
        confirmLabel="Archive"
        confirmDisabled={archiveDeck.isPending}
        onConfirm={() => {
          void confirmArchive()
        }}
      />

      <Dialog
        open={pendingRename !== null}
        onOpenChange={(next) => {
          if (!next) setPendingRename(null)
        }}
      >
        {pendingRename && (
          <DialogContent>
            <DialogTitle>Rename "{pendingRename.name}"</DialogTitle>
            <Input
              aria-label="New deck name"
              value={renameDraft}
              onChange={(event) => {
                setRenameDraft(event.target.value)
              }}
            />
            <div className="mt-4 flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setPendingRename(null)
                }}
              >
                Cancel
              </Button>
              <Button
                type="button"
                disabled={updateDeck.isPending || !renameDraft.trim()}
                onClick={() => {
                  void confirmRename()
                }}
              >
                Save
              </Button>
            </div>
          </DialogContent>
        )}
      </Dialog>
    </div>
  )
}
