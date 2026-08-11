<!-- cSpell:ignore scryfall mtgtop keyset nodelay -->
# Implementation Plan — Tolaria News BFF

| | | Comment |
| --- | --- | --- |
| **Target** | `barrins-project/barrins_api` | Namespace `/bff/tolaria-news/` (Constitution §12) |
| **Initial date** | 2026-08-11 | / |
| **Status** | ✅ Implemented (2026-08-11) | Frontend (`apps/tolaria_news`, T5) not built yet |
| **Source** | `docs/project/v2.0.0-bump/t4-tolaria-news-bff/index.md` (T4) | Constitution §12 anticipates this BFF; I7 (§1.9) decided its access model |
| **Dependency** | T2 (`bs_*` schema, done), T3 (ingestion, done), S8 (MTGJSON, done) | Blocks T5 |

---

## Objective

Expose the `bs_*` scraped-tournament domain (T2/T3 — see
`docs/project/v2.0.0-bump/t2-scraped-tournament-schema/` for the domain
model itself, internal release tracking, not part of the docs site;
this page doesn't re-describe it) as a **public, read-only** BFF under
`/bff/tolaria-news/`, following the same
router/service package pattern as `bff/tamiyo_scroll.md`'s "Target
architecture" — which explicitly names Tolaria News as the next
consumer of that pattern.

Two decisions inherited from T4's planning, not re-litigated here:

- **I7 (resolved 2026-07-27, Option 4)**: no per-user auth on these
  routes (no `CurrentUser`). Access posture is CORS (§33) plus inbound
  rate-limiting as the real anti-abuse control — the data is
  already-public tournament results, the realistic harm is load/abuse,
  not confidentiality.
- **Route prefix**: `/bff/tolaria-news`, matching the real Tamiyo Scroll
  prefix `/bff/tamiyo-scroll` — CLAUDE.md §12 previously documented
  `/api/v1/<app>/` for this namespace, which never matched the shipped
  code; both the constitution and this page use the corrected form.

### Response envelope (deliberate divergence from Tamiyo Scroll)

Every 2xx response is wrapped:

```jsonc
{
  "data": { /* endpoint-specific */ },
  "meta": {
    "generated_at": "2026-08-11T14:03:00Z",
    "source_synced_at": "2026-08-11T13:51:00Z"
  },
  "page": { "next_cursor": "…", "limit": 20 }   // list endpoints only
}
```

Tamiyo Scroll's BFF returns bare data with no wrapper. Tolaria News
diverges on purpose: it's public/cacheable data where "how stale is
this" (`source_synced_at`, the most recent `bs_tournaments.created_at`
— a freshness proxy, not a true last-sweep-run log, since no such
tracking table exists yet) is a user-visible concern Tamiyo Scroll's
personal data doesn't have. Errors are **not** given a bespoke
envelope — `barrins_api` already has one global, uniform error handler
(`app/core/error_handlers.py`) used by every router in the app; adding
a second, different error shape just for this BFF would fragment that
consistency for no real benefit. A `404`/`400` from these routes looks
exactly like a `404`/`400` anywhere else in the API.

Pagination is cursor-based (`?cursor=&limit=`), not offset/limit —
keyset pagination over `(sort_key, id)`, so a page stays stable while
new tournaments keep landing underneath an in-progress scan (see
`app/services/tolaria_news/pagination.py`). No offset/limit convention
exists elsewhere in this codebase to stay consistent with, so this was
free ground.

---

## Route map (v1)

| Method | Route | Notes |
| --- | --- | --- |
| `GET` | `/bff/tolaria-news/tournaments` | List. Filters: `source` (`mtgo`/`mtgtop8`), `format`, `date_from`/`date_to`. `cursor`/`limit` (default 20, max 50) |
| `GET` | `/bff/tolaria-news/tournaments/{id}` | Detail: tournament fields + `deck_count`/`standing_count` |
| `GET` | `/bff/tolaria-news/tournaments/{id}/decks` | Decks entered (`bs_decks`), `cursor`/`limit` |
| `GET` | `/bff/tolaria-news/tournaments/{id}/standings` | Standings (`bs_standings`, ordered by `rank`), `cursor`/`limit` |
| `GET` | `/bff/tolaria-news/tournaments/{id}/bracket` | Elimination bracket (`bs_rounds`/`bs_round_matches`), rounds + nested matches in scrape order. No pagination (small dataset); empty list for Swiss-only tournaments |
| `GET` | `/bff/tolaria-news/decks/{id}` | Deck detail: full decklist + derived commander(s) |

No route accepts or requires `CurrentUser` — covered by an explicit
test (`tests/tolaria_news/test_tournaments.py::TestNoAuthRequired`)
guarding against a copy-paste of Tamiyo Scroll's router silently
reintroducing auth.

Deliberately **not** in v1 (see "Deferred scope" below):
`/metagame`, `/archetypes`, `/trends`, `/forecasts`, `/search`, a card
oracle-text/image proxy, and tournament `location`. Bracket data
(`bs_rounds`/`bs_round_matches`) **is** in v1 (`/tournaments/{id}/bracket`,
added 2026-08-11 — see [ADR-13](../../../ops/architecture/decisions.md#adr-13-karn-tablets-output--data-flow-scope-and-consumption-surface)).

### Commander + card data (`/decks/{id}`)

`bs_deck_cards` (T2) stores raw `card_name` strings with no FK to
`mj_cards` (S8's MTGJSON import). `app/services/tolaria_news/decks.py`
resolves each name via `app.services.scripture.card_resolver` — the
same resolver T3's ingestion route already uses to validate scraped
names, reused rather than re-implemented (Constitution §4.2) — then
batch-joins the resolved names against `mj_cards` for `mana_value`
(cmc), `type_line`, `scryfall_id`, and `color_identity`. An unresolved
name falls back to the raw string with no card metadata, rather than
dropping the line.

**Commander derivation**: confirmed against real fixtures (both MTGO
and MTGTop8, `apps/barrins_scripture/tests/fixtures/`) that for
Duel Commander tournaments (`bs_tournaments.format == "Duel Commander"`
— matches `barrins_scripture.schemas.formats.Formats.DUEL_COMMANDER`'s
value, not imported cross-app on purpose), the `sideboard` board of
`bs_deck_cards` holds exactly the commander(s): one card solo, two for
a partner pair. Commander has no traditional sideboard zone, so that's
all that ever lands there. Non-Commander-format decks get an empty
`commanders` list — the field only means something for this one format.

When a resolved card name matches more than one `mj_cards` printing
(different sets, same name), an arbitrary matching printing is used.
`type_line`/`mana_value`/`color_identity` are the same across
printings of a name; `scryfall_id` isn't — this picks *a* printing's
image, not a "preferred" one. Acceptable for v1, not guaranteed art.

---

## Rate-limit policy

`barrins_api` runs multiple worker processes (`fastapi_backend` role),
so an in-process Python limiter would multiply the effective limit by
worker count. Enforced at nginx instead, scoped to `/bff/tolaria-news`
only — Tamiyo Scroll's routes stay JWT-gated and unaffected:

- `ops/my-server/roles/backend_website/templates/ratelimit.conf.j2`
  (conf.d, http context): `limit_req_zone $binary_remote_addr
  zone=tolaria_news:10m rate=20r/s;`
- `ops/my-server/roles/backend_website/templates/https.conf.j2`: a
  `location /bff/tolaria-news { limit_req zone=tolaria_news burst=80
  nodelay; limit_req_status 429; ... }` block.
- Both are generated by a new, generic `backend_website_rate_limited_paths`
  role variable (`{path, zone, rate, burst}` list) — not hardcoded into
  the role, since `backend_website` is shared with any future backend
  app. `barrins_api.yml` sets the concrete Tolaria News entry.

`rate=20r/s`/`burst=80` is a deliberately generous starting default —
public data, no per-request cost, the real target is bot/scraper abuse
rather than normal browsing. Retune once `apps/tolaria_news` (T5)
exists and real per-page request volume is measurable (browser
devtools network tab, not a guess). Per-IP limiting is a known,
accepted limitation for shared/NAT IPs (school, corporate, mobile
carrier) — "restricted to the Tolaria News app" was decided as a soft
goal, not a hard boundary (I7, Option 4).

---

## Target architecture

Same router/service separation as Tamiyo Scroll — no query built
directly in a route file:

```text
app/
  api/
    tolaria_news/
      router.py            <- aggregator, mounted in main.py
                               alongside general/tamiyo_scroll routers
      tournaments.py        /tournaments, /tournaments/{id},
                             /tournaments/{id}/decks,
                             /tournaments/{id}/standings
      decks.py               /decks/{id}
  services/tolaria_news/
    pagination.py          <- opaque cursor encode/decode (keyset)
    tournaments.py         <- list/detail queries, freshness (latest_sync)
    decks.py                <- card-join + commander derivation
  schemas/
    responses_tolaria_news.py   <- Envelope/Meta/Page + response DTOs
```

No `app/schemas/tolaria_news.py` request-schema file: every route is a
`GET` with query-string filters declared directly on the route function
(matching `app/api/tamiyo_scroll/meta_decks.py`'s `include_archived:
bool = False` pattern) — there's no POST/PUT body anywhere in this v1
BFF to justify a dedicated request-schema module.

---

## Deferred scope (not built now, not "unscoped" — see T4's page)

Archetype clustering has an owner: T6 ("Karn Tablets," not started as
of this page's writing). Everything downstream of "archetype" in an
earlier design-handoff exploration (`/metagame`, `/archetypes`,
`/trends`) is sequenced as a **T4 iteration 2**, once T6/T8 ship —
and requires amending T6's own implementation plan, which currently
routes its clustering output to the S6 admin dashboard only, not to
Tolaria News. See T4's page for the full reconciliation against that
design-handoff material, including what's rejected outright (a
standalone Node BFF service — conflicts with the in-repo FastAPI
pattern this page implements) and what's still genuinely unowned
(`/forecasts`, full `/search`, a card oracle/image proxy, tournament
`location`).

---

## Phase breakdown (as implemented, 2026-08-11)

| Phase | Files |
| --- | --- |
| 1 | `app/schemas/responses_tolaria_news.py` |
| 2 | `app/services/tolaria_news/pagination.py`, `tournaments.py`, `decks.py` |
| 3 | `app/api/tolaria_news/{__init__,router,tournaments,decks}.py`, mounted in `main.py` |
| 4 | nginx rate limiter (`backend_website` role + `barrins_api.yml`) |
| 5 | `tests/tolaria_news/` (14 tests: routes, pagination, card resolution, commander derivation, no-auth) |

Full `barrins_api` suite: 455 passing, 97.16% coverage. `ruff`/`ty`
clean on all new/changed files.
