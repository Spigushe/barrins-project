# Barrin's Codex

A small ecosystem of tools for competitive Magic: The Gathering players —
starting with **Tamiyo Scroll**, a Duel Commander testing tracker built
for the grind of tournament prep: keeping a personal decklist, logging
BO3 test games against a roster of opponent decks, and seeing which
matchups are actually winning before the event.

## What's in it, today

- **Personal decks & decklists** — track one or more decks, each with a
  version history. Import a decklist straight from a public
  [Moxfield](https://www.moxfield.com/) link, or paste it as text.
- **Opponent roster & expected metagame** — keep a tiered list of the
  decks you expect to face, with Top 8 counts and metagame presence.
- **BO3 match log** — record games one by one (on the play/draw, result
  per game, opening hand, turning point, notes), against a personal deck
  and an opponent deck picked or created on the spot.
- **Archetype & matchup stats** — win rates by archetype and by specific
  matchup, computed from your own logged games.
- **Card-test feedback** — rate individual cards from your testing and
  see that feedback annotated directly onto your decklist.

Everything above lives behind a shared Barrin's account (one login
across every app in this ecosystem going forward, not a per-app one).

## Status

Pre-1.0 — the tracker above is fully built and in daily personal use;
this repository is in the final stretch of preparing its first tagged,
production release. Nothing is publicly live yet, so there isn't a
public link to share here just yet. Expect the feature set to keep
growing after that (a shared identity service for future apps,
ML-assisted deck analysis, and more are on the roadmap).

## Under the hood

This is a monorepo: a FastAPI backend (`apps/barrins_api`) and a
React/TypeScript frontend (`apps/tamiyo_scroll`), deployed independently.
For architecture, API contracts, and day-to-day development docs, see
the `apps/*/README.md` files in this repo and `docs/content/`.
