import { type FormEvent, type ReactNode, useEffect, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useCurrentUser, useLogout } from '@/hooks/useAuth'
import { useMySettings, useSharedUsers, useUpdateMySettings } from '@/hooks/useSettings'
import { useCreatePersonalDeck, usePersonalDecks } from '@/hooks/usePersonalDecks'
import { useViewingOwner } from '@/hooks/useViewingOwner'
import { setViewingOwner } from '@/api/viewingOwner'
import { ActiveDeckContext } from '@/contexts/active-deck-context'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
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

const SELF_VALUE = '__self__'

const TABS = [
  { to: '/app/metagame', label: 'Métagame' },
  { to: '/app/suivi-bo3', label: 'Suivi BO3' },
  { to: '/app/decklist', label: 'Ma decklist' },
]

export function AppShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const { data: currentUser } = useCurrentUser()
  const { data: settings } = useMySettings()
  const { data: sharedUsers } = useSharedUsers()
  const { data: personalDecks } = usePersonalDecks()
  const viewingOwner = useViewingOwner()

  const updateSettings = useUpdateMySettings()
  const createDeck = useCreatePersonalDeck()
  const logout = useLogout()

  const [newDeckName, setNewDeckName] = useState('')
  const canEdit = viewingOwner === null

  // Sélection du deck actif : persistée via /me/settings pour ses propres
  // données, mais purement locale en mode "vue partagée" — le backend
  // n'expose pas la préférence de deck actif d'un tiers (elle est privée),
  // donc on choisit localement quel deck du tiers consulter.
  const [localSelectedDeckId, setLocalSelectedDeckId] = useState<string | null>(null)

  useEffect(() => {
    if (canEdit) return
    setLocalSelectedDeckId(personalDecks?.[0]?.id ?? null)
  }, [canEdit, personalDecks])

  const activeDeckId = canEdit
    ? (settings?.active_personal_deck_id ?? null)
    : localSelectedDeckId

  async function handleCreateDeck(event: FormEvent) {
    event.preventDefault()
    if (!newDeckName.trim()) return
    await createDeck.mutateAsync(newDeckName.trim())
    setNewDeckName('')
  }

  async function handleActiveDeckChange(deckId: string) {
    if (canEdit) {
      await updateSettings.mutateAsync({ active_personal_deck_id: deckId })
    } else {
      setLocalSelectedDeckId(deckId)
    }
  }

  function handleViewingChange(value: string) {
    if (value === SELF_VALUE) {
      setViewingOwner(null)
      return
    }
    const user = sharedUsers?.find((candidate) => candidate.id === value)
    if (user) {
      setViewingOwner({ id: user.id, label: user.display_name ?? user.email })
    }
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
            Compétitif · Suivi tests · Duel Commander
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {viewingOwner !== null && (
            <Badge variant="warning">
              Consultation : {viewingOwner.label} · lecture seule
            </Badge>
          )}

          <Select
            value={viewingOwner?.id ?? SELF_VALUE}
            onValueChange={handleViewingChange}
          >
            <SelectTrigger className="w-56">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={SELF_VALUE}>
                Mon compte ({currentUser?.email ?? '…'})
              </SelectItem>
              {sharedUsers?.map((user) => (
                <SelectItem key={user.id} value={user.id}>
                  Voir : {user.display_name ?? user.email}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <label className="flex items-center gap-2 text-[13px] text-foreground">
            <Checkbox
              checked={settings?.data_shared ?? false}
              onCheckedChange={(checked) => {
                void updateSettings.mutateAsync({ data_shared: checked === true })
              }}
            />
            Partager mes données
          </label>

          <Button
            type="button"
            variant="outline"
            className="border-warning text-warning hover:bg-warning hover:text-accent-foreground"
            onClick={handleLogout}
          >
            Déconnexion
          </Button>
        </div>
      </header>

      <div className="mt-5 flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="active-deck">Mon deck personnel</Label>
          <Select
            value={activeDeckId ?? undefined}
            onValueChange={handleActiveDeckChange}
            disabled={!canEdit}
          >
            <SelectTrigger id="active-deck" className="w-64">
              <SelectValue placeholder="— aucun sélectionné —" />
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

        {canEdit && (
          <form
            className="ml-auto flex items-end gap-2"
            onSubmit={(event) => {
              void handleCreateDeck(event)
            }}
          >
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="new-deck-name">Nom du nouveau deck perso</Label>
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
              Créer
            </Button>
          </form>
        )}
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
