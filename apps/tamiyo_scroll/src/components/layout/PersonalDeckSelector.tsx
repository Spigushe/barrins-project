import { useState } from 'react'
import { useCreatePersonalDeck, usePersonalDecks } from '@/hooks/usePersonalDecks'
import { useMySettings, useUpdateMySettings } from '@/hooks/useSettings'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
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

  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')

  const activeDeckId = settings?.active_personal_deck_id ?? null
  const activeDeck = personalDecks?.find((deck) => deck.id === activeDeckId)

  const trimmedSearch = search.trim()
  const filteredDecks =
    personalDecks?.filter((deck) =>
      deck.name.toLowerCase().includes(trimmedSearch.toLowerCase()),
    ) ?? []
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
                  >
                    {deck.id === activeDeckId ? '✓ ' : ''}
                    {deck.name}
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
    </div>
  )
}
