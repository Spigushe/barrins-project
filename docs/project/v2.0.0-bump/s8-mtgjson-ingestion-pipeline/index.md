# S8. MTGJSON card/set data pipeline

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` (new `Card`/`Set` models, `mtgjson` router/service) | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — added 2026-07-26 (see F8) | / |
| **Source** | Discovered while scoping S4; corrects a false assumption in S2/§1.6 | / |
| **Dependency** | D1 (playbook shape for the scheduled refresh) | Blocks S4. No longer blocks S2 — its deck-validation gate deferred to v3.0.0 (2026-07-27) |

---

## Context

`docs/content/back/barrins_api/auth_roles.md` describes a
`POST /mtgjson/import` route, public `sets`/`cards` read routes, and an
`admin`-gated import capability as if already built. **F8 verified this
is false**: zero Python files reference `mtgjson`, no `Card`/`Set` model
exists. This item is the real, from-scratch build that S4 (card images +
sorting) needs before it can start its MTG-data-dependent work. S2's
deck-validation gate originally needed this too, but was deferred to
v3.0.0 (2026-07-27, see `../s2-team-sharing/index.md`), so it no longer
blocks on this item for v2.0.0.

**Not previously scoped as its own item** — it surfaced only once S4 and
S2 were checked against actual code, not against `auth_roles.md`'s
description of them.

## Done statement

- `Card` and `Set` ORM models exist under `app/models/`, populated from
  MTGJSON's data (exact source file — `AllPrintings.json`,
  `AllPrices.json`, or both — needs confirming against MTGJSON's current
  schema during implementation, not assumed here).
- `POST /mtgjson/import` exists, `admin`-gated (`AdminUser`), matching
  `auth_roles.md`'s already-documented shape (`source`: which MTGJSON
  file, `force`: bool) — this part of the doc was directionally right,
  just not yet built.
- `GET /sets/`, `GET /sets/{code}`, `GET /sets/{code}/cards`,
  `GET /cards/{uuid}`, `GET /cards/by-name/{name}` exist, public
  (anonymous), matching `auth_roles.md`'s security matrix.
- Card records carry enough data for S4's needs: an image reference
  (or a derivable image URL — MTGJSON itself doesn't host images;
  needs a decision on an image source during implementation, e.g.
  Scryfall's image API keyed by the same card identity), type line,
  mana value, color identity, and mana cost.
- Multi-face cards store **per-face** type data (front/"face A" and
  back face separately), not just a single flattened type line — this
  is required by S4's "face A Land" rule, which cannot be evaluated
  from a single merged type string.
- A **scheduled refresh** exists (not just the admin-triggered manual
  route) — MTGJSON's own data updates periodically (new sets, price
  updates); a playbook-driven scheduled job keeps this from going
  stale, following D1's template and T8's scheduled-job precedent
  (Barrin's Scripture) as the closest existing pattern. Exact cadence
  and mechanism (VPS-hosted scheduler vs. CI-triggered) not decided
  here.

## Tasks

- [ ] Confirm MTGJSON's exact source file(s) and per-face schema shape
      against real MTGJSON data (don't guess field names from memory).
- [ ] Design `Card`/`Set` models, including per-face type storage.
- [ ] Implement `POST /mtgjson/import` per `auth_roles.md`'s already-
      documented shape (this part can be built as originally described).
- [ ] Implement `GET /sets/*`, `GET /cards/*` public read routes.
- [ ] Decide the card-image source (MTGJSON has no images; needs its own
      small escalation — a new external dependency/data source per
      Constitution §16.2/§4.7, not assumed here).
- [ ] Design and build the scheduled-refresh mechanism, coordinating
      with D1's playbook template.
- [ ] Update `auth_roles.md` (or let F8 handle it) once this lands, so
      the docs describe real behavior again.

## UAT (manual)

- [ ] Trigger `POST /mtgjson/import` on staging; confirm `sets`/`cards`
      tables populate and `GET /cards/by-name/{name}` returns real data.
- [ ] Confirm a multi-face card (e.g. a modal DFC) stores both faces'
      types separately, retrievable independently.
- [ ] Confirm the scheduled refresh runs without manual intervention and
      updates existing records (not just inserting new ones).

## Non-regression tests

- New `tests/test_mtgjson.py`: import idempotency (re-running doesn't
  duplicate rows), public-route reachability without auth, admin-gating
  on the import route (403 for non-admin).
- A test asserting a known multi-face fixture card's per-face type data
  round-trips correctly — this is the data S4's "face A Land" rule
  depends on, so it needs its own explicit regression coverage.
