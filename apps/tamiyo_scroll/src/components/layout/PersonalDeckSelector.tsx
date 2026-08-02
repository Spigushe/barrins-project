import { useState } from 'react'
import {
  useArchivePersonalDeck,
  useCreatePersonalDeck,
  usePersonalDecks,
  useRenamePersonalDeck,
} from '@/hooks/usePersonalDecks'
import { useMySettings, useUpdateMySettings } from '@/hooks/useSettings'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/lib/utils'

const CREATE_ITEM_VALUE = 'create-new-personal-deck'

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
  const renameDeck = useRenamePersonalDeck()

  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [pendingArchive, setPendingArchive] = useState<{
    id: string
    name: string
  } | null>(null)
  const [pendingRename, setPendingRename] = useState<{
    id: string
    name: string
  } | null>(null)
  const [renameDraft, setRenameDraft] = useState('')

  const activeDeckId = settings?.active_personal_deck_id ?? null
  const activeDeck = personalDecks?.find((deck) => deck.id === activeDeckId)

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
  }

  async function selectDeck(deckId: string) {
    await updateSettings.mutateAsync({ active_personal_deck_id: deckId })
    closeAndReset()
  }

  async function createAndSelect() {
    if (!trimmedSearch) return
    const created = await createDeck.mutateAsync(trimmedSearch)
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
    await renameDeck.mutateAsync({ deckId: pendingRename.id, name: renameDraft.trim() })
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
                {trimmedSearch && !hasExactMatch && (
                  <CommandItem
                    value={CREATE_ITEM_VALUE}
                    onSelect={() => {
                      void createAndSelect()
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

      <Dialog
        open={pendingArchive !== null}
        onOpenChange={(next) => {
          if (!next) setPendingArchive(null)
        }}
      >
        {pendingArchive && (
          <DialogContent>
            <DialogTitle>Archive "{pendingArchive.name}"?</DialogTitle>
            <p className="text-sm text-muted-foreground">
              It will disappear from your deck list. This can't be undone.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setPendingArchive(null)
                }}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="destructive"
                disabled={archiveDeck.isPending}
                onClick={() => {
                  void confirmArchive()
                }}
              >
                Archive
              </Button>
            </div>
          </DialogContent>
        )}
      </Dialog>

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
                disabled={renameDeck.isPending || !renameDraft.trim()}
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
