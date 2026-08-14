# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [2.0.0-alpha] - 2026-08-14

### Added

- Real React 19 + Vite + TypeScript app (T5), replacing the placeholder.
  Public, read-only, no auth — calls only `barrins_api`'s Tolaria News BFF
  (`/bff/tolaria-news/*`, T4): tournament list/detail (Decks/Standings/
  Bracket tabs) and decklist detail with derived commander(s).
- `/metagame`, `/archetypes`, `/trends` prepared ahead of their backend
  (T4 iteration 2 / T6 "Karn Tablets", not started), hidden behind
  `VITE_FEATURE_KARN_TABLETS` (default off).
- Visual design adapted from the design handoff (Midnight palette, EB
  Garamond/Geist/JetBrains Mono, teal accent, icon/sigil, Nav + BottomRail
  shell, Eyebrow component) — restyle only, not the handoff's larger
  speculative page set.
- Deployable through the existing `ops/my-server/tolaria_news.yml`
  playbook with no playbook changes.

## [1.0.0] "WorldWake" - 2026-07-24

Nothing yet.
