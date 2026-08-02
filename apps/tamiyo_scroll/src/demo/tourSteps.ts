export type DemoTabKey = 'metagame' | 'tracker' | 'decklist'

export interface TourStep {
  tab: DemoTabKey
  /** Exact text of the section's `<h2>` (its `CardTitle`) the tour points at. */
  heading: string
  title: string
  description: string
}

/**
 * Every step targets a heading that is always present once the demo's fixed
 * personal deck is selected (see `DemoModeProvider`) — no step points at
 * conditional/empty-state content.
 */
export const TOUR_STEPS: TourStep[] = [
  {
    tab: 'metagame',
    heading: 'Breakdown by archetype',
    title: 'Metagame breakdown',
    description:
      'Average win rate against every archetype you have faced, grouped by role (aggro, midrange, control, combo).',
  },
  {
    tab: 'metagame',
    heading: 'Match-up summary',
    title: 'Match-up detail',
    description:
      'Per-opponent win rates, split between on-the-play and on-the-draw, with game counts.',
  },
  {
    tab: 'metagame',
    heading: 'Deck roster (MUR)',
    title: 'Meta deck roster',
    description:
      'The decks you expect to face this season — tier, archetype and notes. Try editing a row; it will not be saved.',
  },
  {
    tab: 'tracker',
    heading: 'New game (BO3)',
    title: 'Log a best-of-three',
    description:
      'Record a new match against any roster deck, game by game. Fill it in and save it — this demo resets on reload.',
  },
  {
    tab: 'tracker',
    heading: 'Match log',
    title: 'Match history',
    description: 'Every logged game, with a quick view, edit or delete.',
  },
  {
    tab: 'decklist',
    heading: 'Tested cards — individual feedback',
    title: 'Card testing',
    description:
      'Individual feedback on cards being tested, rated by effectiveness and matchup.',
  },
  {
    tab: 'decklist',
    heading: 'Current decklist',
    title: 'Current decklist',
    description: 'The latest saved version of the decklist, annotated by test status.',
  },
  {
    tab: 'decklist',
    heading: 'Version history',
    title: 'Version history',
    description: 'Every saved version of the decklist, most recent first.',
  },
]
