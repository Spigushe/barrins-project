import type { RenderResult } from '@testing-library/react'

/**
 * Shared expectations for the "reuse, don't fork" check (S7): the same
 * fixture-derived values must show up in `MetagameTab`/`SuiviBo3Tab`/
 * `DecklistTab` regardless of which data-source mechanism fed them — see
 * `reuse.demo-mode.test.tsx` (real hooks + real `src/api/*.ts` + the demo
 * fetch interceptor) and `reuse.mocked-backend.test.tsx` (real hooks, but
 * `src/api/*.ts` swapped directly for the demo module — standing in for "a
 * real backend that happens to return this same data"). Keeping the
 * expectations in one place means both files are checking the exact same
 * thing, just arrived at differently.
 */

export async function expectMetagameTabRendersFixtureData(
  view: RenderResult,
): Promise<void> {
  // ArchetypeSummarySection / MatchupSummarySection — plain text.
  await view.findAllByText('Golgari Midrange')
  await view.findByText('Breakdown by archetype')
  await view.findByText('Match-up summary')
  // MetaDecksRosterSection — deck names render as <Input> values.
  await view.findByDisplayValue('Azorius Control')
}

export async function expectSuiviBo3TabRendersFixtureData(
  view: RenderResult,
): Promise<void> {
  await view.findAllByText('Golgari Midrange')
  // The session badge on the two matches attached to the seeded session.
  await view.findAllByText('Tournament: Store Championship')
}

export async function expectDecklistTabRendersFixtureData(
  view: RenderResult,
): Promise<void> {
  // Qty and name render as separate table cells now (structured
  // Commander/Library view, not one raw "<qty> <name>" text line).
  await view.findByText('Aurelia, the Warleader')
  await view.findByText('Version 2')
  await view.findByText('Tested cards — card log')
}
