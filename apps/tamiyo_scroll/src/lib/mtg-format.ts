import type {
  ArchetypeCategory,
  DecklistLineStatus,
  DecklistVersionSource,
  ExpectedLevel,
  GameResult,
} from '@/schemas/tamiyoScroll'

export const ARCHETYPE_LABELS: Record<ArchetypeCategory, string> = {
  aggro: 'Aggro',
  midrange: 'Midrange',
  control: 'Control',
  combo: 'Combo',
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
  as_expected: 'Comme attendu',
  more_expected: 'Plus attendu',
  less_expected: 'Moins attendu',
}

export const GAME_RESULT_LABELS: Record<GameResult, string> = {
  win: 'Victoire',
  loss: 'Défaite',
  draw: 'Nul',
}

/** Les pourcentages backend (conversion, winrate) sont déjà exprimés en base 100. */
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
  1: 'Mauvais',
  2: 'Faible',
  3: 'Moyen',
  4: 'Bon',
  5: 'Excellent',
}

/** Échelle 1-5 "Mauvais → Excellent" — même dégradé que les bandes de winrate. */
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

export const DECKLIST_LINE_STATUS_LABELS: Record<DecklistLineStatus, string> = {
  validated: 'Validé',
  rejected: 'Rejeté',
  in_test: 'En test',
  neutral: 'Neutre',
}

export const DECKLIST_LINE_STATUS_TEXT_CLASS: Record<DecklistLineStatus, string> = {
  validated: 'text-success',
  rejected: 'text-destructive',
  in_test: 'text-warning',
  neutral: 'text-foreground',
}

export const DECKLIST_VERSION_SOURCE_LABELS: Record<DecklistVersionSource, string> = {
  manual: 'Saisie manuelle',
  moxfield_import: 'Import Moxfield',
}
