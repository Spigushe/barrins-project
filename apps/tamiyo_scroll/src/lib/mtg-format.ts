import type {
  ArchetypeCategory,
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

export const SESSION_TYPE_LABELS: Record<SessionType, string> = {
  tournament: 'Tournament',
  training: 'Training',
}

/** Shared by the Sessions tab and the match journal's session tag (S9). */
export const SESSION_TYPE_BADGE_VARIANT: Record<SessionType, 'tournament' | 'success'> = {
  tournament: 'tournament',
  training: 'success',
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

export const DECKLIST_VERSION_SOURCE_LABELS: Record<DecklistVersionSource, string> = {
  manual: 'Manual entry',
  moxfield_import: 'Moxfield import',
}
