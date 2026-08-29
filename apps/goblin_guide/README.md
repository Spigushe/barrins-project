# Goblin Guide: Barrin's Identity frontend

Placeholder — the login and account-management frontend for Barrin's
Identity (`apps/barrins_identity/`). Nothing is implemented yet.

> **Status**: ⬜ Planned — documentation only. Shape settled 2026-08-29
> (ADR-17): a **shared frontend library** each Barrin's frontend mounts,
> plus a thin standalone shell. See the Bootstrap doc (linked below) and
> the Barrin's Identity Integration Contract for the backend surface it
> consumes.

## Shape

- A shared library — screens (login, signup + verify, password reset,
  account settings, delete account, admin service-account management),
  hooks, and client-side token handling — consumed by `tamiyo_scroll`,
  `tolaria_news` and future frontends. Ecosystem-default stack
  (React 19 + TypeScript + Tailwind + shadcn/ui), built in Vite library
  mode; React Router and TanStack Query are peer dependencies the host
  provides.
- A thin standalone shell app that serves a canonical
  `goblin.barrins-codex.org` and gives the T9 Jupyter reverse-proxy a
  login page to redirect to.

## What it will never own

Business or authorization rules. Goblin Guide renders the flows Barrin's
Identity defines and stores authentication *state* only — it never
decides permissions (constitution §4.1, §13.5).

## Still open

- Delivery order (login first, then signup, then reset, then settings) —
  proposed, not fixed.
- Refresh-token storage: in-memory by default, or an `HttpOnly` cookie via
  a host BFF (a pluggable token store).
- Page layout / UX specifics.
