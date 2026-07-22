<!-- cSpell:ignore JWKS -->
# Goblin Guide — Bootstrap

> **Status**: ⬜ Placeholder — not yet specified.

## Purpose

Goblin Guide is the planned frontend (login / account management UI) for
Barrin's Identity (`apps/barrins_identity/`), the JWT RS256 + JWKS identity
backend described in
[Barrin's Identity platform.md](../../back/barrins_identity/platform.md).

## Scope (not yet defined)

Nothing about Goblin Guide is specified yet, including:

- stack (the ecosystem default is React 19 + Vite + TypeScript per
  constitution §14, but this hasn't been confirmed for this app
  specifically);
- whether it is a standalone application or an embeddable widget consumed
  by `tamiyo_scroll` and `tolaria_news` for their own login flows;
- its pages and user flows (login, refresh handling, account settings,
  service-account management for admins, etc.);
- which of Barrin's Identity's routes (see
  [platform.md §8](../../back/barrins_identity/platform.md#8-routes)) it
  consumes first.

This page exists to record the name and its relationship to
`barrins_identity` — do not implement against assumptions here; confirm
scope before starting, per constitution §16.2.
