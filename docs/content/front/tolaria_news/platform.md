<!-- cSpell:ignore JWKS tolaria -->
# Tolaria News — Frontend Architecture

> **Status**: ⬜ Planned — documentation only, nothing implemented yet.
> **App**: `apps/tolaria_news/`, currently a placeholder. Duel Commander
> tournament aggregator frontend.

---

## 1. What Tolaria News depends on

Tolaria News is a frontend application. Per constitution §4.1/§4.2, it
renders data and never computes or decides business rules itself. It has
two direct backend dependencies:

```text
tolaria_news (frontend)
  |
  +--> barrins_api       tournament/report data (BFF routes, not yet built)
  |
  +--> barrins_identity  authentication (human login, refresh)
```

It does **not** talk to `karn_tablets` directly — that backend only exists
to feed computed data into `barrins_api`, see §3.

### 1.1 `barrins_api` (BFF)

Same BFF pattern as `tamiyo_scroll`'s `ts_router` (constitution §12):
dedicated endpoints, proposed under `/api/v1/tolaria-news/`, inside
`apps/barrins_api`, aggregating/adapting domain data for this frontend's
needs. Neither these routes nor the underlying tournament/decklist data
pipeline exist yet — grep confirms no `tolaria` path under
`apps/barrins_api/app/api` today.

`barrins_api` remains the single source of truth for all of `tolaria_news`'s
data, including ML-derived data (§3) — the frontend never reconciles two
separate data sources.

### 1.2 `barrins_identity` (auth)

Per [Barrin's Identity platform.md
§5](../../back/barrins_identity/platform.md#5-target-architecture),
`tolaria_news` is a listed future consumer of the human login/refresh flow
(`POST /token`, `POST /refresh`) directly against `barrins_identity` — the
same pattern `tamiyo_scroll` uses against its own backend today and will use
against `barrins_identity` once its cutover lands.

Open question, not yet resolved (see [Goblin Guide
bootstrap.md](../goblin_guide/bootstrap.md)): whether `tolaria_news`
implements its own login UI calling `barrins_identity` directly, or embeds
`goblin_guide` as a shared widget. Do not implement against either
assumption before this is confirmed.

Whichever shape is chosen, the BFF routes in §1.1 must accept a
`barrins_identity`-issued access token the same way `barrins_api` verifies
any other consumer's token (constitution §13.5 — authorization decisions
stay backend-side; the frontend only stores and forwards the token).

---

## 2. Frontend stack

Not yet confirmed for this app specifically. The ecosystem default
(constitution §14.2) is React 19 + TypeScript + Vite + React Router +
TanStack Query + Zod + TailwindCSS + shadcn/ui, same as `tamiyo_scroll` —
but this hasn't been validated for `tolaria_news`, whose `apps/tolaria_news/`
directory is currently a placeholder.

---

## 3. Backend-side detail: `karn_tablets` (informational only)

This section is backend context that `tolaria_news` (the frontend) never
calls directly — kept here because it explains where some of the data
returned by the `barrins_api` BFF (§1.1) comes from.

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
| ML-02 | Authentication mechanism between this backend and `barrins_api` | Not yet decided by the user. Natural candidate: a `barrins-identity` service account (`client_credentials`, see [Barrin's Identity platform.md §8](../../back/barrins_identity/platform.md#8-routes)) issuing a scoped token (e.g. `karn_tablets:read`, `karn_tablets:write`) — but this must be confirmed, not assumed |
| ML-03 | Calculation schedule/trigger (cron? worker queue? interval?) | Not yet decided |
| ML-04 | Shape of the write-back payload (which tables/DTOs in `barrins_api` receive computed results) | Not yet decided — depends on ML-01 and on the tournament/decklist data model existing in `barrins_api`, which it does not yet |
| ML-05 | Underlying tournament/decklist/card data pipeline in `barrins_api` | Does not exist yet in this monorepo (no decklist/mtgjson import modules under `apps/barrins_api/app` today) — a precondition for both the BFF routes (§1.1) and this calculation backend, not addressed by this document |

### Why this validates the `barrins-identity` service-account design

[Barrin's Identity's plan](../../back/barrins_identity/platform.md) proposes
a `client_credentials`-style service-account flow specifically for
machine-to-machine calls between backends, in anticipation of a second
backend appearing. This calculation backend is that second backend: once
ML-01/ML-02 are confirmed, it becomes a second concrete consumer of that
flow (alongside `barrins_api` verifying its own callers), which is the
scenario the RS256/JWKS design was built for.

---

## 4. Tests-first note

Per constitution §16.4, before the BFF routes (§1.1), the auth integration
(§1.2), or the calculation backend (§3) are implemented, a dedicated test
plan for each must be written and confirmed — none exists yet, since the
open items above (ML-01 through ML-05, plus the login-UI-vs-widget question
in §1.2) are prerequisites to writing one meaningfully.
