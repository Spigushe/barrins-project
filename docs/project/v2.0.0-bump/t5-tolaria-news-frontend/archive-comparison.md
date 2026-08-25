# T5 addendum — Landing/Tournaments appearance & data vs. `barrins-archive/tolaria_news`

[← Back to T5](index.md)

| | | Comment |
| --- | --- | --- |
| **Status** | 🟡 Study complete, decisions pending | Not scheduled as implementation yet |
| **Raised** | 2026-08-14 | User: "T5 appearance and data for the first two pages can be based on archive version" (`https://github.com/barrins-archive/tolaria_news`) |
| **Scope** | Landing (`/`) and Tournaments (`/tournaments`) only | The two pages a visitor actually reaches with `VITE_FEATURE_KARN_TABLETS` off (default) |

---

## Context

`barrins-archive/tolaria_news` is the same design-handoff prototype already
on record in T5's own page (`handoff/design_handoff_tolaria_news/`) — a
Vite+JS app calling a speculative `/api/v1/tolaria/*` API that doesn't
exist. T5 was scoped 2026-08-14 as **restyle only** against T4's real,
public `/bff/tolaria-news/*` routes (`GET /tournaments`,
`GET /tournaments/{id}`, `GET /tournaments/{id}/decks`,
`GET /tournaments/{id}/bracket`, `GET /tournaments/{id}/standings`,
`GET /decks/{id}` — confirmed against
`apps/barrins_api/app/api/tolaria_news/tournaments.py`; no stats/meta/
metagame aggregate endpoint exists anywhere in T4).

This addendum records a comparison, done at the user's request, between
the archive's first two pages and the current `apps/tolaria_news`
implementation, to separate what can be adopted as pure appearance from
what would require inventing data client-side (Constitution §4.1/§4.2)
or a T4 endpoint that doesn't exist yet.

---

## Landing page (`/`)

### Appearance — safe to adopt, no data risk

- Archive mounts a global `Starfield` above all routes (`App.jsx`);
  current has only per-page `BackgroundField`, no starfield layer.
  Confirm whether this was a deliberate drop during the restyle or a gap.
- Archive has a secondary "Read the methodology" button next to the
  primary CTA; current has only the primary CTA. No methodology page
  exists in either app — decide stub vs. drop.
- Naming inconsistency already present in current code, independent of
  the archive: the header reads "Tolaria News" but the landing subhead
  reads *"Barrin's Project is a suite of..."* (`LandingPage.tsx:12`).
  Archive's equivalent subhead correctly says "Tolaria News." Worth
  fixing regardless of this comparison.

### Data — do not copy verbatim

- Archive's eyebrow (`Barrin's API· {meta.version}`) and its 3 stats
  (tournaments/archetypes/decklists) are fed by `fetchStats`/`fetchMeta`
  against `/api/v1/tolaria/{stats,meta}` — endpoints that don't exist in
  T4. Archive's `VizPanel` callouts (cluster/commander/winrate) are fed
  by `fetchTopArchetype` against `/api/v1/tolaria/metagame/top` — also
  nonexistent (needs Karn Tablets/T6).
- Current already handles this correctly: two stats are static
  placeholder strings (documented as such in `LandingPage.tsx`'s own
  comments), and `VizPanel`'s archetype-specific callouts are fully
  gated behind `VITE_FEATURE_KARN_TABLETS`, showing only the decorative
  procedural graph when the flag is off. **This is the right behavior
  per §4.1/§4.2 and must not regress** — "based on archive" should not
  be read as "make these numbers look live" without a real backing
  endpoint.
- Open, non-blocking question: does T4's `GET /tournaments` envelope
  expose a real total count that could back "tournaments parsed"
  instead of the hardcoded `3,184`? Worth a quick check before deciding
  it has to stay a placeholder.

---

## Tournaments page (`/tournaments`)

### Appearance — the real scope question

Archive is a dashboard: 4 tabs (Recent / Upcoming / By region /
Calendar), a "Featured event" hero panel (a 3-stat headline row + a
Top-4 standings list), then a responsive 3-column card grid with a
status badge and winner per card. Current is a plain filterable table
(Source / From / To filters, Date / Name / Source / Players columns,
cursor pagination).

Adopting archive's layout is a genuine page rebuild, not a CSS-level
restyle — it crosses the "restyle only" boundary T5 already drew
(see T5's own `index.md`, Context section). **Needs explicit sign-off
before implementation, not an assumed yes.**

### Data — validated per element against T4's real routes

| Archive element | Backed by T4 today? |
| --- | --- |
| Event cards (name / date / players / status) | Yes — close to `TournamentSummary`, reshape only |
| "Winner" per card | Not in `TournamentSummary`; would need a `/standings` call per card (N+1 risk across a grid) |
| Featured event's **Top 4** | **Yes, genuinely** — `GET /tournaments/{id}/standings` is real. Unlike the rest of the page this is adoptable as real data, not mock |
| "11.4% winning archetype / 32 archetypes / 73% conversion top 8" | No — needs archetype clustering (Karn Tablets/T6, unshipped). Must stay flag-gated or be dropped, same pattern as the Landing page's `VizPanel` |
| "Upcoming" / "By region" / "Calendar" tabs | No backend concept — T3's ingestion pipeline only ever writes past scraped results; no region/date-grouping filter exists on `GET /tournaments` |
| Location field (e.g. "Paris, FR") | Not evidenced as a queryable or returned field in `tournaments.py`/`TournamentSummary` — needs a schema check before assuming it exists |
| Source / date-range filters | Current already has these wired for real against T4 query params; archive has **no** working filter UI on this page at all |
| Pagination | Current already matches T4's real cursor contract (`next_cursor`); archive's table has none |

**Bottom line**: most of archive's Tournaments-page visual richness is
hardcoded mock data (`TOURNAMENTS`, `TOP_4`, the stat trio) laid over a
page that only partially calls its own speculative API. The one element
that is genuinely real and cheaply adoptable is Top-4-via-`/standings`;
everything else needs either a schema check, a feature-flag gate
(matching the Karn Tablets pattern already used elsewhere in this app),
or is not backed by any data that exists today.

---

## Open decisions (need the user's call before implementation)

- [ ] **Landing**: adopt the cosmetic-only items (Starfield layer,
      secondary CTA, fix the "Barrin's Project" → "Tolaria News"
      subhead wording)? No data risk either way.
- [ ] **Tournaments**: keep the current table, or rebuild as archive's
      dashboard layout (tabs + featured panel + card grid)? If
      rebuilding: restrict "data" to what's genuinely backed by T4
      today (event cards + real Top 4 via `/standings`), and gate or
      drop the archetype-stat trio and the Upcoming/region/calendar
      tabs the same way `VizPanel` already gates Karn-Tablets-only data.
