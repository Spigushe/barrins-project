import { type FormEvent, type ReactNode, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useLogout } from '@/hooks/useAuth'
import { useMySettings, useUpdateMySettings } from '@/hooks/useSettings'
import { useCreatePersonalDeck, usePersonalDecks } from '@/hooks/usePersonalDecks'
import { ActiveDeckContext } from '@/contexts/active-deck-context'
import { SharingControls } from '@/components/layout/SharingControls'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'

const TABS = [
  { to: '/app/metagame', label: 'Metagame' },
  { to: '/app/suivi-bo3', label: 'BO3 Tracking' },
  { to: '/app/decklist', label: 'My decklist' },
]

export function AppShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const { data: settings } = useMySettings()
  const { data: personalDecks } = usePersonalDecks()

  const updateSettings = useUpdateMySettings()
  const createDeck = useCreatePersonalDeck()
  const logout = useLogout()

  const [newDeckName, setNewDeckName] = useState('')

  // Sharing/read-only viewing is disabled for v1.0.0 (SharingControls),
  // so editing one's own data is always allowed here.
  const canEdit = true
  const activeDeckId = settings?.active_personal_deck_id ?? null

  async function handleCreateDeck(event: FormEvent) {
    event.preventDefault()
    if (!newDeckName.trim()) return
    await createDeck.mutateAsync(newDeckName.trim())
    setNewDeckName('')
  }

  async function handleActiveDeckChange(deckId: string) {
    await updateSettings.mutateAsync({ active_personal_deck_id: deckId })
  }

  async function handleLogout() {
    await logout.mutateAsync()
    navigate('/login')
  }

  return (
    <div className="mx-auto max-w-[1400px] px-8 pt-7 pb-20">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-extrabold text-foreground">Tamiyo Scroll</h1>
          <p className="text-[13px] text-muted-foreground">
            Competitive · Test tracking · Duel Commander
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <SharingControls />

          <Button
            type="button"
            variant="outline"
            className="border-warning text-warning hover:bg-warning hover:text-accent-foreground"
            onClick={handleLogout}
          >
            Log out
          </Button>
        </div>
      </header>

      <div className="mt-5 flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="active-deck">My personal deck</Label>
          <Select
            value={activeDeckId ?? undefined}
            onValueChange={handleActiveDeckChange}
          >
            <SelectTrigger id="active-deck" className="w-64">
              <SelectValue placeholder="— none selected —" />
            </SelectTrigger>
            <SelectContent>
              {personalDecks?.map((deck) => (
                <SelectItem key={deck.id} value={deck.id}>
                  {deck.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <form
          className="ml-auto flex items-end gap-2"
          onSubmit={(event) => {
            void handleCreateDeck(event)
          }}
        >
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="new-deck-name">New personal deck name</Label>
            <Input
              id="new-deck-name"
              value={newDeckName}
              onChange={(event) => {
                setNewDeckName(event.target.value)
              }}
              className="w-64"
            />
          </div>
          <Button type="submit" disabled={createDeck.isPending}>
            Create
          </Button>
        </form>
      </div>

      <nav className="mt-6 flex items-end gap-1 border-b border-border">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              cn(
                '-mb-px rounded-t-(--radius-input) border-b-2 border-transparent px-4 py-2.5 text-sm font-semibold text-muted-foreground transition-colors',
                'hover:text-foreground',
                isActive && 'border-accent bg-card text-foreground',
              )
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>

      <ActiveDeckContext.Provider value={{ activeDeckId, canEdit }}>
        <main className="mt-7 flex flex-col gap-7">{children}</main>
      </ActiveDeckContext.Provider>
    </div>
  )
}
