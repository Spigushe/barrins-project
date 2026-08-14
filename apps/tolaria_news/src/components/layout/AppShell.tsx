import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { karnTabletsEnabled } from '@/lib/featureFlags'
import { cn } from '@/lib/utils'

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'border-b-[0.5px] border-transparent pb-1 font-sans text-[13.5px] font-medium tracking-[0.01em] transition-colors duration-150',
          isActive
            ? 'border-accent text-foreground'
            : 'text-muted-foreground hover:text-foreground',
        )
      }
    >
      {label}
    </NavLink>
  )
}

/**
 * Nav + BottomRail shell, per the design handoff's "Shared layout"
 * (PAGES.md). Restyle only — no sign-in, no ⌘K search: neither exists on
 * this public, unauthenticated app (T4's BFF has no `CurrentUser` at all).
 * BottomRail is a normal footer rather than fixed-bottom, a deliberate
 * adaptation for a data-table-heavy app where a fixed band would obscure
 * table rows on scroll.
 */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-svh flex-col">
      <header className="sticky top-0 z-10 border-b-[0.5px] border-border bg-background/85 backdrop-blur">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-6 py-[22px] md:px-14">
          <Link to="/" className="flex items-center gap-2.5">
            <img src="/favicon.svg" alt="" className="size-7 rounded-[7px]" />
            <span className="font-serif text-lg italic text-foreground">
              Tolaria News
            </span>
          </Link>
          <nav className="flex items-center gap-6">
            <NavItem to="/tournaments" label="Tournaments" />
            {karnTabletsEnabled && (
              <>
                <NavItem to="/metagame" label="Metagame" />
                <NavItem to="/archetypes" label="Archetypes" />
                <NavItem to="/trends" label="Trends" />
              </>
            )}
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1440px] flex-1 px-6 py-8 md:px-14">
        {children}
      </main>

      <footer className="border-t-[0.5px] border-border">
        <div className="mx-auto flex max-w-[1440px] flex-col gap-1 px-6 py-3 font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted-foreground sm:flex-row sm:items-center sm:justify-between md:px-14">
          <span>Duel Commander · Barrin&rsquo;s Project</span>
          <span>Public tournament data</span>
          <span>Read-only</span>
        </div>
      </footer>
    </div>
  )
}
