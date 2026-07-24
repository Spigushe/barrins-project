import type { ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useCurrentUser, useLogout } from '@/hooks/useAuth'
import { useMySettings } from '@/hooks/useSettings'
import { ActiveDeckContext } from '@/contexts/active-deck-context'
import { PersonalDeckSelector } from '@/components/layout/PersonalDeckSelector'
import { SharingControls } from '@/components/layout/SharingControls'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const TABS = [
  { to: '/app/bo3-tracker', label: 'BO3 Tracking' },
  { to: '/app/metagame', label: 'Metagame' },
  { to: '/app/decklist', label: 'My decklist' },
]

export function AppShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const { data: settings } = useMySettings()
  const { data: currentUser } = useCurrentUser()
  const logout = useLogout()

  // Sharing/read-only viewing is disabled for v1.0.0 (SharingControls),
  // so editing one's own data is always allowed here.
  const canEdit = true
  const activeDeckId = settings?.active_personal_deck_id ?? null

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

          {currentUser && (
            <span className="text-sm text-muted-foreground">
              Welcome, {currentUser.display_name ?? currentUser.email}
            </span>
          )}

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
        <PersonalDeckSelector />
      </div>

      {activeDeckId !== null && (
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
      )}

      <ActiveDeckContext.Provider value={{ activeDeckId, canEdit }}>
        <main className="mt-7 flex flex-col gap-7">{children}</main>
      </ActiveDeckContext.Provider>
    </div>
  )
}
