# Tolaria West — hidden mana-source calculator (Tolaria News easter egg)

Internal project note, not part of the public docs site (same as the rest
of `docs/project/`).

|            |                                                            |
| ---------- | ---------------------------------------------------------- |
| **Target** | `apps/tolaria_news` (frontend only)                        |
| **Date**   | 2026-09-06                                                 |
| **Status** | 🟢 Implemented on `proj/tolaria-west-easter-egg`           |
| **Owner**  | Agent 2 (frontend), Agent 0 sign-off on the §4.1 exception |

---

## Context

The author wrote a standalone HTML toy years ago — a Monte Carlo
simulator that answers _"how many of my lands must produce a given colour
for me to cast a spell on curve with ~90% reliability?"_ for a 99-card
singleton (Duel Commander) deck. It was Bootstrap + vanilla JS. The ask:
fold it into Tolaria News as a hidden easter egg.

## Decision

### Runs client-side, as a documented §4.1 exception

The simulation lives entirely in the browser (a Web Worker), not in
`barrins_api`. Constitution §4.1 puts business logic in the backend, but:

- it is a **generic MTG probability toy** — it reads no ecosystem data,
  persists nothing, and duplicates no rule that exists anywhere else in
  the codebase (§4.2);
- building a domain service + BFF route + DTO + schema + backend tests
  for a hidden toy is exactly the premature surface area §48 warns
  against.

So it is an intentional, in-code-documented exception (see the header
comment in `src/lib/manaOracle.ts`), not an oversight. No `barrins_api`,
BFF, or Ansible change — `tolaria_news.yml` is untouched (§26.1).

### Three ways in, no nav link ever

| Trigger                                 | Where                                                                                                       |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Konami code (`↑ ↑ ↓ ↓ ← → ← → B A`)     | anywhere in the app                                                                                         |
| Seven clicks on the **"decoded."** word | landing-page headline (`metagame decoded.`) — no visual tell, it stays styled like the rest of the flourish |
| Typing **`manabase`**                   | anywhere outside a form field                                                                               |

All keyboard triggers are suppressed while an `input` / `textarea` /
`select` / contenteditable is focused, so they never fight the
calculator's own form. The route is `/west` (after the MTG land _Tolaria
West_, which transmutes to fetch any land). It is **not** behind a
`VITE_FEATURE_*` flag — an easter egg that is flag-off everywhere would
never be found; it ships live but unlisted.

### The simulation model (unchanged from the original)

- Deck = `goodLands` colour sources + other lands + `99 − lands` spells.
- Colority `1CC`: mana value (Σ digits + count of `C`) is the target
  turn; count of `C` is the coloured pips needed in play.
- London mulligan 7→4, on the play (draw `turn − 1` extra cards).
- A game short of `turn` total lands is _discarded_ (mana screw), not
  counted in the denominator.
- Sweep source counts from 0 up; report the first whose success rate
  clears 90% at the **lower bound** of its 95% Wilson score interval.

### Four defects fixed in the port

1. The sim-count ceiling now agrees with the input (**100 000**; default
   still 5 000) instead of the old silent "max 10 000" rejection.
2. A zero-simulation run is rejected up front (Zod), so the old `0 / 0`
   NaN in the result line cannot happen.
3. The hand is reset between mulligan iterations (the original leaked
   stale card counts from earlier iterations).
4. The mulligan keep/discard decision is evaluated on the hand actually
   kept, and the London bottoming rule is one documented heuristic
   instead of per-handsize branches.

## Consequences

- **New files**: `src/lib/manaOracle.ts` (pure core, RNG injected for
  tests), `src/lib/manaOracle.worker.ts`, `src/hooks/useManaOracle.ts`,
  `src/hooks/useSecretUnlock.ts` (`useSecretUnlock` + `useTapUnlock`),
  `src/pages/TolariaWestPage.tsx`, plus tests for each.
- **Touched**: `src/App.tsx` (adds the unlisted `/west` route),
  `src/components/layout/AppShell.tsx` (mounts `useSecretUnlock`),
  `src/pages/LandingPage.tsx` (the "decoded." word gains the seven-click
  handler — no visual change).
- **No new dependencies** (§22.3) — the Worker is a browser API; the
  seeded PRNG used in tests is ~4 inline lines.
- **No i18n** — Tolaria News ships English string literals throughout and
  has no i18n library; this page matches that.
- Output numbers differ slightly from the original HTML toy because of
  defect fixes 3 and 4; the model is otherwise identical.
