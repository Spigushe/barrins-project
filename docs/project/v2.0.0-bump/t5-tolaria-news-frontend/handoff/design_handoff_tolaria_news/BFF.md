# BFF — `tolaria_news` ↔ `barrins_api`

Backend-for-frontend contract. `barrins_api` is the **domain API** (normalized, generic, slow-changing). The **BFF** is a thin layer owned by the frontend team that shapes domain data into exactly what a route renders — one request per screen, no waterfalls, no client-side joins.

- **Domain API**: `barrins_api` — Python, owns ingestion, archetype clustering, stats.
- **BFF**: `tolaria_bff` — Node (Fastify or Hono) or FastAPI, sits between browser and `barrins_api`.
- **Client**: `tolaria_news` — React + TanStack Query, talks *only* to the BFF.

```
browser ──HTTPS──▶ tolaria_bff ──internal──▶ barrins_api ──▶ Postgres
                        │
                        └─ cache (in-proc LRU + Redis), auth, rate limit, ETag
```

## Why a BFF at all

1. **Screen-shaped payloads.** `/metagame` needs tournaments count + archetype table + color split + movers. That's 4 domain calls; the BFF makes it 1.
2. **Stable client contract.** `barrins_api` can rename/reshape internals; the BFF absorbs it.
3. **Cache boundary.** Metagame aggregates change at most hourly. Cache at the BFF, not in every browser tab.
4. **Payload discipline.** Domain responses carry fields the UI never renders. The BFF strips them.
5. **One place for i18n, feature flags, and the `Retry-After` / error envelope.**

If `barrins_api` is ever the *only* consumer-facing surface, the BFF collapses into a route-handler layer inside it — the contracts below still hold.

---

## Conventions

| Aspect | Rule |
|---|---|
| Base path | `/bff/v1` |
| Format | JSON, UTF-8. `Content-Type: application/json; charset=utf-8` |
| Casing | `snake_case` keys (matches `barrins_api`; avoids a translation layer) |
| Dates | ISO 8601 UTC, `2026-08-11T14:03:00Z`. Date-only fields: `2026-08-11` |
| Percentages | Floats `0..1`, never `0..100`. UI formats. |
| IDs | Opaque strings. Slugs for archetypes (`tymna-thrasios-flash-hulk`), ULIDs for decklists/tournaments |
| Pagination | Cursor: `?cursor=<opaque>&limit=50`. Response carries `page.next_cursor` (null = end) |
| Sorting | `?sort=field` / `?sort=-field` (leading `-` = desc). Whitelisted per endpoint. |
| Nulls | Omit absent optional fields rather than sending `null`, except where `null` is meaningful (e.g. `prev_share: null` = archetype is new) |
| Versioning | Path-versioned. Additive changes ship in `v1`; breaking changes mint `v2`. |

### Response envelope

Every 2xx body:

```jsonc
{
  "data":  { /* endpoint-specific */ },
  "meta": {
    "generated_at": "2026-08-11T14:03:00Z",
    "source_synced_at": "2026-08-11T13:51:00Z",   // drives the "last sync · 12 min ago" rail
    "cache": "hit" | "miss" | "stale-while-revalidate",
    "window": "30d"                                // echo of the effective query params
  },
  "page": { "next_cursor": "…", "limit": 50, "total": 412 }   // list endpoints only
}
```

### Error envelope

```jsonc
{
  "error": {
    "code": "ERR-UPSTREAM-TIMEOUT",   // rendered as the mono eyebrow on the error card
    "message": "The archive did not respond in time.",  // user-facing, in-tone, translatable
    "detail": "barrins_api /metagame exceeded 4000ms",  // dev-only; omitted in production
    "retryable": true,
    "request_id": "01J9…"
  }
}
```

| HTTP | `code` | When |
|---|---|---|
| 400 | `ERR-BAD-PARAM` | Unknown window, bad cursor, sort field not whitelisted |
| 404 | `ERR-NOT-FOUND` | Unknown archetype/decklist/tournament id |
| 422 | `ERR-QUERY-SYNTAX` | Decklist search DSL failed to parse (include `detail.position`) |
| 429 | `ERR-RATE-LIMIT` | Include `Retry-After` header |
| 502 | `ERR-UPSTREAM` | `barrins_api` returned 5xx |
| 504 | `ERR-UPSTREAM-TIMEOUT` | `barrins_api` exceeded the per-call budget |
| 503 | `ERR-COLD` | Aggregates rebuilding; include `Retry-After` |

The UI renders `code` as the `ERR-…` eyebrow and `message` as the serif title — see `PAGES.md` › *Empty / error / loading*.

### Caching

| Endpoint class | BFF TTL | `Cache-Control` to browser | Notes |
|---|---|---|---|
| Metagame aggregates | 15 min | `public, max-age=60, stale-while-revalidate=900` | Recomputed upstream hourly |
| Archetype index/detail | 30 min | `public, max-age=300, s-maxage=1800` | |
| Decklist detail | 24 h | `public, max-age=3600, immutable`-ish | Lists are immutable once published |
| Decklist search | 2 min | `private, max-age=0` | High cardinality; don't cache aggressively |
| Tournaments (past) | 6 h | `public, max-age=600` | |
| Tournaments (upcoming) | 5 min | `public, max-age=60` | |
| Trends / forecasts | 1 h | `public, max-age=600, stale-while-revalidate=3600` | |
| Card oracle data | 7 d | `public, max-age=86400` | Only changes on set release |

All GETs emit a strong `ETag` (hash of `data`); the BFF honours `If-None-Match` → `304`. TanStack Query config to match:

```ts
staleTime: 5 * 60_000,      // aggregates
gcTime:   30 * 60_000,
refetchOnWindowFocus: false,
retry: (n, e) => e.retryable && n < 2,
```

### Auth

Public read is unauthenticated. The nav's sign-in gates saved queries and watchlists only.

- Session cookie `tn_session`, `HttpOnly; Secure; SameSite=Lax`.
- The BFF holds the `barrins_api` service token server-side — it never reaches the browser.
- Anonymous rate limit: 120 req/min/IP. Authenticated: 600 req/min/user.

---

## Shared primitives

These shapes recur; define them once (see `API_TYPES.ts`).

```jsonc
// ColorIdentity — WUBRG subset, canonical order, uppercase
"colors": ["U", "W"]

// Commander — one entry; a pair is a 2-element array
{ "name": "Tymna the Weaver", "scryfall_id": "…", "partner_kind": "partner" }

// ArchetypeRef — the minimum needed to render a link + pips
{ "id": "tymna-thrasios-flash-hulk", "name": "Flash Hulk", "colors": ["W","U","B","G"] }

// StatDelta — powers <ShareDeltaPill>
{ "current": 0.081, "previous": 0.064, "delta": 0.017, "direction": "up" }

// Series — powers <Sparkline> and all charts
{ "points": [{ "t": "2026-07-06", "v": 0.061 }, …], "granularity": "weekly" }
```

---

## Endpoints

### 1. `GET /bff/v1/landing`

Powers `/`. One call for the whole banner.

**Query:** none.

**Response `data`:**
```jsonc
{
  "stats": {
    "tournaments_parsed": 3184,
    "archetypes_mapped": 412,
    "decklists_indexed": 96231
  },
  "season": { "label": "Duel Commander · season 2026.1", "started_on": "2026-01-15" },
  "telemetry": [                       // the three callouts on the viz
    { "label": "CLUSTER DENSITY", "value": "0.71", "note": "top-8 lists" },
    { "label": "DRIFT", "value": "+2.4%", "note": "vs. last window" },
    { "label": "NEW NODES", "value": "17", "note": "past 30d" }
  ],
  "embedding": {                       // optional; omit → viz stays procedural
    "nodes": [{ "id": "…", "x": 0.31, "y": -0.44, "weight": 0.08, "archetype": { … } }],
    "edges": [[0, 4], [0, 9]]
  }
}
```

Notes: `embedding` is the only place the decorative graph becomes real. If `barrins_api` has no embedding endpoint, the BFF omits the key and the client falls back to the procedural layout in `graph.jsx` — see `ANIMATING_STARS.md`. `x`/`y` are normalized to `-1..1`; the client maps to viewport.

---

### 2. `GET /bff/v1/metagame`

Powers `/metagame` in one call. Fans out to 3–4 domain calls in parallel.

**Query:** `window=7d|30d|90d|season` (default `30d`) · `tier=all|mid|top8` (default `all`)

**Response `data`:**
```jsonc
{
  "totals": {
    "tournaments": 214,
    "decks": 8817,
    "top_commander": { "name": "Tymna the Weaver", "share": 0.113 }
  },
  "archetypes": [
    {
      "archetype": { "id": "…", "name": "Flash Hulk", "colors": ["W","U","B","G"] },
      "share": 0.081,
      "prev_share": 0.064,          // null → new this window
      "delta": 0.017,
      "winrate": 0.573,
      "samples": 714,
      "sparkline": { "points": [ … ], "granularity": "weekly" }   // last 4 buckets
    }
  ],
  "colors": { "W": 0.18, "U": 0.31, "B": 0.24, "R": 0.14, "G": 0.13 },  // sums to 1
  "movers": {
    "up":   [ { "archetype": { … }, "delta": 0.021, "sparkline": { … } } ],
    "down": [ … ]
  }
}
```

**Sizing:** `archetypes` is capped at 60 rows (everything below 0.2% share is folded into a synthetic `{"id": "other", "name": "Other"}` row). `movers.up`/`down` are 4 each. Target payload < 60 KB gzipped.

**Client mapping:** `totals` → hero stat blocks · `archetypes` → `ArchetypeTable` (`delta` → `ShareDeltaPill`) · `colors` → treemap/stacked bar · `movers` → the 4-card grid.

---

### 3. `GET /bff/v1/archetypes`

Powers the `/archetypes` index grid + filter rail.

**Query:** `q` (free text) · `colors=UW` (subset match; `colors_mode=exact|subset`, default `subset`) · `strategy=control,combo` · `commander_count=mono|partner|background` · `min_samples=25` · `sort=-share|-winrate|name` · `cursor` · `limit` (≤ 60, default 24)

**Response `data`:** array of
```jsonc
{
  "id": "tymna-thrasios-flash-hulk",
  "name": "Flash Hulk",
  "colors": ["W","U","B","G"],
  "commanders": [ { "name": "Tymna the Weaver", … }, { "name": "Thrasios, Triton Hero", … } ],
  "strategy": "combo",
  "share": 0.081,
  "winrate": 0.573,
  "samples": 714,
  "staples_preview": ["Flash", "Protean Hulk", "Mana Crypt", "Force of Will", "Demonic Tutor"]
}
```

`meta.facets` carries counts for the filter rail so it never needs its own call:
```jsonc
"facets": {
  "colors":   { "W": 188, "U": 301, … },
  "strategy": { "control": 96, "combo": 74, … }
}
```

---

### 4. `GET /bff/v1/archetypes/:id`

Powers the `/archetypes/:id` hero + the default (Decklists) tab, so the page paints in one round trip.

**Response `data`:**
```jsonc
{
  "id": "…", "name": "Flash Hulk", "colors": ["W","U","B","G"],
  "commanders": [ … ],
  "strategy": "combo",
  "description": "A two-card combo shell that…",
  "stats": { "share": 0.081, "winrate": 0.573, "samples": 714, "first_seen": "2023-04-12" },
  "share_over_time": { "points": [ … ], "granularity": "monthly" },
  "centroid": { "x": 0.31, "y": -0.44, "neighbors": [ { "archetype": { … }, "distance": 0.12 } ] },
  "decklists": { "items": [ /* DecklistRow, first page */ ], "next_cursor": "…" }
}
```

Tab data loads lazily as separate calls:

| Tab | Endpoint |
|---|---|
| Decklists (page 2+) | `GET /bff/v1/archetypes/:id/decklists?cursor=…` |
| Cards | `GET /bff/v1/archetypes/:id/cards` |
| Trends | `GET /bff/v1/archetypes/:id/trends?window=1y&granularity=monthly` |
| Tournaments | `GET /bff/v1/archetypes/:id/tournaments?cursor=…` |

`…/cards` response:
```jsonc
{
  "always_run": [ { "name": "Force of Will", "inclusion": 0.98, "trend": { "points": [ … ] } } ],
  "often_run":  [ … ],   // 0.5 ≤ inclusion < 0.9
  "flex":       [ … ]    // 0.15 ≤ inclusion < 0.5 — collapsed by default in the UI
}
```

---

### 5. `GET /bff/v1/decklists`

Powers the virtualized table.

**Query:** `q` (DSL, below) · `archetype` · `pilot` · `tournament` · `colors` · `placement_max=8` · `from=2026-01-01` · `to=…` · `sort=-date|placement|pilot` · `cursor` · `limit` (≤ 100, default 50)

**Search DSL** — parsed by the BFF, not the client. Grammar:
```
term        := bare_word | quoted | field_filter
field_filter:= ("commander"|"color"|"colors"|"pilot"|"archetype"|"tournament"|"card"|"placement"|"date") ":" value
value       := word | quoted | range ("2026-01-01..2026-06-30", "1..8")
```
Bare words search commander names, pilot, and archetype name. Terms AND together. Unparseable input → `422 ERR-QUERY-SYNTAX` with `detail.position` so the input can underline the offending token.

**Response `data`:** array of `DecklistRow`:
```jsonc
{
  "id": "01J9…",
  "pilot": "A. Nakamura",
  "commanders": [ … ],
  "colors": ["U","B"],
  "archetype": { "id": "…", "name": "Dimir Tempo", "colors": ["U","B"] },
  "tournament": { "id": "…", "name": "Paris DC Open", "date": "2026-07-19" },
  "placement": 3,
  "player_count": 184
}
```

Row shape is intentionally flat and small — the table renders 50 rows at a time; keep it under 25 KB gzipped per page.

---

### 6. `GET /bff/v1/decklists/:id`

```jsonc
{
  "id": "01J9…",
  "pilot": "A. Nakamura",
  "commanders": [ … ],
  "archetype": { … },
  "tournament": { "id": "…", "name": "…", "date": "…", "location": "Paris, FR", "player_count": 184 },
  "placement": 3, "record": "6-1-1",
  "published_at": "2026-07-20T09:00:00Z",
  "cards": {
    "commander":    [ { "name": "…", "qty": 1, "cmc": 4, "scryfall_id": "…", "type_line": "…" } ],
    "creatures":    [ … ], "spells": [ … ], "artifacts": [ … ],
    "enchantments": [ … ], "planeswalkers": [ … ], "lands": [ … ]
  },
  "analysis": {
    "mana_curve": [ { "cmc": 0, "count": 9 }, { "cmc": 1, "count": 21 }, … ],
    "color_split": { "U": 0.52, "B": 0.48 },
    "unique_cards": ["Sword of Feast and Famine"]   // not in archetype's always_run
  }
}
```

Card detail for the side drawer: `GET /bff/v1/cards/:scryfall_id` → oracle text, mana cost, type line, plus `inclusion_in_archetype` when `?archetype=<id>` is passed. **Card images and oracle text come from Scryfall** — the BFF proxies and caches them; never hotlink Scryfall from the browser (their API asks for ≤ 10 req/s and a real User-Agent).

---

### 7. `GET /bff/v1/tournaments`

**Query:** `status=recent|upcoming` (default `recent`) · `cursor` · `limit` (≤ 50, default 20)

**Response `data`:**
```jsonc
{
  "featured": { /* TournamentCard, only on page 1 of status=recent */ },
  "items": [
    {
      "id": "…", "name": "Paris DC Open", "date": "2026-07-19",
      "location": "Paris, FR", "player_count": 184, "status": "completed",
      "winner": { "pilot": "A. Nakamura", "archetype": { … }, "decklist_id": "01J9…" },
      "top_archetypes": [ { "archetype": { … }, "share": 0.14 } ]   // up to 4
    }
  ]
}
```

Detail: `GET /bff/v1/tournaments/:id` (hero + standings page 1) · `…/:id/standings?cursor=` · `…/:id/metagame` (field share + conversion: `{ archetype, entered, top8, conversion }`) · `…/:id/decklists?cursor=`.

---

### 8. `GET /bff/v1/trends`

**Query:** `window=90d|6m|1y|all` · `granularity=weekly|monthly` · `archetypes=<id,id,…>` (default: top 10 by share)

```jsonc
{
  "buckets": ["2026-01", "2026-02", …],
  "series": [
    { "archetype": { … }, "points": [0.061, 0.068, …] }   // index-aligned to buckets
  ],
  "other": [0.11, 0.10, …]     // everything outside the selected set; keeps the stack at 1.0
}
```

Parallel arrays, not objects-per-point — a 12-month × 10-archetype stacked area is ~120 numbers instead of ~120 objects. Matters at `window=all`.

- `GET /bff/v1/trends/cards?names=Force+of+Will,Mana+Crypt&window=1y` — same bucket/series shape, ≤ 6 names.
- `GET /bff/v1/forecasts?horizon=4w` →
  ```jsonc
  { "rising": [ { "archetype": { … }, "projected_delta": 0.014,
                  "confidence": { "low": 0.004, "high": 0.024 },
                  "sparkline": { "points": [ … ] } } ],
    "falling": [ … ], "stable": [ … ] }   // 3 each
  ```
  `confidence` renders as the faint band behind the sparkline. If the model isn't ready, return `503 ERR-COLD` and the UI hides the section rather than showing empty cards.

---

### 9. `GET /bff/v1/search`

Powers ⌘K. Cross-entity, debounce 200 ms client-side, hard 150 ms budget at the BFF.

**Query:** `q` (≥ 2 chars) · `limit=8` per group

```jsonc
{
  "archetypes":  [ { "id": "…", "name": "…", "colors": [ … ] } ],
  "commanders":  [ { "name": "…", "scryfall_id": "…", "archetype_count": 12 } ],
  "tournaments": [ { "id": "…", "name": "…", "date": "…" } ],
  "pilots":      [ { "name": "…", "decklist_count": 31 } ]
}
```

---

### 10. `GET /bff/v1/meta/health`

`{ "status": "ok", "upstream": "ok", "source_synced_at": "…", "build": "…" }` — drives the bottom rail's sync stamp and any status page. Cache 30 s.

---

## BFF implementation notes

**Fan-out with budgets.** Each domain call gets a 4 s timeout; the composite handler has a 6 s ceiling. If a *non-essential* part fails (e.g. `movers`), return the rest with a `meta.partial: ["movers"]` marker rather than failing the screen. The client renders those sections in their empty state.

**Never proxy blind.** Every field in a BFF response is explicitly mapped. No `return upstream.json()` — that's how domain refactors become frontend outages.

**Aggregate keys, not query strings.** Cache key = normalized tuple of whitelisted params (`window`, `tier`, `sort`, `cursor`), not the raw URL. Unknown params are rejected with `400`, which keeps the key space bounded.

**Compression.** Brotli where supported, gzip otherwise. The trends payloads are the only ones near the 100 KB mark.

**Observability.** Log `request_id`, route, upstream call count, upstream ms, cache result, response bytes. Alert on p95 > 800 ms or upstream error rate > 2%.

**Local development.** Ship `msw` handlers generated from the fixtures in `fixtures/` so the frontend can be built and demoed with `barrins_api` unavailable. Every endpoint above needs one realistic fixture — that's also the contract test corpus.

**Contract tests.** Validate every BFF response against the schemas in `API_TYPES.ts` (via `zod` or `typebox`) in CI, on both real and fixture data. A schema drift should break the BFF build, not the browser.

---

## Open questions for `barrins_api`

1. Does an **embedding endpoint** exist (node coordinates + edges)? If yes, `/landing.embedding` becomes real; if no, the viz stays decorative and this can wait.
2. Is **archetype clustering** stable across re-runs, or do ids churn? If ids churn, the BFF needs a slug-alias table so bookmarked `/archetypes/:id` URLs survive re-clustering.
3. What's the **ingestion cadence**? All the TTLs above assume hourly aggregate rebuilds — tell us the real number and they get retuned.
4. Are **upcoming tournaments** in scope, or is the corpus results-only? Affects `/tournaments?status=upcoming`.
5. Are **forecasts** in scope for v1, or does `/trends` ship without the forecast row?
6. **Scryfall data**: does `barrins_api` already store card oracle data, or does the BFF fetch and cache it itself?
7. **Language**: does the API carry FR/EN archetype names and descriptions, or is copy frontend-owned? (See the i18n note in `README.md`.)
