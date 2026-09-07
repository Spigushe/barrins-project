import type { TournamentSummary } from '@/schemas/tolariaNews'

/**
 * MTGO League pages publish no player-count header, so the scraper stores
 * `players: 0` for them. That is "not reported", not a real turnout of zero,
 * and rendering a literal `0` reads as the latter.
 *
 * This is the display-side mirror of the backend's own league test
 * (`apps/barrins_api/app/services/tolaria_news/decks.py::size_bucket_condition`,
 * bucket `"leagues"`): source `mtgo`, `players == 0`, name contains `"League"`.
 * Keep the two in step -- the backend owns the rule, this only decides how the
 * already-classified value is shown.
 */
export function isMtgoLeagueWithoutPlayerCount(
  tournament: Pick<TournamentSummary, 'source' | 'players' | 'name'>,
): boolean {
  return (
    tournament.source === 'mtgo' &&
    tournament.players === 0 &&
    tournament.name.includes('League')
  )
}
