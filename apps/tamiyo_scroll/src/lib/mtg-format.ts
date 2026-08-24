import type { CSSProperties } from 'react'
import type {
  ArchetypeCategory,
  CardGame,
  DecklistLineStatus,
  DecklistVersionSource,
  ExpectedLevel,
  GameResult,
  SessionType,
} from '@/schemas/tamiyoScroll'

export const ARCHETYPE_LABELS: Record<ArchetypeCategory, string> = {
  aggro: 'Aggro',
  midrange: 'Midrange',
  control: 'Control',
  combo: 'Combo',
}

export const CARD_GAME_LABELS: Record<CardGame, string> = {
  magic: 'Magic: The Gathering',
  yu_gi_oh: 'Yu-Gi-Oh!',
  pokemon: 'Pokémon TCG',
  flesh_and_blood: 'Flesh and Blood',
  one_piece: 'One Piece Card Game',
  lorcana: 'Disney Lorcana',
  star_wars_unlimited: 'Star Wars: Unlimited',
  digimon: 'Digimon Card Game',
  cardfight_vanguard: 'Cardfight!! Vanguard',
  riftbound: 'Riftbound',
  other: 'Other',
}

export const SESSION_TYPE_LABELS: Record<SessionType, string> = {
  tournament: 'Tournament',
  training: 'Training',
}

/** Shared by the Sessions tab and the match journal's session tag (S9). */
export const SESSION_TYPE_BADGE_VARIANT: Record<SessionType, 'tournament' | 'success'> = {
  tournament: 'tournament',
  training: 'success',
}

/**
 * S14 item 6: a session's freeform hue (0-359), when set, replaces
 * `SESSION_TYPE_BADGE_VARIANT`'s type-based color on every session tag in
 * the app (Sessions tab row/summary, archived-sessions list, Match
 * journal tag — see `SessionTypeBadge`). `null` means no override —
 * callers fall back to the type-based variant.
 */
export function sessionHueBadgeStyle(hue: number | null): CSSProperties | undefined {
  if (hue === null) return undefined
  return {
    backgroundColor: `hsl(${hue.toString()} 70% 50% / 0.18)`,
    borderColor: `hsl(${hue.toString()} 70% 45%)`,
    // Bright text, not dark: the app is dark-theme-only (index.css), so a
    // low lightness here (previously 25%) was reading as near-invisible
    // against the page background regardless of hue.
    color: `hsl(${hue.toString()} 75% 75%)`,
  }
}

export const ARCHETYPE_TEXT_CLASS: Record<ArchetypeCategory, string> = {
  aggro: 'text-archetype-aggro',
  midrange: 'text-archetype-midrange',
  control: 'text-archetype-control',
  combo: 'text-archetype-combo',
}

export const ARCHETYPE_BORDER_CLASS: Record<ArchetypeCategory, string> = {
  aggro: 'border-archetype-aggro',
  midrange: 'border-archetype-midrange',
  control: 'border-archetype-control',
  combo: 'border-archetype-combo',
}

export const EXPECTED_LABELS: Record<ExpectedLevel, string> = {
  as_expected: 'As expected',
  more_expected: 'More than expected',
  less_expected: 'Less than expected',
}

export const GAME_RESULT_LABELS: Record<GameResult, string> = {
  win: 'Win',
  loss: 'Loss',
  draw: 'Draw',
}

/** Backend percentages (conversion, winrate) are already expressed on a 0-100 scale. */
export function formatPercent(value: number | null): string {
  if (value === null) return '—'
  return `${String(Math.round(value))}%`
}

export function winrateTextClass(value: number | null): string {
  if (value === null) return 'text-muted-foreground'
  if (value >= 80) return 'text-winrate-80'
  if (value >= 60) return 'text-winrate-60'
  if (value >= 40) return 'text-winrate-40'
  if (value >= 20) return 'text-winrate-20'
  return 'text-winrate-0'
}

/** S12 item 8's opt-in match-up row tint — reuses the same "Very negative"
 * (0-19%) / "Very positive" (80-100%) thresholds as `winrateTextClass`
 * and `WINRATE_BANDS`, applied at the row level instead of the cell
 * level. A low-opacity fill (not a solid one) so per-cell winrate text
 * colors and shared/multi-share badges sitting on top stay legible.
 * Middle bands and `null` (no data yet) get no tint. */
export function winrateRowTintClass(value: number | null): string {
  if (value === null) return ''
  if (value >= 80) return 'bg-success/10'
  if (value < 20) return 'bg-destructive/10'
  return ''
}

/** S12 item 9's opt-in "2W / 0L" result format — parses the backend's
 * always-`"wins-losses"` string (`stats.py`'s `_ratio()`) client-side.
 * Draws aren't possible in a BO3 match count, so a two-part split is
 * safe. Returns the original string unchanged when the format is off
 * (default). */
export function formatMatchRatio(ratio: string, use2w0lFormat: boolean): string {
  if (!use2w0lFormat) return ratio
  const [wins, losses] = ratio.split('-')
  return `${wins}W / ${losses}L`
}

/** S12 item 11's 3-color tier background scale — no existing tier→color
 * mapping to reuse (unlike the archetype colors or winrate bands), so
 * this groups the `TIERS` scale (`[0, 0.5, 1, 1.5, 2, 2.5, 3]`) into
 * three bands: 0/0.5/1 read as strong (green), 1.5/2 as middling
 * (amber), 2.5/3 as weak (red) — loosely mirroring the winrate
 * palette's good/mid/bad framing, same low-opacity tint convention as
 * `winrateRowTintClass`. */
export function tierBackgroundClass(tier: number): string {
  if (tier <= 1) return 'bg-success/10'
  if (tier <= 2) return 'bg-warning/10'
  return 'bg-destructive/10'
}

export const RATING_LABELS: Record<number, string> = {
  1: 'Bad',
  2: 'Weak',
  3: 'Average',
  4: 'Good',
  5: 'Excellent',
}

/** 1-5 scale "Bad → Excellent" — same gradient as the winrate bands. */
export function ratingTextClass(rating: number): string {
  if (rating >= 5) return 'text-winrate-80'
  if (rating >= 4) return 'text-winrate-60'
  if (rating >= 3) return 'text-winrate-40'
  if (rating >= 2) return 'text-winrate-20'
  return 'text-winrate-0'
}

export const GAME_RESULT_BORDER_CLASS: Record<GameResult, string> = {
  win: 'border-l-success',
  loss: 'border-l-destructive',
  draw: 'border-l-warning',
}

export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-')
  return `${day}/${month}/${year}`
}

export function formatDateTime(isoDateTime: string): string {
  return new Date(isoDateTime).toLocaleDateString('fr-FR')
}

/** Shared by both S5 session-report download entry points (row icon + summary button). */
export function sessionReportFilename(session: { name: string }): string {
  const slug = session.name.trim().toLowerCase().replace(/\s+/g, '-')
  return `session-report-${slug}.pdf`
}

/** S5's deck-level (no-session, last-30-days) report download entry point. */
export function deckReportFilename(deck: { name: string }): string {
  const slug = deck.name.trim().toLowerCase().replace(/\s+/g, '-')
  return `deck-report-${slug}.pdf`
}

/** S2's cumulative team-deck report — one PDF per flagged name, not per owner. */
export function teamDeckReportFilename(deck: { deck_name: string }): string {
  const slug = deck.deck_name.trim().toLowerCase().replace(/\s+/g, '-')
  return `team-deck-report-${slug}.pdf`
}

export const DECKLIST_LINE_STATUS_LABELS: Record<DecklistLineStatus, string> = {
  validated: 'Validated',
  rejected: 'Rejected',
  in_test: 'In test',
  neutral: 'Neutral',
}

export const DECKLIST_LINE_STATUS_TEXT_CLASS: Record<DecklistLineStatus, string> = {
  validated: 'text-success',
  rejected: 'text-destructive',
  in_test: 'text-warning',
  neutral: 'text-foreground',
}

/**
 * Literal `bg-*` classes, kept as their own map rather than derived from
 * `DECKLIST_LINE_STATUS_TEXT_CLASS` via a `text-` → `bg-` string replace:
 * Tailwind's scanner only generates utilities it finds as literal strings
 * in source, so a runtime-computed class name never gets built.
 */
export const DECKLIST_LINE_STATUS_BG_CLASS: Record<DecklistLineStatus, string> = {
  validated: 'bg-success',
  rejected: 'bg-destructive',
  in_test: 'bg-warning',
  neutral: 'bg-foreground',
}

export const DECKLIST_VERSION_SOURCE_LABELS: Record<DecklistVersionSource, string> = {
  manual: 'Manual entry',
  moxfield_import: 'Moxfield import',
}
