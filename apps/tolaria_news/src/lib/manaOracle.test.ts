import { describe, expect, it } from 'vitest'
import { manaValue, requiredPips, runSimulation, wilsonInterval } from './manaOracle'

/** Tiny seeded PRNG so simulation runs are reproducible in tests. Inline
 * (≈4 lines) rather than a dependency, per constitution §22.3. */
function mulberry32(seed: number): () => number {
  let a = seed
  return () => {
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

describe('manaValue', () => {
  it('sums digits and counts each C as one pip of mana value', () => {
    expect(manaValue('1CC')).toBe(3)
    expect(manaValue('3')).toBe(3)
    expect(manaValue('2CCC')).toBe(5)
    expect(manaValue('')).toBe(0)
  })
})

describe('requiredPips', () => {
  it('counts the coloured pips', () => {
    expect(requiredPips('1CC')).toBe(2)
    expect(requiredPips('4')).toBe(0)
    expect(requiredPips('CCCC')).toBe(4)
  })
})

describe('wilsonInterval', () => {
  it('brackets the point estimate for 50/100', () => {
    const [low, high] = wilsonInterval(50, 100)
    expect(low).toBeCloseTo(0.4038, 3)
    expect(high).toBeCloseTo(0.5962, 3)
  })

  it('returns the whole range when there are no games', () => {
    expect(wilsonInterval(0, 0)).toEqual([0, 1])
  })
})

describe('runSimulation', () => {
  it('is deterministic under a seeded RNG', () => {
    const params = { lands: 39, colority: '1CC', simulations: 2000 }
    const first = runSimulation(params, mulberry32(42))
    const second = runSimulation(params, mulberry32(42))

    expect(first).toEqual(second)
    expect(first.found).toBe(true)
    if (first.found) {
      // Wide smoke bound — the real assertion is the run-to-run equality
      // above. This model is demanding by design (only "good" lands cast the
      // spell, judged at the 90% CI lower bound), so the count runs high.
      expect(first.goodLands).toBeGreaterThanOrEqual(8)
      expect(first.goodLands).toBeLessThanOrEqual(36)
      expect(first.targetTurn).toBe(3)
      expect(first.requiredPips).toBe(2)
      expect(first.discardedGames + first.relevantGames).toBe(2000)
    }
  })

  it('reports progress from 0 toward 1', () => {
    const fractions: number[] = []
    runSimulation({ lands: 39, colority: '1CC', simulations: 200 }, mulberry32(1), (f) =>
      fractions.push(f),
    )
    expect(fractions.length).toBeGreaterThan(0)
    expect(fractions[0]).toBeGreaterThan(0)
    expect(fractions[fractions.length - 1]).toBeLessThanOrEqual(1)
    expect([...fractions]).toEqual([...fractions].sort((a, b) => a - b))
  })

  it('needs zero coloured sources for a colourless cost', () => {
    const out = runSimulation(
      { lands: 39, colority: '3', simulations: 1500 },
      mulberry32(1),
    )
    expect(out.found).toBe(true)
    if (out.found) expect(out.goodLands).toBe(0)
  })

  it('reports not-found without NaN when every hand is mana-screwed', () => {
    const out = runSimulation(
      { lands: 2, colority: '6CCC', simulations: 400 },
      mulberry32(7),
    )
    expect(out.found).toBe(false)
    if (!out.found) {
      expect(out.everyGameDiscarded).toBe(true)
      expect(Number.isNaN(out.targetTurn)).toBe(false)
    }
  })
})
