/**
 * tolaria_news — BFF response types.
 * Companion to BFF.md. Keep in sync; CI validates fixtures against these.
 * Copy into the app as `src/api/types.ts` (and mirror as zod schemas for runtime validation).
 */

/* ─── envelope ─────────────────────────────────────────────────────────── */

export interface Envelope<T> {
  data: T;
  meta: Meta;
  page?: Page;
}

export interface Meta {
  generated_at: string;        // ISO 8601 UTC
  source_synced_at: string;    // drives the bottom-rail "last sync" stamp
  cache: "hit" | "miss" | "stale-while-revalidate";
  window?: TimeWindow;
  partial?: string[];          // sections that failed and were omitted
  facets?: Record<string, Record<string, number>>;
}

export interface Page {
  next_cursor: string | null;
  limit: number;
  total?: number;
}

export interface ApiError {
  error: {
    code:
      | "ERR-BAD-PARAM" | "ERR-NOT-FOUND" | "ERR-QUERY-SYNTAX"
      | "ERR-RATE-LIMIT" | "ERR-UPSTREAM" | "ERR-UPSTREAM-TIMEOUT" | "ERR-COLD";
    message: string;
    detail?: string | { position?: number; [k: string]: unknown };
    retryable: boolean;
    request_id: string;
  };
}

/* ─── primitives ───────────────────────────────────────────────────────── */

export type Color = "W" | "U" | "B" | "R" | "G";
export type ColorIdentity = Color[];                       // canonical WUBRG order
export type TimeWindow = "7d" | "30d" | "90d" | "season" | "6m" | "1y" | "all";
export type Granularity = "weekly" | "monthly";
export type Tier = "all" | "mid" | "top8";
export type Strategy = "control" | "aggro" | "midrange" | "combo" | "stax" | "tempo";

export interface Commander {
  name: string;
  scryfall_id: string;
  partner_kind?: "partner" | "partner_with" | "background" | "friends_forever";
}

export interface ArchetypeRef {
  id: string;                  // slug
  name: string;
  colors: ColorIdentity;
}

export interface SeriesPoint { t: string; v: number }
export interface Series { points: SeriesPoint[]; granularity: Granularity }

/* ─── /landing ─────────────────────────────────────────────────────────── */

export interface LandingData {
  stats: {
    tournaments_parsed: number;
    archetypes_mapped: number;
    decklists_indexed: number;
  };
  season: { label: string; started_on: string };
  telemetry: { label: string; value: string; note?: string }[];
  /** Absent → client falls back to the procedural layout in graph.jsx */
  embedding?: {
    nodes: { id: string; x: number; y: number; weight: number; archetype?: ArchetypeRef }[];
    edges: [number, number][];
  };
}

/* ─── /metagame ────────────────────────────────────────────────────────── */

export interface ArchetypeRow {
  archetype: ArchetypeRef;
  share: number;               // 0..1
  prev_share: number | null;   // null → new this window
  delta: number;
  winrate: number;
  samples: number;
  sparkline?: Series;
}

export interface MoverRow {
  archetype: ArchetypeRef;
  delta: number;
  sparkline: Series;
}

export interface MetagameData {
  totals: {
    tournaments: number;
    decks: number;
    top_commander: { name: string; share: number };
  };
  archetypes: ArchetypeRow[];           // ≤ 60; tail folded into id "other"
  colors: Record<Color, number>;        // sums to 1
  movers: { up: MoverRow[]; down: MoverRow[] };
}

/* ─── /archetypes ──────────────────────────────────────────────────────── */

export interface ArchetypeCard {
  id: string;
  name: string;
  colors: ColorIdentity;
  commanders: Commander[];
  strategy: Strategy;
  share: number;
  winrate: number;
  samples: number;
  staples_preview: string[];
}

export interface ArchetypeDetail {
  id: string;
  name: string;
  colors: ColorIdentity;
  commanders: Commander[];
  strategy: Strategy;
  description?: string;
  stats: { share: number; winrate: number; samples: number; first_seen: string };
  share_over_time: Series;
  centroid?: {
    x: number; y: number;
    neighbors: { archetype: ArchetypeRef; distance: number }[];
  };
  decklists: { items: DecklistRow[]; next_cursor: string | null };
}

export interface CardInclusion {
  name: string;
  scryfall_id?: string;
  inclusion: number;           // 0..1
  trend?: Series;
}

export interface ArchetypeCards {
  always_run: CardInclusion[];  // ≥ 0.90
  often_run: CardInclusion[];   // 0.50 – 0.90
  flex: CardInclusion[];        // 0.15 – 0.50
}

/* ─── /decklists ───────────────────────────────────────────────────────── */

export interface DecklistRow {
  id: string;
  pilot: string;
  commanders: Commander[];
  colors: ColorIdentity;
  archetype: ArchetypeRef;
  tournament: { id: string; name: string; date: string };
  placement: number;
  player_count: number;
}

export interface DeckCard {
  name: string;
  qty: number;
  cmc: number;
  scryfall_id: string;
  type_line: string;
}

export type DeckSection =
  | "commander" | "creatures" | "spells" | "artifacts"
  | "enchantments" | "planeswalkers" | "lands";

export interface DecklistDetail {
  id: string;
  pilot: string;
  commanders: Commander[];
  archetype: ArchetypeRef;
  tournament: {
    id: string; name: string; date: string;
    location: string; player_count: number;
  };
  placement: number;
  record?: string;
  published_at: string;
  cards: Record<DeckSection, DeckCard[]>;
  analysis: {
    mana_curve: { cmc: number; count: number }[];
    color_split: Partial<Record<Color, number>>;
    unique_cards: string[];
  };
}

export interface CardDetail {
  scryfall_id: string;
  name: string;
  mana_cost: string;
  cmc: number;
  type_line: string;
  oracle_text: string;
  image_url: string;           // BFF-proxied, never a raw Scryfall URL
  inclusion_in_archetype?: number;
}

/* ─── /tournaments ─────────────────────────────────────────────────────── */

export interface TournamentCard {
  id: string;
  name: string;
  date: string;
  location: string;
  player_count: number;
  status: "completed" | "upcoming" | "in_progress";
  winner?: { pilot: string; archetype: ArchetypeRef; decklist_id: string };
  top_archetypes: { archetype: ArchetypeRef; share: number }[];
}

export interface TournamentsData {
  featured?: TournamentCard;   // page 1 of status=recent only
  items: TournamentCard[];
}

export interface StandingRow {
  placement: number;
  pilot: string;
  record: string;
  archetype: ArchetypeRef;
  decklist_id?: string;
}

export interface TournamentMetagame {
  field: { archetype: ArchetypeRef; entered: number; top8: number; conversion: number }[];
}

/* ─── /trends & /forecasts ─────────────────────────────────────────────── */

export interface TrendsData {
  buckets: string[];                                        // e.g. ["2026-01", …]
  series: { archetype: ArchetypeRef; points: number[] }[];  // index-aligned to buckets
  other?: number[];                                         // keeps the stack at 1.0
}

export interface CardTrendsData {
  buckets: string[];
  series: { name: string; scryfall_id?: string; points: number[] }[];
}

export interface Forecast {
  archetype: ArchetypeRef;
  projected_delta: number;
  confidence: { low: number; high: number };
  sparkline: Series;
}

export interface ForecastsData {
  rising: Forecast[];
  falling: Forecast[];
  stable: Forecast[];
}

/* ─── /search ──────────────────────────────────────────────────────────── */

export interface SearchData {
  archetypes: ArchetypeRef[];
  commanders: { name: string; scryfall_id: string; archetype_count: number }[];
  tournaments: { id: string; name: string; date: string }[];
  pilots: { name: string; decklist_count: number }[];
}

/* ─── /meta/health ─────────────────────────────────────────────────────── */

export interface HealthData {
  status: "ok" | "degraded" | "down";
  upstream: "ok" | "degraded" | "down";
  source_synced_at: string;
  build: string;
}

/* ─── route → response map ─────────────────────────────────────────────── */

export interface BffRoutes {
  "/landing": LandingData;
  "/metagame": MetagameData;
  "/archetypes": ArchetypeCard[];
  "/archetypes/:id": ArchetypeDetail;
  "/archetypes/:id/cards": ArchetypeCards;
  "/archetypes/:id/decklists": DecklistRow[];
  "/archetypes/:id/trends": TrendsData;
  "/decklists": DecklistRow[];
  "/decklists/:id": DecklistDetail;
  "/cards/:scryfall_id": CardDetail;
  "/tournaments": TournamentsData;
  "/tournaments/:id": TournamentCard;
  "/tournaments/:id/standings": StandingRow[];
  "/tournaments/:id/metagame": TournamentMetagame;
  "/trends": TrendsData;
  "/trends/cards": CardTrendsData;
  "/forecasts": ForecastsData;
  "/search": SearchData;
  "/meta/health": HealthData;
}
