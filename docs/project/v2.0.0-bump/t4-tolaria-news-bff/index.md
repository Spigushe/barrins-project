# T4. Tolaria News BFF routes

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` | New `/api/v1/tolaria-news/...` namespace |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — depends on T2 | / |
| **Source** | Request item 1 | / |
| **Dependency** | T2 | Blocks T5 |

---

## Context

`docs/content/back/barrins_api/bff/tamiyo_scroll.md` already anticipates
this BFF existing, noting Tamiyo Scroll's routes "all require
`CurrentUser` ... unlike the Tolaria News BFF which is publicly
readable." That's the one concrete precedent to build from: Tolaria
News is a public tournament aggregator, so its reads need no
authentication, unlike Tamiyo Scroll's personal-data routes.

## Done statement (once T2 lands)

- A new router package `app/api/tolaria_news/`, following the same
  aggregator + one-file-per-resource pattern as
  `app/api/tamiyo_scroll/` (per `bff/tamiyo_scroll.md`'s own
  "Target architecture" section, which explicitly says future BFFs
  should follow the identical pattern).
- Every route is a **read**, requires no `CurrentUser` dependency
  (public), and returns data computed server-side (Constitution §4.1) —
  no aggregation logic duplicated in the future frontend.
- Mounted in `main.py` alongside `general_router`/`tamiyo_scroll_router`.

## Tasks

- [ ] Design the route map (tournaments list/detail, decks, standings —
      exact shape depends on T2's final schema).
- [ ] Implement `app/services/tolaria_news/` (pure, tested aggregation
      functions, mirroring `services/tamiyo_scroll/stats.py`'s pattern).
- [ ] Add `app/schemas/tolaria_news.py` /
      `responses_tolaria_news.py`.
- [ ] Mount the router in `main.py`.

## UAT (manual)

- [ ] Every new route returns real data reflecting T2/T3's ingested
      tournaments, with no authentication header sent.
- [ ] Confirm no route accidentally requires `CurrentUser` (a copy-paste
      mistake from the Tamiyo Scroll router would break the "public"
      requirement silently).

## Non-regression tests

- New `tests/tolaria_news/` module, same structure as
  `tests/tamiyo_scroll/`.
- A test explicitly asserting every mounted Tolaria News route is
  reachable with no `Authorization` header.
