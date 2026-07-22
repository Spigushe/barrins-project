<!-- cSpell:ignore JWKS tolaria -->
# Tolaria News — Backend Architecture

> **Status**: ⬜ Planned — documentation only, nothing implemented yet.
> **Front**: under specification (see `apps/tolaria_news/`, currently a
> placeholder). This document covers backend/data architecture only.

---

## 1. Two backend pieces, not one

`tolaria_news` (Duel Commander tournament aggregator) is served by two
separate backend pieces:

1. **BFF routes inside `apps/barrins_api`** — request/response endpoints for
   the `tolaria_news` frontend, same pattern as `tamiyo_scroll`'s
   `ts_router` (see [Barrin's Identity platform.md
   §10](../barrins_identity/platform.md#10-tolaria-news)). Neither these
   routes nor the underlying tournament/decklist data
   pipelines exist yet in this monorepo's `apps/barrins_api` — grep confirms
   no `tolaria` path under `apps/barrins_api/app/api` today.
2. **A companion periodic-calculation backend** (new app, name not yet
   decided — proposed working name `apps/karn_tablets/`, to confirm before
   scaffolding) — described below.

`barrins_api` remains the single source of truth for `tolaria_news`'s data:
the calculation backend reads from it and writes its results back into it,
so the frontend never has to reconcile two separate data sources.

---

## 2. Companion calculation backend

### Purpose

Runs periodic (not on-demand) machine-learning/analytics calculations to
supplement `tolaria_news` — e.g. metagame/archetype trend analysis over
tournament data. Not request-driven: no user-facing endpoint triggers a
calculation synchronously.

### Data flow — read + write-back

```text
barrins_api  <---- periodic read (tournament/decklist data) ---  karn_tablets
     ^                                                              |
     |----------------- write-back (computed results) --------------
```

- The calculation backend periodically **reads** source data from
  `barrins_api` through its API (not direct DB access — consistent with
  constitution §4.3, API contracts as first-class objects; never expose
  internal DB models directly).
- It **writes its computed results back** into `barrins_api` through its
  API, so `tolaria_news` keeps a single data source (`barrins_api`) for
  everything, including ML-derived data.
- `barrins_api` therefore needs both a read surface (tournament/decklist
  data, once that pipeline exists) and a write surface (accepting computed
  results) for this backend to call.

### Open items (not yet decided — do not implement against guesses)

| # | Item | Status |
| - | ---- | ------ |
| ML-01 | Final app name and location (proposed: `apps/karn_tablets/`) | To confirm before scaffolding |
| ML-02 | Authentication mechanism between this backend and `barrins_api` | Not yet decided by the user. Natural candidate: a `barrins-identity` service account (`client_credentials`, see [Barrin's Identity platform.md §8](../barrins_identity/platform.md#8-routes)) issuing a scoped token (e.g. `karn_tablets:read`, `karn_tablets:write`) — but this must be confirmed, not assumed, before Phase 9/11 of that plan accounts for it |
| ML-03 | Calculation schedule/trigger (cron? worker queue? interval?) | Not yet decided |
| ML-04 | Shape of the write-back payload (which tables/DTOs in `barrins_api` receive computed results) | Not yet decided — depends on ML-01 and on the tournament/decklist data model existing in `barrins_api`, which it does not yet |
| ML-05 | Underlying tournament/decklist/card data pipeline in `barrins_api` | Does not exist yet in this monorepo (no decklist/mtgjson import modules under `apps/barrins_api/app` today) — a precondition for both the BFF routes (§1.1) and this calculation backend, not addressed by this document |

### Why this validates the `barrins-identity` service-account design

[Barrin's Identity's plan](../barrins_identity/platform.md) proposes a
`client_credentials`-style service-account flow specifically for
machine-to-machine calls between backends, in anticipation of a second
backend appearing. This calculation backend is that second backend: once
ML-01/ML-02 are confirmed, it becomes a second concrete consumer of that
flow (alongside `barrins_api` verifying its own callers), which is the
scenario the RS256/JWKS design was built for.

---

## 3. Tests-first note

Per constitution §16.4, before either the BFF routes (§1.1) or the
calculation backend (§2) are implemented, a dedicated test plan for each
must be written and confirmed — none exists yet, since the open items above
(ML-01 through ML-05) are prerequisites to writing one meaningfully.
