/**
 * "Tolaria West" easter egg — a Monte Carlo mana-source calculator.
 *
 * This is a straight port of a standalone HTML toy the author wrote years
 * ago: given a deck's land count and a spell's "colority", it answers how
 * many of those lands must produce the required colour for the spell to be
 * castable on curve with ~90% reliability.
 *
 * It runs entirely in the browser (a Web Worker — see `manaOracle.worker.ts`)
 * and is a deliberate, documented exception to constitution §4.1 "backend
 * owns business logic": it is a generic Magic: the Gathering probability toy,
 * touches no ecosystem data, persists nothing, and duplicates no rule that
 * exists anywhere else in the codebase. §48 (don't build unused APIs for a
 * hidden feature) is why it isn't a backend service.
 *
 * The simulation model is preserved from the original. Four defects were
 * fixed in the port (see the feature doc): the sim-count ceiling now agrees
 * with the input, a zero-simulation run can no longer divide by zero, the
 * hand is reset between mulligan iterations, and the mulligan keep decision
 * is evaluated on the hand actually kept.
 */

/** "Colority" notation: bare digits are generic mana, each `C` is one pip of
 * the single colour you care about. It is NOT a real mana cost — multi-digit
 * runs are summed per character, exactly as the original toy did (`"12"` → 3),
 * because the field was only ever meant for short strings like `1CC`. */
export interface OracleParams {
  /** Total lands in the 99-card singleton deck. */
  lands: number
  /** Colority string, e.g. `1CC`. */
  colority: string
  /** Games to simulate per candidate source count. */
  simulations: number
}

export interface OracleResult {
  found: true
  /** Fewest colour-producing lands that clear the 90% confidence bar. */
  goodLands: number
  /** Turn the spell is wanted on (its colority mana value). */
  targetTurn: number
  /** Colour pips that must be in play (count of `C`). */
  requiredPips: number
  colority: string
  /** Success share over non-discarded games, 0..1. */
  successRate: number
  /** Half-width of the 95% Wilson score interval, 0..1. */
  ciHalfWidth: number
  /** Games that reached the target turn with enough lands to be judged. */
  relevantGames: number
  /** Games thrown out for missing land drops by the target turn. */
  discardedGames: number
  simulations: number
}

export interface OracleNotFound {
  found: false
  targetTurn: number
  requiredPips: number
  colority: string
  simulations: number
  /** Highest source count the sweep tried before giving up. */
  maxGoodLandsTried: number
  /** True when every simulated game was discarded (pure mana screw) — the
   * caller shows a different message for this than for "close but never 90%". */
  everyGameDiscarded: boolean
}

const GOOD = 0
const OTHER = 1
const SPELL = 2

const IRRELEVANT = 0
const FAILURE = 1
const SUCCESS = 2

const DECK_SIZE = 99
const CONFIDENCE_TARGET = 0.9

interface Hand {
  good: number
  other: number
  spell: number
}

/** Colority mana value — the turn the spell is wanted on. Summed per
 * character (each `C` = 1), preserving the original toy's behaviour. */
export function manaValue(colority: string): number {
  let total = 0
  for (const ch of colority) {
    if (ch === 'C' || ch === 'c') {
      total += 1
    } else {
      const digit = Number(ch)
      if (!Number.isNaN(digit)) total += digit
    }
  }
  return total
}

/** Colour pips that must be in play — the count of `C` in the colority. */
export function requiredPips(colority: string): number {
  let count = 0
  for (const ch of colority) {
    if (ch === 'C' || ch === 'c') count += 1
  }
  return count
}

/**
 * 95% Wilson score interval for `successes` out of `n` Bernoulli trials.
 * Ported verbatim from the original toy (`computeUncertainty`), including
 * the `n === 0` guard that returns the whole `[0, 1]` range.
 */
export function wilsonInterval(successes: number, n: number): [number, number] {
  if (n === 0) return [0, 1]

  const p = successes / n
  const z = 1.96
  const denominator = 1 + (z * z) / n
  const center = (p + (z * z) / (2 * n)) / denominator
  const margin = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / denominator

  return [center - margin, center + margin]
}

function makeLibrary(goodLands: number, lands: number): Uint8Array {
  const library = new Uint8Array(DECK_SIZE)
  let index = 0
  for (let i = 0; i < goodLands; i++) library[index++] = GOOD
  for (let i = 0; i < lands - goodLands; i++) library[index++] = OTHER
  for (; index < DECK_SIZE; index++) library[index] = SPELL
  return library
}

/** In-place Fisher–Yates, matching the original `shuffleArray`. */
function shuffle(library: Uint8Array, rng: () => number): void {
  for (let i = library.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    const temp = library[i]
    library[i] = library[j]
    library[j] = temp
  }
}

function countTopSeven(library: Uint8Array): Hand {
  const hand: Hand = { good: 0, other: 0, spell: 0 }
  for (let i = 0; i < 7; i++) {
    const card = library[i]
    if (card === GOOD) hand.good += 1
    else if (card === OTHER) hand.other += 1
    else hand.spell += 1
  }
  return hand
}

/**
 * London mulligan: put `7 - handsize` cards on the bottom, shedding surplus
 * spells first (down to three), then non-producing lands, then producing
 * lands. This rationalises the original's per-handsize spell/land branches
 * into one rule; the "keep three spells if you can" intent is unchanged.
 */
function bottomForLondon(hand: Hand, handsize: number): void {
  let toBottom = 7 - handsize

  const surplusSpells = Math.min(toBottom, Math.max(0, hand.spell - 3))
  hand.spell -= surplusSpells
  toBottom -= surplusSpells

  const otherLands = Math.min(toBottom, hand.other)
  hand.other -= otherLands
  toBottom -= otherLands

  const goodLands = Math.min(toBottom, hand.good)
  hand.good -= goodLands
  toBottom -= goodLands

  hand.spell -= Math.min(toBottom, hand.spell)
}

/**
 * Decide whether to keep a freshly-seen hand, and if so apply the London
 * bottoming. The keep test runs on the hand that is actually kept (i.e.
 * after bottoming) — the original checked it against the pre-bottoming land
 * count, one of the defects fixed in this port.
 */
function resolveMulligan(hand: Hand, handsize: number): boolean {
  if (handsize === 7) {
    const lands = hand.good + hand.other
    return lands >= 3 && lands <= 5
  }

  bottomForLondon(hand, handsize)

  if (handsize === 6 || handsize === 5) {
    const lands = hand.good + hand.other
    return lands >= 2 && lands <= 4
  }

  // handsize === 4: the last hand you are dealt is always kept.
  return true
}

function playOneGame(
  library: Uint8Array,
  targetTurn: number,
  pips: number,
  rng: () => number,
): number {
  let good = 0
  let other = 0

  for (let handsize = 7; handsize >= 4; handsize--) {
    shuffle(library, rng)
    const hand = countTopSeven(library)
    if (resolveMulligan(hand, handsize)) {
      good = hand.good
      other = hand.other
      break
    }
  }

  // On the play: draw one card per turn from turn 2 up to the target turn.
  // (Spell counts don't matter past the mulligan, so only lands are tallied.)
  const drawUntil = Math.min(7 + targetTurn - 1, library.length)
  for (let i = 7; i < drawUntil; i++) {
    const card = library[i]
    if (card === GOOD) good += 1
    else if (card === OTHER) other += 1
  }

  if (good + other < targetTurn) return IRRELEVANT
  if (good < pips) return FAILURE
  return SUCCESS
}

/**
 * Sweep candidate colour-source counts from 0 upward and return the first
 * one whose success rate clears {@link CONFIDENCE_TARGET} at the lower bound
 * of its 95% Wilson interval.
 *
 * @param rng injected for deterministic tests; defaults to `Math.random`.
 * @param onProgress called after each candidate with a 0..1 fraction.
 */
export function runSimulation(
  params: OracleParams,
  rng: () => number = Math.random,
  onProgress?: (fraction: number) => void,
): OracleResult | OracleNotFound {
  const { lands, colority, simulations } = params
  const targetTurn = manaValue(colority)
  const pips = requiredPips(colority)
  const steps = lands + 1

  let sawAnyRelevantGame = false

  for (let goodLands = 0; goodLands <= lands; goodLands++) {
    const library = makeLibrary(goodLands, lands)
    let successes = 0
    let relevant = 0

    for (let game = 0; game < simulations; game++) {
      const outcome = playOneGame(library, targetTurn, pips, rng)
      if (outcome !== IRRELEVANT) relevant += 1
      if (outcome === SUCCESS) successes += 1
    }

    if (relevant > 0) sawAnyRelevantGame = true

    const [low, high] = wilsonInterval(successes, relevant)
    onProgress?.((goodLands + 1) / steps)

    if (low >= CONFIDENCE_TARGET) {
      return {
        found: true,
        goodLands,
        targetTurn,
        requiredPips: pips,
        colority,
        successRate: relevant === 0 ? 0 : successes / relevant,
        ciHalfWidth: (high - low) / 2,
        relevantGames: relevant,
        discardedGames: simulations - relevant,
        simulations,
      }
    }
  }

  return {
    found: false,
    targetTurn,
    requiredPips: pips,
    colority,
    simulations,
    maxGoodLandsTried: lands,
    everyGameDiscarded: !sawAnyRelevantGame,
  }
}

/** Messages the worker posts back to the `useManaOracle` hook. */
export type OracleResponse =
  | { type: 'progress'; fraction: number }
  | { type: 'done'; result: OracleResult | OracleNotFound }
  | { type: 'error'; message: string }
