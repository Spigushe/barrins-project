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
| `GET` | `/bff/tolaria-news/decks` | Global, cross-tournament decklist index (T5's `/decklists` route). Restricted server-side to Duel Commander tournaments. Filters: `player` (substring), `source`, `commander` (exact), `colors` (repeated, exact color-identity match), `date_from`/`date_to`. `cursor`/`limit`. Each row carries `tournament_name`/`tournament_source` so it's meaningful without a second request |
| `GET` | `/bff/tolaria-news/decks/commanders` | Distinct commander names across Duel Commander tournaments — backs `/decklists`' commander dropdown. Small, unpaginated. Must stay registered before `/decks/{id}` (see code comment) |
| `GET` | `/bff/tolaria-news/decks/{id}` | Deck detail: full decklist + derived commander(s) |

No route accepts or requires `CurrentUser` — covered by an explicit
test (`tests/tolaria_news/test_tournaments.py::TestNoAuthRequired`)
guarding against a copy-paste of Tamiyo Scroll's router silently
reintroducing auth.

Deliberately **not** in v1 (see "Deferred scope" below):
`/metagame`, `/archetypes`, `/trends`, `/forecasts`, `/search`, a card
oracle-text/image proxy, and tournament `location`. Bracket data
(`bs_rounds`/`bs_round_matches`) **is** in v1 (`/tournaments/{id}/bracket`,
added 2026-08-11 — see [ADR-13](../../../ops/architecture/decisions.md#adr-13-karn-tablets-output-data-flow-scope-and-consumption-surface)).

**Addendum (2026-08-15)**: `GET /decks` (global index) added to back T5's
`/decklists` route. Deliberately a plain filtered list, not the
design-handoff prototype's `commander:X color:UW` search DSL — at the
time, commander/color looked like they needed indexing as queryable data
that didn't exist anywhere (`get_deck` only ever derived a commander for
one deck at a time, on demand). Full DSL support was tracked as a
separate follow-up.

**Addendum (2026-08-16)**: that premise was wrong, and it's worth
recording why. `app/services/scripture/ingester.py::_replace_deck_cards`
already runs *every* `bs_deck_cards.card_name` — mainboard and sideboard
— through `card_resolver.resolve_card_name` before storing it; a name
that doesn't resolve is skipped at ingest, never stored. So `card_name`
is never a raw scraped string — it's already guaranteed to equal some
`mj_cards.name`/`face_name` exactly. That means commander/color-identity
filtering needs no Python-side resolution at query time and no new
indexed columns: it's plain, exact-match SQL joining `bs_deck_cards` to
`mj_cards` on name equality. `list_decks` gained `commander` (an `EXISTS`
against sideboard `card_name`) and `colors` (exact color-identity-set
match, decomposed into two conditions — no sideboard card has a color
outside the requested set, and every requested color is covered by at
least one sideboard card — using `ARRAY.contains()`/`.contained_by()`,
correct across a partner pair's up-to-2 commander rows without needing
`unnest`/aggregation). New `list_commanders` backs the dropdown. No
change to pagination — both filters are ordinary SQL `WHERE` clauses, so
the existing keyset cursor logic needed no special-casing.

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

`CommanderRef` carries `mana_cost`, `text`, and `keywords` alongside
`name`/`scryfall_id`/`color_identity` (added for T5's decklist table —
the frontend renders a Commander row with the same Qty/Name/Color
pips/Popover columns as every other card group, which needs oracle
text and mana cost). These reuse the same resolved `mj_cards` row
`_as_deck_card_out` already builds for mainboard cards — no second
resolution pass, just the fields that were previously discarded when
building `CommanderRef`.

When a resolved card name matches more than one `mj_cards` printing
(different sets, same name), an arbitrary matching printing is used.
`type_line`/`mana_value`/`color_identity` are the same across
printings of a name; `scryfall_id` isn't — this picks *a* printing's
image, not a "preferred" one. Acceptable for v1, not guaranteed art.

**Updated 2026-08-14 (S4)**: `mainboard` is no longer a flat
`DeckCardOut[]` — it's grouped into `DeckCardTypeGroup[]` (`category`,
`count`, `cards`), same category order and sort (type, then mana
value, then name) as Tamiyo Scroll's own decklist view, both built on
the shared `app/services/decklist_sort.py` module rather than each app
deriving its own order. `DeckCardOut`/`CommanderRef` both gained
`mana_cost`/`text`/`keywords` (already documented above for
`CommanderRef`) so the frontend's mana-pip rendering and oracle-text
popover work identically for a commander row and a mainboard row. Card
art itself is served by a new, general (not `/bff/tolaria-news`-
scoped) route, `GET /api/v1/cards/{scryfall_id}/image` — a disk-cached
Scryfall image proxy (`app/services/scryfall/`), reused as-is by both
this BFF and Tamiyo Scroll's decklist view since card art isn't a
Tolaria-News-specific concept. See `auth_roles.md`'s security matrix
for the route's auth posture (anonymous, same as `/sets/*`/`/cards/*`).

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

## Karn Tablets clustering — `/metagame`, `/archetypes`, `/trends` (ADR-13)

Built 2026-08-27. Backed by the `kt_*` tables the Karn Tablets clustering
job (`apps/karn_tablets`) pushes into via `POST /internal/karn/ingest`
(ADR-13's push-based data flow — `barrins_api` owns the schema, every
consumer reads Postgres directly). Public, no auth (ADR-10), wrapped in
the same `Envelope`/`Meta` as the rest of this BFF.

### `POST /internal/karn/ingest`

| | |
| --- | --- |
| **Purpose** | Persist one clustering run: window metadata + per-cluster share and representative decklist. Each cluster is matched to a stable `kt_archetypes` identity by representative-decklist Jaccard similarity (`app/services/karn/ingester.py`, threshold `0.6`) so `/trends` can follow an archetype across runs; the pipeline's raw `cluster_id` is *not* a stable identity. |
| **Auth** | Static shared secret, `X-Karn-Token` header (`KARN_INGEST_TOKEN`), same mechanism as `X-Scripture-Token`. No admin-JWT fallback — the only caller is the scheduled job. |
| **Request** | `{window: {kind, date_from, date_to, label}, algorithm, total_decks, pipeline_version, generated_at, archetypes: [{cluster_id, deck_count, share, representative_mainboard, representative_sideboard}], format?}`. `format` is optional and not sent by the pipeline today — the ingester stamps `"Duel Commander"`. This body is the frozen contract `apps/karn_tablets/karn_tablets/push.py` builds. |
| **Response** | `200 {run_id, archetypes_matched, archetypes_created}` |
| **Idempotency** | An exact re-push of the same `(format, window kind, window label, generated_at)` updates the run in place and rebuilds its cluster rows. A re-run of the same window with a later `generated_at` is a *new* run and becomes the one reads return. |
| **Errors** | `401` missing/wrong token · `503` token not configured · `422` malformed body |

### Public read routes

All take `window` (`rolling_30d` \| `banlist_period`, required) and
`format` (optional, default `"Duel Commander"` — the only populated value
in v1; the param ships from v1 per ADR-13's 2026-08-27 amendment). By
default they read the **latest** window for that `(format, window)`;
`/metagame` and `/archetypes` also take `at` — a `window.label` from a
prior response — to step to a past window (`404` if no run has that
label). An unknown format or a window kind with no runs yet returns an
empty snapshot with the current calendar window and `200`, never an
error.

| Method | Path | Response |
| --- | --- | --- |
| `GET` | `/bff/tolaria-news/metagame?at=` | `Envelope[{format, window, previous_window \| null, next_window \| null, archetypes: [{id, name, commanders: [CardRef], deck_count, deck_share, deck_share_delta \| null, momentum}]}]`, largest archetype first |
| `GET` | `/bff/tolaria-news/archetypes?at=&limit=&cursor=` | `Envelope[{format, window, previous_window \| null, next_window \| null, archetypes: [{…MetagameArchetype, representative_mainboard: [{name, qty, scryfall_id \| null, is_land, is_signature}]}]}, page: {next_cursor \| null, limit}]` — `limit` 1–100 (default 20), `cursor` opaque; a malformed cursor is `400` |
| `GET` | `/bff/tolaria-news/trends` | `Envelope[[{archetype_id, archetype_name, commanders: [CardRef], points: [{window: WindowOut, deck_share \| null}]}]]` — top-10 archetypes of the latest run, their share across the last 12 runs; `deck_share` is `null` for a run in which the archetype had no cluster |

`window` / `previous_window` / `next_window` are all `WindowOut`. The
last two are the adjacent windows of the same kind (oldest→newest,
ordered by period start), for the frontend's prev/next stepper — `null`
at either end. Navigate by re-requesting with `?at=<window.label>`.

`CardRef` is `{name, scryfall_id \| null}`. `commanders` (on every
archetype row of all three routes) is the archetype's commander card(s)
— 1 solo, 2 for a partner pair, `[]` for none — resolved against
`mj_cards` for the frontend's card-image hover; `name` can diverge from
them (an admin rename, a `#2` split).

`momentum` (`"rising" \| "falling" \| "stable" \| "new"`) and
`deck_share_delta` compare each archetype to the run of the **preceding
window of the same kind** (`previous_window`), not "the second-most-
recent run" — so momentum stays meaningful at any point in the stepper.
`deck_share_delta` is the raw share change; `momentum` buckets it against
a ±10%-of-previous-share relative band (inside → `"stable"`; outside →
`"rising"`/`"falling"`). `"new"` means the archetype had a cluster in
this window but none in the preceding one (`deck_share_delta` is then
`null`); at the oldest window (`previous_window` is `null`) every
archetype is `"stable"` with a `null` delta.

`is_land` (`/archetypes` only) is resolved against `mj_cards.type_line`
(via `app/services/decklist_sort.py::categorize`). `is_signature` is the
"belongs in the signature-cards view" flag: `true` for every non-land;
`false` for a **basic** land (`Basic` supertype) always, and for any
other land that appears in ≥33% of the run's archetypes' representative
lists (a metagame-wide staple). A non-basic land unique to one archetype
stays `is_signature: true`. The ≥33% threshold and the basic-land rule
are backend-owned (Constitution §4.1/§4.2) — the frontend just filters
on `is_signature`. Only `/archetypes` resolves per-card facts;
`/metagame` and the S6 admin route resolve commanders only.

`apps/tolaria_news/src/schemas/karnTablets.ts` is reconciled against
this contract and its Metagame/Archetypes/Trends pages are wired to
these routes: window defaults to `banlist_period`; Metagame and
Archetypes carry a prev/next period stepper (`?at=`); Archetypes is the
paginated detail table only; the Trends per-archetype grid is two rows
of five. It all stays behind `VITE_FEATURE_KARN_TABLETS`, still unset in
every environment — flipping it is gated on T7 docs / T8 playbook.

The S6 admin dashboard reads the same numbers through the same service
(`app/services/karn/read.py::metagame_snapshot`) at
`GET /bff/tamiyo-scroll/admin/metrics/karn-tablets?window=&format=`
(`AdminUser`-gated) — so admin and public can't drift (ADR-13
consequence). This is a §51 aggregate-analytics surface: counts/shares
derived from data already stored for the pipeline, public for the BFF,
admin for S6.

### Still deferred

`/forecasts`, full `/search` DSL, and tournament `location` remain
genuinely unowned (see T4's page — a standalone Node BFF service was
rejected outright as conflicting with this in-repo FastAPI pattern). The
card image proxy once named here as unowned **was** built, 2026-08-14,
as part of S4 — see the "Commander + card data" section above.

The Karn Tablets deployment playbook (T8) landed 2026-08-28
(`ops/my-server/karn_tablets.yml` — a scheduled `systemd`-timer job, not
deployed to the real VPS yet). No separate nginx rate-limit entry was
needed for `/metagame`, `/archetypes`, `/trends`: `barrins_api.yml`'s
existing `location /bff/tolaria-news` `limit_req` block is a prefix
match that already covers them (`20r/s`, burst `80`, per IP).

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

**S4 addendum (2026-08-14)**: `mainboard` type-grouping/sort and the
`GET /cards/{scryfall_id}/image` proxy landed alongside Tamiyo Scroll's
own decklist redesign (shared `app/services/decklist_sort.py` and
`app/services/scryfall/`) — see the "Commander + card data" section
above. Full `barrins_api` suite now 500 passing, 97.20% coverage;
`ruff`/`ty` clean.

**T5 addendum (2026-08-15)**: `GET /decks` (global decklist index) added
— see the route-map addendum above. `app/schemas/responses_tolaria_news.py`
gained `DeckListItem`; `app/services/tolaria_news/decks.py` gained
`list_decks` (same keyset-cursor pattern as `list_tournaments`);
`app/api/tolaria_news/decks.py` gained the route plus its own local
`_meta`/`_decode_cursor_or_400` helpers (mirroring `tournaments.py`).
14 new/updated tests in `tests/tolaria_news/test_decks.py` (25 total in
the package); `ruff`/`ty` clean.

**T5 addendum (2026-08-16)**: `commander`/`colors` filters and
`GET /decks/commanders` added to `GET /decks` — see the 2026-08-16
route-map addendum above for why this turned out to be plain SQL rather
than the follow-up item the previous addendum expected.
`app/services/tolaria_news/decks.py` gained `_sideboard_card_exists`,
`_sideboard_card_joined_to_mj_cards`, and `list_commanders`.
`pyproject.toml` gained `[tool.ruff.lint.flake8-bugbear]
extend-immutable-calls = ["fastapi.Query"]` — ruff's B008 treats any
non-scalar-typed default (`list[str] | None`) as mutable regardless of
the `Query(...)` call wrapping it; this is ruff's own documented escape
hatch for that FastAPI pattern. 8 new tests in
`tests/tolaria_news/test_decks.py` (33 total in the package); `ruff`/`ty`
clean.
