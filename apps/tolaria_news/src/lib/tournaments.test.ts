import { describe, expect, it } from 'vitest'
import { isMtgoLeagueWithoutPlayerCount } from './tournaments'

const base = { source: 'mtgo', players: 0, name: 'Duel Commander League' } as const

describe('isMtgoLeagueWithoutPlayerCount', () => {
  it('is true for an MTGO League with no reported player count', () => {
    expect(isMtgoLeagueWithoutPlayerCount(base)).toBe(true)
  })

  it('is false once the League actually reports a player count', () => {
    expect(isMtgoLeagueWithoutPlayerCount({ ...base, players: 16 })).toBe(false)
  })

  it('is false for a non-League MTGO event that reports 0 (an ingestion anomaly, not a league)', () => {
    expect(
      isMtgoLeagueWithoutPlayerCount({ ...base, name: 'Duel Commander Challenge' }),
    ).toBe(false)
  })

  it('is false for a non-MTGO source even when the name contains "League"', () => {
    expect(isMtgoLeagueWithoutPlayerCount({ ...base, source: 'mtgtop8' })).toBe(false)
  })
})
