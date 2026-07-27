# T4. Tolaria News BFF routes

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` | New `/api/v1/tolaria-news/...` namespace |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — depends on T2. I7 (§1.9) resolved 2026-07-27 | / |
| **Source** | Request item 1 | / |
| **Dependency** | T2 | Blocks T5 |

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

- [ ] Design the route map (tournaments list/detail, decks, standings —
      exact shape depends on T2's final schema).
- [ ] Implement `app/services/tolaria_news/` (pure, tested aggregation
      functions, mirroring `services/tamiyo_scroll/stats.py`'s pattern).
- [ ] Add `app/schemas/tolaria_news.py` /
      `responses_tolaria_news.py`.
- [ ] Mount the router in `main.py`.
- [ ] **Define the rate-limit policy** (§1.9's residual-risk list, not
      yet settled): key (per-IP? per-something-else?), threshold, time
      window, `429` response shape, and whether the limit is scoped to
      these public BFF routes specifically or applied API-wide. `barrins_
      api` has **no inbound rate-limiting anywhere today** (only the
      Moxfield client's *outbound* limiter, and `POST /auth/token`'s
      inbound limiting is separately tracked as open item P-03 in
      `auth_roles.md`) — this is net-new infrastructure, not a config
      toggle. See `../consitution-amendment.md` Proposal 6.
- [ ] Implement the limiter at the layer the policy calls for — nginx
      (`limit_req`/`limit_conn`, §29, correct by construction across
      multiple `barrins_api` workers) if coarse per-IP is enough, or a
      shared-state (Redis/DB) limiter in `barrins_api` if finer
      per-client control is later needed. A naïve in-process limiter
      would multiply its effective limit by worker count — don't ship
      that.

## UAT (manual)

- [ ] Every new route returns real data reflecting T2/T3's ingested
      tournaments, with no `Authorization` header sent.
- [ ] Confirm no route accidentally requires `CurrentUser` (a copy-paste
      mistake from the Tamiyo Scroll router would break the "public"
      requirement silently).
- [ ] Exceed the configured rate limit against a test client; confirm a
      `429` (or the decided response) rather than an unbounded pass-
      through or an opaque `500`.

## Non-regression tests

- New `tests/tolaria_news/` module, same structure as
  `tests/tamiyo_scroll/`.
- A test explicitly asserting every mounted Tolaria News route is
  reachable with no `Authorization` header.
- A test covering the rate limiter: requests under the threshold pass,
  requests over it are rejected, and (if nginx-enforced) at minimum a
  smoke test confirming the vhost config is applied.
