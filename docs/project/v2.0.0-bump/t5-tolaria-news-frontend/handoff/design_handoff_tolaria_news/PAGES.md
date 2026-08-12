# Pages — tolaria_news

Per-route briefs. The landing page is fully designed in `design_files/`; the five inner pages are spec'd here. **Use the same design system (`DESIGN_SYSTEM.md`) across every page** — shared Nav, shared BackgroundField, shared BottomRail, shared type/color tokens.

---

## Shared layout

Every route renders inside this shell:

```
┌──────────────────────────────────────────────┐
│  Nav (logo, links, ⌘K, sign-in)              │  ← sticky on scroll, becomes translucent
├──────────────────────────────────────────────┤
│                                              │
│  <Outlet />  — the route's content           │
│                                              │
├──────────────────────────────────────────────┤
│  BottomRail (context · scroll · status)      │
└──────────────────────────────────────────────┘
   + BackgroundField (radial + grain) absolute
```

- Nav: same component as the landing page. Active route link gets `color: var(--ink)` and a 0.5px accent underline (1px offset below baseline).
- BottomRail: contextualize per page — the middle column can be a breadcrumb or last-updated stamp on inner pages.
- BackgroundField: keep on every page, slightly dimmer (drop the radial intensity ~30%) so it doesn't fight content.

---

## `/` — Landing

**Status:** fully designed.

See `design_files/`. Recreate pixel-perfect. Key elements:
- Eyebrow chip with accent dot
- Italic-accent display headline
- Subhead
- Two CTAs (primary "Explore the metagame", secondary "Read the methodology")
- Stats row (tournaments parsed / archetypes mapped / decklists indexed)
- Node-graph viz on the right with three telemetry callouts and corner brackets
- Bottom rail with "Duel Commander · season 2026.1" and "last sync · 12 min ago"

The CTAs link to `/metagame` (primary) and `/about` or `/methodology` (secondary — add this route if you want a methodology page; otherwise drop the secondary CTA).

---

## `/metagame` — Metagame snapshot

### Purpose
Single-screen "state of the format" view. Answers: *what decks are people winning Duel Commander tournaments with right now?*

### Layout

```
[Page header]
  Eyebrow:  "Metagame · last 30 days"
  Title:    "What's winning in Duel Commander."
  Filters:  [Time window: 7d / 30d / 90d / season] [Tier: all / mid+ / top8 only]

[Hero row — 3 stat blocks]
  Total tournaments · Total decks · Top commander share

[Main grid — 2 columns @ desktop, 1 @ mobile]
  Left  (8/12):  Archetype share table (sortable; row = archetype, columns = share / Δ / winrate / sample size)
  Right (4/12):  Treemap or stacked bar of color identity distribution

[Below the fold]
  "Movers" — 4-card grid: archetypes with the biggest share delta (up and down)
    Each card: archetype name (serif), Δ% (mono, signed, colored), small sparkline of last 4 weeks
```

### Data (from `barrins_api`)
- `GET /api/metagame?window=30d&tier=all` → `{ tournaments: n, decks: n, archetypes: [{ id, name, share, prev_share, winrate, samples }], colors: { W: 0.18, U: 0.31, ... } }`
- `GET /api/archetypes/movers?window=30d&n=8` → `[{ id, name, delta, sparkline: [...] }]`

### States
- **Loading**: skeleton — gray shimmer blocks at the same heights as the real data
- **Empty**: not applicable (there's always data); if API fails, show retry CTA
- **Error**: full-page mono error card with retry button

### Components new to this page
- `ArchetypeTable` — sortable table; rows use the eyebrow-chip pattern for the color identity pip cluster
- `ShareDeltaPill` — small pill, `+/-X.X%`, green for positive, terracotta for negative (NOT red — match the warm accent system)
- `Sparkline` — 80×24px inline mini-chart, accent stroke, no axes
- `TreemapBlock` or `StackedBar` — pick one

---

## `/archetypes` — Archetypes index + detail

### Purpose
Browse and drill into archetypes. Each archetype is a cluster of decks built around a similar core strategy and commander pair.

### Index layout (`/archetypes`)

```
[Page header]
  Eyebrow:  "412 archetypes mapped"
  Title:    "Every archetype, traced to its core."
  Search:   [⌘K-styled search input — "Search by commander, color, or strategy…"]

[Filter rail — left, sticky]
  Color identity (multi-select pips)
  Commander count (mono / partner pair / friends-forever)
  Strategy tag (control / aggro / midrange / combo / stax / tempo)
  Sample size minimum (slider)

[Grid — 3 columns @ desktop, 2 @ tablet, 1 @ mobile]
  Archetype cards. Each card:
    - Card frame: 14px radius, 0.5px hairline border, padding 24
    - Top:    commander pair (mono pip cluster + names in serif)
    - Middle: representative decklist excerpt (4–6 staple cards, mono, dim)
    - Bottom: 3 mini-stats — share / winrate / samples (mono labels, serif numbers)
    - Hover:  border brightens to var(--ink) at 25%; subtle translateY(-1px)
    - Click → /archetypes/:id
```

### Detail layout (`/archetypes/:id`)

```
[Breadcrumb] Archetypes / <archetype name>

[Hero — split]
  Left:  Archetype name (serif H1), strategy tag chip, color identity pips
         Description (1–2 sentences; sourced from API or hand-curated)
         Stat row: share / winrate / sample / first seen (date)
  Right: Color identity ring chart OR cluster centroid viz (small graph viz reused)

[Tabs]  Decklists | Cards | Trends | Tournaments

  Decklists:  Paginated list of decklists in this cluster, sorted by recency / placement
              Each row: tournament name · date · pilot · placement · → /decklists/:id
  Cards:      Staples breakdown — which cards appear in >X% of decks in this archetype
              Two columns: "Always run" (90%+) | "Often run" (50–90%)
              Card rows: name (serif), inclusion %, sparkline of inclusion over time
  Trends:     Line chart of this archetype's share over time (last 12 months)
              Optional: small-multiples of card inclusion trends
  Tournaments: Where this archetype has placed, table view
```

### Data
- `GET /api/archetypes?filters=...` → `[{ id, name, commanders, colors, strategy, share, winrate, samples, sample_decklist_id }]`
- `GET /api/archetypes/:id` → full detail
- `GET /api/archetypes/:id/cards` → `[{ card_name, inclusion_pct, trend: [...] }]`
- `GET /api/archetypes/:id/decklists?page=...` → paginated decklists
- `GET /api/archetypes/:id/share-over-time` → time-series

---

## `/decklists` — Decklists index + detail

### Purpose
Searchable corpus of every indexed decklist with full tournament context.

### Index layout

```
[Page header]
  Eyebrow:  "96,231 decklists indexed"
  Title:    "Every list. Every result."
  Search bar (large; supports `commander:X color:UW pilot:Y`)

[Filter rail — sticky left]
  Same color/strategy/format filters as Archetypes
  Plus: Pilot, Tournament, Date range, Placement (top 8 / top 16 / etc.)

[Table — virtualized]
  Cols: Pilot · Commander pair (pips + names) · Archetype · Tournament · Date · Placement
  Sortable headers; row click → /decklists/:id
  Dense but readable: 48px row height, hairline dividers, hover bg `rgba(255,255,255,0.02)`
```

### Detail layout (`/decklists/:id`)

```
[Breadcrumb] Decklists / <pilot name> @ <tournament>

[Hero]
  Commander pair (serif H2 + pips)
  Pilot · Archetype (link) · Tournament (link) · Placement (chip)
  Date

[Body — 2 columns]
  Left (8/12):   Decklist
    Grouped by category (Commander · Creatures · Spells · Artifacts · Enchantments · Lands · Sideboard)
    Each card: name (sans 14px), CMC (mono, dim, right-aligned), quantity if not 1
    Click a card → side drawer with card detail (oracle text, inclusion rate in this archetype, etc.)
  Right (4/12):  Meta sidebar
    Mana curve histogram
    Color identity pie
    "Cards unique to this list" — cards in this deck not in the archetype's "Always run" set
```

### Data
- `GET /api/decklists?filters=...&page=...` → paginated rows for the table
- `GET /api/decklists/:id` → `{ pilot, tournament, archetype, commanders, cards: { commander: [...], creatures: [...], ... } }`
- `GET /api/cards/:name` → for the side drawer

---

## `/tournaments` — Tournaments index + detail

### Purpose
Past and upcoming tournament results.

### Index layout

```
[Page header]
  Eyebrow:  "Duel Commander · Tournaments"
  Title:    "Where the format gets decided."
  Toggle:   [Recent · Upcoming]

[Featured row — 1 large card]
  Most recent major tournament: name, date, winner archetype, link to results

[List]
  Two-column grid of tournament cards
  Each card:
    - Tournament name (serif)
    - Date · location · player count (mono row)
    - Winning archetype with pips
    - Top 3–4 archetypes by representation (small chips)
```

### Detail (`/tournaments/:id`)

```
[Hero] Tournament name, date, location, player count, format
[Tabs] Standings | Metagame breakdown | Decklists

  Standings:  Full results table, placement / pilot / record / archetype
  Metagame breakdown:  Share of archetypes in the field (vs. day-of)
                       Conversion: which archetypes over/underperformed (entered → top 8)
  Decklists:  All published decklists from this tournament
```

### Data
- `GET /api/tournaments?status=recent|upcoming&page=...`
- `GET /api/tournaments/:id`
- `GET /api/tournaments/:id/standings`
- `GET /api/tournaments/:id/metagame`

---

## `/trends` — Time-series & forecasts

### Purpose
The "research" surface — view how the format has evolved.

### Layout

```
[Page header]
  Eyebrow:  "Research · Trends"
  Title:    "The metagame, over time."
  Controls: [Time window: 90d / 6m / 1y / all] [Granularity: weekly / monthly]

[Chart 1 — full width]
  Archetype share over time (stacked area)
  Legend below: top 10 archetypes, toggleable
  Hover: vertical guide + tooltip showing share at that point

[Chart 2 — full width]
  Card inclusion trends
  Allow user to add up to 6 cards to compare
  Line chart, each card a different shade of accent + ink

[Forecasts section]
  Eyebrow: "Forecasts · 4-week projection"
  3-card row:
    - "Rising" — 3 archetypes with positive projected delta
    - "Falling" — 3 with negative
    - "Stable" — 3 holding
  Each card has a sparkline + forecast confidence interval (faint band)
```

### Data
- `GET /api/trends/archetypes?window=...&granularity=...`
- `GET /api/trends/cards?names=...&window=...`
- `GET /api/forecasts/archetypes?horizon=4w`

---

## Cross-cutting components

These appear across multiple pages — build them once.

- **`<Pips>`** — color-identity pip cluster. `<Pips colors="UW" />` renders 5×5 circles in WUBRG order. Use small letterforms or solid dots; **don't recreate the actual MTG mana symbols.** Suggested: solid 6px dots, white-cream / cyan / dark / red-orange / green using the accent system.
- **`<CommanderName>`** — pair-aware. `<CommanderName commanders={[a, b]} />` renders `Tymna the Weaver / Thrasios, Triton Hero` (slash separator for partners, "+" for backgrounds).
- **`<Sparkline>`** — 80×24px line chart, no axes.
- **`<Eyebrow>`** — the dot+chip thing from the landing page; reuse everywhere a section starts.
- **`<StatBlock>`** — serif number + uppercase mono label.
- **`<TelemetryCallout>`** — mono eyebrow + italic serif main; pair with any chart or viz.
- **`<TableSkeleton>`, `<CardSkeleton>`** — loading states. Use `--line` background with a subtle shimmer animation.

## Empty / error / loading

- **Loading**: never spinners — use skeletons that match the destination layout
- **Empty**: serif H3 + sans subhead + ghost CTA. Match the "Tolaria" tone — e.g. "The archives are empty for this query." rather than "No results."
- **Error**: mono "ERR-{code}" eyebrow + serif title + retry button. Don't over-design errors.

## Responsive

- Desktop is the primary canvas (1440 wide max content)
- Tablet (768–1199): collapse 2-col splits to 1 col; filter rails go above content as a chip row
- Mobile (< 768): single column everywhere; the landing node-graph viz hides on mobile (it doesn't read at small sizes — the headline + CTAs carry the page on their own); inner-page filter rails become a dropdown
