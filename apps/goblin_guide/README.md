# Goblin Guide: Barrin's Identity frontend

Placeholder — the login and account-management UI for Barrin's Identity
(`apps/barrins_identity/`). Nothing is implemented yet.

> **Status**: ⬜ Planned — documentation only. See the Bootstrap doc
> (linked below) for the scope questions still open, and the Barrin's
> Identity Integration Contract for the backend surface it will consume.

## What it will own

- Login, silent token refresh, and logout.
- Signup + email-verification screens.
- Forgot-password / reset-password screens.
- Account settings (display name, email change, delete account).
- Service-account management for administrators.

## What it will never own

Business or authorization rules. Goblin Guide renders the flows Barrin's
Identity defines and stores authentication *state* only — it never
decides permissions (constitution §4.1, §13.5).

## Not yet decided

- Stack (ecosystem default is React 19 + Vite + TypeScript per
  constitution §14, unconfirmed for this app).
- Standalone application vs. an embeddable widget consumed by
  `tamiyo_scroll` / `tolaria_news` for their own login.
- Which Barrin's Identity routes it consumes first.

Do not implement against assumptions here — confirm scope first
(constitution §16.2).
