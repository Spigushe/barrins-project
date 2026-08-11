# T4. Tolaria News BFF routes

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` | New `/bff/tolaria-news/...` namespace (corrected 2026-08-11 — see CLAUDE.md §12 amendment) |
| **Initial date** | 2026-08-11 | / |
| **Status** | ✅ Done (2026-08-11) — v1 route map implemented and tested; nginx rate limiter written, not yet exercised against a live server. See `docs/content/back/barrins_api/bff/tolaria_news.md` | / |
| **Source** | Request item 1 | / |
| **Dependency** | T2 (done) | Blocks T5 |

---

## Context

`docs/content/back/barrins_api/bff/tamiyo_scroll.md` already anticipates
this BFF existing, noting Tamiyo Scroll's routes "all require
`CurrentUser` ... unlike the Tolaria News BFF which is publicly
readable." That's the one concrete precedent to build from: Tolaria
News is a public tournament aggregator, so its reads need no
per-user authentication, unlike Tamiyo Scroll's personal-data routes.

**I7 resolved 2026-07-27 (§1.9), Option 4**: "public" (no per-user auth)
stays exactly that — these routes are **not** gated by caller identity
(no agent key, no CORS-as-boundary, no reverse-proxy flip). Instead,
access posture is CORS (§33, browser-only friction) plus **inbound
rate-limiting** as the real anti-abuse control, since "restricted to the
Tolaria News app" was explicitly decided as a soft goal, not a hard
boundary — the data is aggregated, already-public tournament results,
and the realistic harm is load/abuse, not confidentiality.

**Scope note (2026-08-11)**: a separate design handoff
(`docs/project/v2.0.0-bump/tolaria_news_handoff/`) sketches a much
larger product — archetype clustering (`/metagame`, `/archetypes`),
trends, forecasts, search. None of that is v1 scope here: archetype
data has no owner in `bs_*` yet — that's T6 ("Karn Tablets"), not
started, and T6's own implementation plan currently routes its output
to the S6 admin dashboard only, not to Tolaria News. Exposing
`/metagame`/`/archetypes` through this BFF is planned as **T4
iteration 2**, once T6/T8 ship, and requires amending T6's
consumption-surface decision to add Tolaria News as a second, public
consumer — not something to silently fold into this item's "done
statement." T4 v1 itself ships tournaments/decks/standings/decklist
detail only (see route map below).

**T4 iteration 2 — planned (2026-08-11), not yet built.** See
[ADR-13](../../../content/ops/architecture/decisions.md#adr-13-karn-tablets-output--data-flow-scope-and-consumption-surface)
for the full alternatives/trade-offs record. Scope: `/tournaments/{id}/bracket`
(`bs_rounds`/`bs_round_matches`, independent of Karn Tablets, no new
dependency), plus `/metagame`, `/archetypes`, `/trends` (Karn-Tablets-tied,
Duel-Commander-only, push-based — Karn Tablets pushes computed results into
new `barrins_api`-owned `kt_*` tables via `POST /internal/karn/ingest`; this
BFF reads those tables directly, same DB-only pattern as v1, no live call to
Karn Tablets on the read path). Tournament `location`, `/forecasts`, full
`/search`, and a card oracle/image proxy stay explicitly out of scope — no
design exists for them yet.

**Optional enhancement (2026-08-11) — Manatraders "rent this deck" link.**
For a deck displayed on Tolaria News, add a link to rent it on Manatraders
(MTGO card rental) — see
[T5's "Optional enhancement" section](../t5-tolaria-news-frontend/index.md#optional-enhancement-manatraders-rent-this-deck-link)
for the full cost/gain investigation. Manatraders' single-card and
whole-deck rental links are **public,
unauthenticated deep-links** — `https://www.manatraders.com/load-deck?
c=<qty> <name>||...` — no API key, no server-to-server call, no secret to
hold. `DeckDetail` (`GET /bff/tolaria-news/decks/{id}`) already computes
everything the link needs (`mainboard`, `commanders`). **Backend provides
the finished URL** in that response (a plain string field, computed
inline — Constitution §4.1: the frontend renders a link, it doesn't build
one), not left to T5 to assemble client-side. **Optional, not scheduled**
— no dependency on Karn Tablets or T4 iteration 2's other routes; can land
independently, in v1's own follow-up or alongside iteration 2, whichever
the user picks when prioritizing.

## Done statement (once T2 lands)

- A new router package `app/api/tolaria_news/`, following the same
  aggregator + one-file-per-resource pattern as
  `app/api/tamiyo_scroll/` (per `bff/tamiyo_scroll.md`'s own
  "Target architecture" section, which explicitly says future BFFs
  should follow the identical pattern).
- Every route is a **read**, requires no `CurrentUser` (no per-user
  auth), and returns data computed server-side (Constitution §4.1) —
  no aggregation logic duplicated in the future frontend.
- Every route is covered by an inbound rate limiter (policy TBD — see
  Tasks below) — the only access restriction these routes carry, per
  §1.9's Option 4.
- Mounted in `main.py` alongside `general_router`/`tamiyo_scroll_router`.

## Tasks

- [x] Design the route map (tournaments list/detail, decks, standings,
      decklist detail with derived commander/color-identity data) —
      see `docs/content/back/barrins_api/bff/tolaria_news.md`.
- [x] Implement `app/services/tolaria_news/` (`pagination.py`,
      `tournaments.py`, `decks.py` — the latter includes the
      `mj_cards` join + commander derivation).
- [x] Add `app/schemas/responses_tolaria_news.py` (`Envelope`/`Meta`/
      `Page` + response DTOs). No separate request-schema file — every
      route is a `GET` with plain query params, no POST/PUT body exists
      in this v1 BFF.
- [x] Mount the router in `main.py`.
- [x] **Define the rate-limit policy**: nginx `limit_req`, per-IP,
      scoped to `/bff/tolaria-news` only (not API-wide — Tamiyo Scroll
      stays JWT-gated, unaffected). `rate=20r/s`, `burst=80 nodelay`,
      `limit_req_status 429` — a deliberately generous starting default
      (public data, no per-request cost, real target is bot/scraper
      abuse not normal browsing), to be retuned once T5 exists and
      real per-page request volume is measurable. See
      `docs/content/back/barrins_api/bff/tolaria_news.md`.
- [x] Implement the limiter: a new, generic
      `backend_website_rate_limited_paths` role variable
      (`{path, zone, rate, burst}`) drives both
      `templates/ratelimit.conf.j2` (conf.d, the `limit_req_zone`
      directive — must live in nginx's `http` context, not inside a
      `server` block) and a matching `location` block in
      `https.conf.j2`. Not hardcoded into the role, since
      `backend_website` is shared with any future backend app;
      `barrins_api.yml` sets the concrete Tolaria News entry
      (`rate=20r/s`, `burst=80`). Nginx-level, not in-process —
      `barrins_api` runs multiple workers, an in-process limiter would
      multiply the effective limit by worker count.

## UAT (manual)

- [x] Every new route returns real data reflecting T2/T3's ingested
      tournaments, with no `Authorization` header sent — verified by
      `tests/tolaria_news/` against real-shaped fixture data (real
      staging exercise still pending an actual deploy).
- [x] Confirm no route accidentally requires `CurrentUser` (a copy-paste
      mistake from the Tamiyo Scroll router would break the "public"
      requirement silently) —
      `TestNoAuthRequired::test_every_route_ignores_missing_authorization`.
- [ ] Exceed the configured rate limit against a test client; confirm a
      `429` rather than an unbounded pass-through or an opaque `500`.
      **Not yet exercised** — needs the nginx config actually deployed
      (`ops/my-server/barrins_api.yml`) and a live client hitting it;
      not something a `pytest` suite against the FastAPI app directly
      can cover (the limiter lives entirely at the nginx layer).

## Non-regression tests

- `tests/tolaria_news/` (14 tests): `test_tournaments.py` (list
  filters/pagination/cursor validation, detail counts, decks,
  standings ordering), `test_decks.py` (card resolution against
  `mj_cards`, commander derivation from the `sideboard` board on
  Duel Commander decks, unresolved-name fallback, non-Commander
  format has no commanders, 404s).
- `TestNoAuthRequired` explicitly asserts every mounted route is
  reachable with no `Authorization` header sent.
- The rate limiter has **no automated test** — it's nginx
  configuration, not application code; covered by the manual UAT
  step above instead once deployed.
