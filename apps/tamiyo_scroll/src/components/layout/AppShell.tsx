import { type ReactNode, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useCurrentUser, useLogout } from '@barrins/goblin-guide'
import { useMySettings } from '@/hooks/useSettings'
import { ActiveDeckContext } from '@/contexts/active-deck-context'
import { AccountSettingsDialog } from '@/components/layout/AccountSettingsDialog'
import { PersonalDeckSelector } from '@/components/layout/PersonalDeckSelector'
import { TeamDeckSelector } from '@/components/layout/TeamDeckSelector'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const TABS = [
  { to: '/app/tracker', label: 'BO3 Tracking' },
  { to: '/app/metagame', label: 'Metagame' },
  { to: '/app/decklist', label: 'My decklist' },
  { to: '/app/sessions', label: 'Sessions' },
  { to: '/app/team', label: 'Teams' },
]

export function AppShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const { data: settings } = useMySettings()
  const { data: currentUser } = useCurrentUser()
  const logout = useLogout()
  const [settingsOpen, setSettingsOpen] = useState(false)

  // No more "view as another user" mode (retired 2026-07-30) — shared
  // data is merged directly, read-only per-row (`match.is_readonly` /
  // `metaDeck.is_readonly`), not gated by a page-wide flag. Always true;
  // kept for ActiveDeckContext's existing shape rather than reworking it.
  const canEdit = true
  const activeDeckId = settings?.active_personal_deck_id ?? null

  async function handleLogout() {
    await logout.mutateAsync()
    navigate('/login')
  }

  return (
    <div className="mx-auto max-w-[1400px] px-8 pt-7 pb-20">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <img src="/favicon.svg" alt="" className="size-10 shrink-0" />
          <div>
            <h1 className="text-[22px] font-extrabold text-foreground">Tamiyo Scroll</h1>
            <p className="text-[13px] text-muted-foreground">
              Competitive · Test tracking · Duel Commander
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {currentUser && (
            <span className="text-sm text-muted-foreground">
              Welcome, {currentUser.display_name ?? currentUser.email}
            </span>
          )}

          {currentUser?.role === 'admin' && (
            <Button type="button" variant="outline" asChild>
              <Link to="/app/admin/metrics">Admin metrics</Link>
            </Button>
          )}

          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setSettingsOpen(true)
            }}
          >
            Settings
          </Button>

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

      <AccountSettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />

      <div className="mt-5 flex flex-wrap items-end gap-3">
        <PersonalDeckSelector />
        <TeamDeckSelector />
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
        <main className="mt-7 flex flex-col gap-7">
          {activeDeckId !== null ? (
            children
          ) : (
            <p className="text-sm text-muted-foreground">
              Create or select a personal deck above to get started.
            </p>
          )}
        </main>
      </ActiveDeckContext.Provider>
    </div>
  )
}
