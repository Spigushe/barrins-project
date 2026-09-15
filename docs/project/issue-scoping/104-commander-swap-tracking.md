# #104 — Commander swap tracking (opponent swaps commander between games)

[← Back to issue-scoping index](README.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` (roster / match model) + `apps/tamiyo_scroll` | Domain-model evolution — **needs Agent 0** (Constitution §6) |
| **Initial date** | 2026-09-08 | Scoped from the code, not yet decided |
| **Status** | 🔲 **Scoped — decision needed** | Do not implement before the Decisions section is answered |
| **Source** | GitHub issue [#104](https://github.com/Spigushe/barrins-project/issues/104), reported 2026-08-27 | Author: repo owner |
| **Roadmap** | Not explicitly on the [feature roadmap](../../content/front/tamiyo_scroll/roadmap.md) | Adjacent to its v2+ "add opponent name/alias" row |
| **Constitution** | §41 (Commander Validation — future), §42 (Partner Commander Support — future), §47.2 (reverse reports), §6 (Agent 0 owns domain-model evolution), §39/§48 (extensible, not premature) | |
| **Related** | [123-124-structured-match-log.md](123-124-structured-match-log.md) — strong coupling, see "Coupling" below |

---

## The request, verbatim

> **Current Situation:** My opponent played Brigid, Clachan's Heart and
> swapped game 2 and 3 on Jennifer Walters.
>
> **Expected Behaviour:** I am able to flag Jennifer Walters as the
> commander the opponent played on game 2 and 3.
>
> **Possible evolution:**
> 1. Adding "sub" decks linked to main decks in roster games
> 2. Being able to select a sub roster deck game 2 and 3

## Context — verified against the code (2026-09-08, `staging`)

### There is no "commander" concept in the tracker's match / roster model

- [`TSMetaDeck`](../../../apps/barrins_api/app/models/tamiyo_scroll.py)
  (the opponent "roster" entry) is `name` + `tier` + `category` +
  metagame stats. **No commander field.** The only place the string
  "commander" appears in the Tamiyo Scroll backend is the *decklist
  view* (`is_commander`, the Commander *section* of a decklist) — a
  different concept entirely.
- [`TSMatch`](../../../apps/barrins_api/app/models/tamiyo_scroll.py) has
  a single `opponent_deck_id` FK → one `TSMetaDeck`. There is **no
  per-game opponent** and no per-game anything except the `game1/2/3`
  result columns.
- [`_validate_match_refs` in `matches.py`](../../../apps/barrins_api/app/api/tamiyo_scroll/matches.py)
  validates that the one `opponent_deck_id` belongs to the caller.
- Matchup stats
  ([`stats.py` `compute_period_stats`](../../../apps/barrins_api/app/services/tamiyo_scroll/stats.py))
  key every matchup row on `opponent_deck_id`. A BO3 is one match
  against one opponent deck.

So "Jennifer Walters" today can only be represented as its own separate
`TSMetaDeck` roster row, and a single match can only point at one of
them.

### The constitution already has opinions here — all marked *future*

- **§41 Commander Validation:** *"frontend must not contain commander
  database; validation logic belongs to backend; external data sources
  must be abstracted."* `mj_cards` (MTGJSON, S8) now exists and could
  back such validation, but §41 is explicitly a future feature.
- **§42 Partner Commander Support:** *"The data model must not assume
  `Deck -> Commander = One entity`. Prefer an extensible relationship …
  Do not implement this feature now unless required. Ensure current
  architecture does not block it."*
- **§39 / §48:** simple today, extensible tomorrow; no unused tables or
  abstractions.

Any commander concept added for #104 must not hard-code single-commander
(§42) and should keep validation server-side (§41), even if validation
itself is deferred.

## Alternatives

### A. Literal ask only — per-game opponent override on the match

Add nullable `opponent_deck_id_g2` / `opponent_deck_id_g3` FKs to
`ts_matches` (or, if #123/#124's `ts_match_games` table lands, a nullable
`opponent_meta_deck_id` column there). Blank = "same as the match-level
opponent". "Jennifer Walters" is a normal `TSMetaDeck` roster row the
user creates once.

- **Trade-offs:** smallest change, reuses the roster + the existing
  `OpponentDeckField` combobox, keeps matchup stats keyed on a real
  `TSMetaDeck`. But it makes the user maintain "Brigid" and "Jennifer
  Walters" as unrelated roster rows with no link between them, and it
  says nothing about *commanders* specifically — it's "different
  opponent deck per game", which is close enough to the literal ask.

### B. The user's "sub decks" — self-referential roster hierarchy

`TSMetaDeck` gains a nullable `parent_meta_deck_id` → itself. "Jennifer
Walters" becomes a *variant of* "Brigid". A match (or per-game slot)
can point at a parent or any of its variants.

- **Trade-offs:** matches the user's own stated evolution and models the
  real thing ("one deck, swappable configurations"). But it forces a
  **stats-semantics decision** (see D3): does a game vs. the "Jennifer
  Walters" variant count toward the "Brigid" matchup row, its own row,
  or both? Every matchup aggregation, the archetype breakdown, the
  reverse-report groundwork (§47.2) and the PDF reports have to pick a
  rule. This is a genuine domain-model change — Agent 0 territory (§6).

### C. Commander as a first-class field on `TSMetaDeck` (+ per-game commander on the match)

`TSMetaDeck` gains `commander_name` (nullable, single now, designed to
extend to a partner slot per §42). "Swap" = *same deck, different
commander per game* → a nullable `opponent_commander_g2/g3` (free text or
FK-to-`mj_cards`) on the match / game row.

- **Trade-offs:** models exactly what the issue title says
  ("commander"), and lines up with §41/§42's eventual direction. But
  §41/§42 are deliberately future, §48 warns against building the
  abstraction before it's needed, and doing this properly pulls in
  commander-name validation against `mj_cards`, partner handling, and a
  decision about whether the roster is keyed by *deck* or by
  *commander*. Largest scope; should not be back-doored through a
  small feature request.

### D. Free-text per-game note only

Add `opponent_commander_g2` / `_g3` as plain strings, shown in the
journal, never queried.

- **Trade-offs:** trivial and unblocking for the user's immediate need
  ("I am able to flag …"). But it's a dead-end string that a future §41
  commander concept would have to migrate away from, and it can't feed
  any stat or reverse report. Acceptable only as an explicit
  stopgap.

## Recommendation

1. **Sequence after [#123/#124](123-124-structured-match-log.md)'s model
   decision.** If that item's recommended `ts_match_games` child table
   is adopted, #104 is *"add a nullable `opponent_meta_deck_id` to
   `ts_match_games`, defaulting to `TSMatch.opponent_deck_id`"* — a
   small, clean addition with a natural home. Building #104 first would
   put per-game opponent columns straight onto `ts_matches` and then
   have to move them.
2. **Ship Alternative A** (per-game opponent = another roster row) as
   the first step — it satisfies the literal ask with the least model
   risk, and keeps the match-level `opponent_deck_id` as the **canonical
   matchup key** (a BO3 is still one match vs. the opponent's deck; the
   per-game opponent is annotation).
3. **Defer B ("sub decks") and C (commander field) to their own
   items**, each opened with an **Agent 0 design note** (§6, §16.3) —
   they are §41/§42 domain-model evolution, not a bug-sized change.

## Decisions needed (flagged, not guessed)

1. **Scope now.** Alternative A (per-game opponent override) /
   B (sub-deck hierarchy) / C (commander field) / D (free-text stopgap).
   Recommendation: A, sequenced after #123/#124.
2. **Per-game opponent representation.** Nullable FK to another
   `TSMetaDeck` (recommended — queryable, reuses roster + combobox) vs.
   free-text commander string (cheap, dead-end).
3. **Stats attribution (only if B, or if A splits a BO3).** When a
   BO3's games point at different opponent decks, does the match count
   toward one matchup row (the match-level opponent), one row per
   distinct per-game opponent, or is per-game opponent excluded from
   matchup aggregation entirely? Recommendation: match-level opponent
   stays the sole matchup key; per-game opponent is annotation only,
   for now.
4. **Commander field on `TSMetaDeck`.** Add `commander_name` now
   (nullable, single, §42-extensible) or defer entirely to a future
   §41/§42 item? Recommendation: defer — don't introduce the
   abstraction through this issue (§48).
5. **Own side too?** The issue is about the *opponent* swapping. Record
   the user's *own* per-game commander as well? Not requested —
   recommendation: out of scope (its future home is §42 partner
   selection on the personal deck).
6. **Coupling to #123/#124.** Confirm #104 waits on that item's
   `ts_match_games` vs. flat-columns decision before implementation, so
   the per-game opponent lands in the right place once.

## Consequences

- **Domain model:** touches the opponent-roster / match relationship —
  Constitution §6 puts "domain model evolution" and "migration
  strategy" under Agent 0. This item cannot proceed on a
  Backend-Lead-only sign-off.
- **Schema:** Alternative A = 2 nullable FK columns on `ts_matches`
  (or 1 on `ts_match_games`); B = 1 self-FK on `ts_meta_decks` + the
  per-game slot; C = a commander column + partner design. All additive,
  no destructive migration, but B/C need a data-semantics migration
  plan for stats.
- **API contract:** `MatchWrite` / `ResponseMatch` (and per-game
  payloads if #123/#124 nests them) grow an optional per-game opponent
  field; `_validate_match_refs` extends to validate it; matchup
  responses may or may not change depending on D3. Documented per §21.1.
- **Frontend:** `MatchFormFields` gains an optional per-game opponent
  picker (reuse `OpponentDeckField`); `MatchJournalSection` shows the
  swap; under B, the roster UI (`MetaDecksSections`) gains a
  parent/variant affordance.
- **Reverse reports (§47.2):** per-game opponent data is a prerequisite
  the future reverse-report feature would want — worth capturing the
  shape with that in mind even though that feature isn't scheduled.
- **Roadmap / docs:** add a roadmap row linking here; if B or C is
  chosen, an ADR and/or `v3.0.0-bump/`-style page, plus updates to how
  §41/§42 describe the now-partially-built commander concept.
- **Tests:** per-game opponent round-trips through `POST`/`PUT /matches`;
  `_validate_match_refs` rejects a foreign per-game opponent; matchup
  stats behave per D3; journal renders the swap.
