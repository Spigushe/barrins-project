<!-- cSpell:ignore Moxfield MTGJSON Competitif Barrin scryfall -->
<!-- cSpell:ignore Pydantic upserts mypy -->
# Implementation Plan — Competitive MTG Tracking (Tamiyo Scroll BFF)

> **Target**: barrins-project/barrins_api
> **Initial date**: 2026-07-15
> **Status**: ✅ Implemented — 2026-07-15 (backend only, Tamiyo Scroll
> frontend to be built separately)
> **Source**: design handoff `Suivi Competitif MTG.dc.html` + `README.md`
> (provided by the client, high fidelity — see §13 of the project
> constitution for the product summary)
> **Dependency**: reuses the existing JWT authentication
> (`docs/auth_roles/`). Does **not** technically depend on
> `docs/signup_email_verification/` — accounts can be provisioned via
> `POST /auth/register` (admin) pending self-registration.

---

## Objective

By the end of this implementation, the API must expose, under the BFF
namespace `/api/v1/tamiyo-scroll/` (constitution §12), everything needed to:

1. Manage a user's personal decks and their decklist versions (raw pasted text
   or Moxfield import placeholder — **no real scraping**, see Non-goals).
2. Manage a roster of expected opponent decks ("MUR"), with tier, archetype,
   and expected metagame data (Top 8, presence, server-computed conversion).
3. Log BO3 matches (games, OTP/OTD, match notes) linked to a personal deck
   and a roster deck.
4. Log individual feedback on tested cards (1-5 rating, free-form notes).
5. Compute server-side — never on the frontend (constitution §4.1/§4.2) —
   the Top8/Presence conversion, per-matchup win rate summaries
   (global/OTP/OTD, W/L ratios), the average win rate per archetype, and
   decklist row coloring derived from tested-card feedback.
6. Allow a user to enable read-only sharing of their data
   (`data_shared`), and let another authenticated user view — but never
   modify — that shared data.
7. Guarantee, **at the server level** (not just via the UI), that no write
   request can target another user's data, even in the event of a frontend bug.

### Non-goals (explicitly out of scope for v1)

- Real Moxfield scraping:
  `POST .../personal-decks/{id}/versions/import-moxfield` creates a
  version whose content is a placeholder mentioning the provided URL
  (faithful to the prototype's simulated behavior). Actual automation is
  a **future** BFF extension, explicitly mentioned as "in progress" in
  the design handoff — to be handled in a separate plan.
- Auto-population of the expected metagame from tournament data already
  present in `dl_decks`/`dl_tournaments`: the roster (`ts_meta_decks`) is
  entered manually by the user in v1, even though a future link with the
  `decklist_integration` pipeline is conceivable (see §12 of this
  document, "Future compatibility").
- Resolving tested card names to `cards.uuid` (autocomplete, MTGJSON
  validation) — `card_name` remains a free-form string in v1, as in the
  design.

---

## Domain model

> **Naming convention**: `ts_` prefix (Tamiyo Scroll), mirroring the `dl_`
> prefix used by `docs/decklist_integration/` for the scraped tournament
> domain. This new domain is **deliberately distinct** from `dl_*`: data
> owned by the user, editable, versioned — not public scraped data
> indexed by `anchor_uri`.

| Table | Role | Key fields |
| ----- | ---- | ----------- |
| `ts_user_settings` | Per-user preferences (1 row per user, created on demand) | `user_id` (PK/FK), `data_shared: bool`, `active_personal_deck_id: FK nullable` |
| `ts_personal_decks` | User's personal decks (`myDecks[]`) | `id`, `owner_id FK`, `name`, `archived_at: datetime \| None`, `created_at` |
| `ts_personal_decklist_versions` | Versioned decklist history (`decklistVersions[]`) | `id`, `personal_deck_id FK`, `version: int`, `content: text`, `source: enum(manual, moxfield_import)`, `created_at` |
| `ts_meta_decks` | Opponent deck roster + expected metagame — **a single entity** for both UI sections (`decks[]`) | `id`, `owner_id FK`, `name`, `tier: numeric(2,1)`, `category: enum(aggro, midrange, control, combo)`, `decklist_notes: text`, `top8: int`, `presence: int`, `expected: enum(as_expected, more_expected, less_expected)`, `tests_status: text`, `archived_at: datetime \| None` |
| `ts_matches` | BO3 match log (`matches[]`) | `id`, `owner_id FK`, `date`, `personal_deck_id FK -> ts_personal_decks`, `opponent_deck_id FK -> ts_meta_decks`, `on_play: bool` (OTP=true/OTD=false), `game1/2/3: enum(win, loss, draw) nullable`, `opening_hand/turning_point/final_turn: text` |
| `ts_card_tests` | Tested card feedback (`cardTests[]`) | `id`, `owner_id FK`, `personal_deck_id FK -> ts_personal_decks nullable` (see 2026-07-16 fix), `tester: string` (free text — no account FK, see Decision E), `card_name: string`, `opponent_deck_id FK -> ts_meta_decks nullable`, `rating: int 1-5`, `notes: text` |

All `ts_*` tables (except `ts_user_settings`) carry `owner_id FK ->
users.id ON DELETE CASCADE` — deleting **an account** purges its
tracker data, consistent with `dl_decks` which already cascades from
`dl_tournaments`. However, deleting **a deck** (personal or roster) from
the UI is **never** an SQL `DELETE` — see Option G below — so
`ts_matches.personal_deck_id` and
`ts_matches.opponent_deck_id`/`ts_card_tests.opponent_deck_id` remain
stable FKs indefinitely, never becoming `NULL`.

---

## Options analysis

### A. Table naming prefix

| Option | Advantages | Disadvantages |
| ------ | --------- | ------------- |
| **A (chosen)** `ts_` | Consistent with the `dl_` prefix already in place; avoids any ambiguity with the scraped tournament domain | One more prefix to know |
| B No prefix (`personal_decks`, `meta_decks`, …) | More readable in isolation | Risk of confusion with a future non-Tamiyo-Scroll "personal" domain; the project already has a per-functional-domain prefix convention |

**Choice: A** — consistency with the existing convention.

### B. Enforcing the read-only (sharing) model

| Option | Mechanism | Advantages | Disadvantages |
| ------ | --------- | --------- | ------------- |
| **A (chosen)** | `owner_id` query parameter on **GET routes only**; write routes (POST/PUT/DELETE) never accept this parameter and always operate on `current_user` | Secure by construction: even if the frontend mistakenly shows editing controls in view mode, the backend technically cannot write to a third party's data | Every GET route must resolve and validate `owner_id` (shared FastAPI dependency to factor this out) |
| B | `can_edit` flag sent by the client | The client decides — **explicitly rejected by constitution §13.5** ("Frontend must not decide permissions") | — |
| C | Separate "viewer" account with its own tokens | Over-engineering for this need | Unnecessary complexity |

**Choice: A**, via a shared FastAPI dependency
`resolve_owner(owner_id: UUID | None, current_user: CurrentUser,
session) -> User` which:

- returns `current_user` if `owner_id` is absent or equal to
  `current_user.id`;
- otherwise verifies that the target user exists and has
  `ts_user_settings.data_shared = True`, else `403`;
- is used **only** in the signature of GET routes.

### C. Win rate calculation basis

| Option | Mechanism | Advantages | Disadvantages |
| ------ | --------- | --------- | ------------- |
| **A (chosen)** | Win rate at the **game** level (aggregating `game1/game2/game3` across all matches of the matchup), draws excluded from the denominator | Matches literally the README's description (§"Matchup summary": "aggregation of games (g1/g2/g3)") | A BO3 match won 2-1 contributes 2 wins + 1 loss to the calculation, not "1 win" — behavior to confirm visually with the client once the screen is rebuilt |
| B | Win rate at the **match** level (overall BO3 result) | Simpler, more intuitive for a player | Contradicts the README text, which explicitly refers to games |

**Choice: A**, with a **validation note** — behavior derived directly
from the design text, but to be confirmed visually (Agent 4 / client
feedback) once the first render is available on the frontend, before
treating this calculation as final.

### D. Persisting preferences (active deck, sharing)

| Option | Mechanism | Advantages | Disadvantages |
| ------ | --------- | --------- | ------------- |
| A | Columns added to `users` | No new table | Pollutes the shared identity model (constitution §13.1) with state specific to a single application — blocking if a future Barrin app has its own concept of "active deck" |
| **B (chosen)** | Dedicated `ts_user_settings` table for the BFF domain | Respects domain separation (§11.5); `users` remains a pure identity model, reusable as-is by future applications | One more join |

**Choice: B**.

### E. `ts_card_tests`'s `tester` field

| Option | Mechanism | Advantages | Disadvantages |
| ------ | --------- | --------- | ------------- |
| **A (chosen)** | Free-form string, no FK to `users` | Faithful to the design (free-text nickname — allows crediting a tester without a Barrin account, e.g. an occasional teammate) | No uniqueness/spelling guarantee |
| B | FK to `users.id` | Referential consistency | Forces every tester to have an account — contradicts the usage observed in the design (free nickname) |

**Choice: A**, consistent with the prototype's behavior.

### F. Decklist row coloring

Derived calculation (README §"Derived calculations"): for each row of
the current decklist, find the longest card name among
`ts_card_tests.card_name` (from the same `owner`) that appears in the
row's text, then aggregate the ratings (`rating`) of the feedback tied
to that card name: **validated** if ≥4 majority, **rejected** if ≤2
majority, otherwise **in test** if at least one piece of feedback
exists, otherwise **neutral**.

**Decision**: computed server-side
(`GET .../personal-decks/{id}/decklist-view`), never reimplemented on
the frontend — direct application of the "no duplicated business
logic" rule (constitution §4.2). The frontend receives
`{line: str, status: "validated"|"rejected"|"in_test"|"neutral"}[]`.

### G. Deleting a deck (personal or roster)

| Option | Mechanism | Information loss for data science |
| ------ | --------- | --------------------------------- |
| A | Real SQL `DELETE`, `ts_matches`/`ts_card_tests` FKs made nullable + `ON DELETE SET NULL` | The opponent deck's name/tier/category at the time of the match is lost, unless snapshot columns are added to duplicate the information |
| **B (chosen)** | Soft delete: `archived_at` column on `ts_personal_decks` and `ts_meta_decks`. "Deleting" in the UI becomes archiving (`UPDATE ... SET archived_at = now()`), never an SQL `DELETE` | No loss: the future data science layer queries `ts_matches`/`ts_card_tests` joined to `ts_meta_decks`/`ts_personal_decks` directly, never encountering a missing row or a broken FK |

**Choice: B** — explicitly chosen to preserve the deck's full set of
attributes (not just its name) for the benefit of the future data
science layer.

Consequences:

- The `ts_matches.personal_deck_id`, `ts_matches.opponent_deck_id`, and
  `ts_card_tests.opponent_deck_id` FKs remain `NOT NULL` (except
  `ts_card_tests`'s `opponent_deck_id`, nullable for a different reason
  — optional matchup, see domain model) — **never** `SET NULL` by a
  deck deletion.
- `GET /personal-decks` and `GET /meta-decks` filter on `archived_at IS
  NULL` by default (active list for the UI). An
  `include_archived: bool = False` parameter allows including them if
  needed.
- The derived-calculation endpoints (`/archetype-summary`,
  `/matchup-summary`, `/decklist-view`) **never filter out** archived
  decks in their joins — an archived deck keeps its win rate/feedback
  history intact, only its visibility in management lists changes.
- `DELETE /api/v1/tamiyo-scroll/personal-decks/{id}` is added to the
  route map (absent from this plan's initial v1) to symmetrically
  cover both tables — implemented as archiving, not SQL deletion.
- No un-archiving in v1 (YAGNI, constitution §39/§48) — recoverable
  manually in the database if needed; a dedicated route can be added
  later without a schema change.

---

## Target architecture

Same router/service separation as `tolaria_news`
(`docs/tolaria_news/00_plan_general.md`) — no query written directly
in route files:

```text
app/
  api/v1/
    tamiyo_scroll.py               ← aggregator, mounted in main.py
                                     alongside v1_router/tolaria_router
    tamiyo_scroll_routers/
      settings.py                  ← GET/PATCH /me/settings, GET /shared-users
      personal_decks.py            ← /personal-decks,
                                     /personal-decks/{id}/versions*,
                                     /decklist-view
      meta_decks.py                ← /meta-decks (CRUD)
      matches.py                   ← /matches (CRUD)
      card_tests.py                ← /card-tests (CRUD)
      stats.py                     ← /archetype-summary, /matchup-summary
  services/tamiyo_scroll/
    ownership.py                   ← resolve_owner() — shared FastAPI
                                     dependency
    stats.py                       ← win rate/conversion/archetype
                                     calculations
    decklist_coloring.py           ← coloring algorithm (100% tested function)
  models/
    ts_user_settings.py, ts_personal_deck.py, ts_personal_decklist_version.py,
    ts_meta_deck.py, ts_match.py, ts_card_test.py
  schemas/
    tamiyo_scroll.py               ← request schemas,
    responses_tamiyo_scroll.py     ← response schemas
```

---

## Route map

| Method | Route | Owner param | Required role |
| ------- | ----- | :---------: | ----------- |
| `GET` | `/api/v1/tamiyo-scroll/shared-users` | — | user |
| `GET`/`PATCH` | `/api/v1/tamiyo-scroll/me/settings` | — (always self) | user |
| `GET` | `/api/v1/tamiyo-scroll/personal-decks` | ✅ (+ `include_archived?`) | user |
| `POST` | `/api/v1/tamiyo-scroll/personal-decks` | — | user |
| `DELETE` | `/api/v1/tamiyo-scroll/personal-decks/{id}` | — | user *(archiving, no SQL DELETE — see Option G)* |
| `GET` | `/api/v1/tamiyo-scroll/personal-decks/{id}/versions` | ✅ | user |
| `POST` | `/api/v1/tamiyo-scroll/personal-decks/{id}/versions` | — | user |
| `POST` | `/api/v1/tamiyo-scroll/personal-decks/{id}/versions/import-moxfield` | — | user |
| `DELETE` | `/api/v1/tamiyo-scroll/personal-decks/{id}/versions/{version_id}` | — | user *(real SQL DELETE — it's not the deck being targeted)* |
| `GET` | `/api/v1/tamiyo-scroll/personal-decks/{id}/decklist-view` | ✅ | user |
| `GET` | `/api/v1/tamiyo-scroll/meta-decks` | ✅ (+ `include_archived?`) | user |
| `POST`/`PUT` | `/api/v1/tamiyo-scroll/meta-decks[/{id}]` | — | user |
| `DELETE` | `/api/v1/tamiyo-scroll/meta-decks/{id}` | — | user *(archiving, no SQL DELETE — see Option G)* |
| `GET` | `/api/v1/tamiyo-scroll/matches` | ✅ | user |
| `POST`/`PUT`/`DELETE` | `/api/v1/tamiyo-scroll/matches[/{id}]` | — | user |
| `GET` | `/api/v1/tamiyo-scroll/card-tests` | ✅ (+ `personal_deck_id?`) | user |
| `POST`/`PUT`/`DELETE` | `/api/v1/tamiyo-scroll/card-tests[/{id}]` | — | user |
| `GET` | `/api/v1/tamiyo-scroll/archetype-summary` | ✅ | user |
| `GET` | `/api/v1/tamiyo-scroll/matchup-summary` | ✅ (+ `personal_deck_id?`) | user |

All routes require `CurrentUser` (valid JWT) — no anonymous access,
unlike the Tolaria News BFF which is publicly readable. Write-side
security: every POST/PUT/DELETE route explicitly checks
`resource.owner_id == current_user.id` before modifying (404, not 403,
if the resource doesn't belong to the user — avoids revealing the
existence of another person's ID).

---

## Overview of changes

| Dimension | Current state | After implementation | Work required |
| --------- | ----------- | -------------------- | -------------- |
| ORM models | `dl_*` (tournaments), `User` | +6 `ts_*` tables | `app/models/ts_*.py` |
| Migration | 10 existing migrations (+1 if signup handled first) | +1 migration | `alembic/versions/` |
| Schemas | `auth.py`, `responses_*` | + `app/schemas/tamiyo_scroll.py`, `responses_tamiyo_scroll.py` | New files |
| Services | `app/services/{decklist,mtgjson,ml,scryfall,tolaria}/` | + `app/services/tamiyo_scroll/` | New service |
| Routes | `app/api/v1/routers/*`, `tolaria_routers/*` | + `app/api/v1/tamiyo_scroll_routers/*`, mounted in `main.py` | New files + 2 lines in `main.py` |
| Tests | `tests/tolaria/` (previous BFF) | + `tests/tamiyo_scroll/` (same structure) | New files |

---

## Phase breakdown

| Phase | Title | Main files | Prerequisites |
| ----- | ----- | ------------------- | --------- |
| 1 | ORM models | `app/models/ts_*.py` | — |
| 2 | Alembic migration | `alembic/versions/` | Phase 1 |
| 3 | Pydantic schemas | `app/schemas/tamiyo_scroll.py`, `responses_tamiyo_scroll.py` | Phase 1 |
| 4 | `ownership` service (sharing dependency) | `app/services/tamiyo_scroll/ownership.py` | Phase 1 |
| 5 | `stats` service (win rate, conversion, archetypes) | `app/services/tamiyo_scroll/stats.py` | Phases 1, 3 |
| 6 | `decklist_coloring` service | `app/services/tamiyo_scroll/decklist_coloring.py` | Phases 1, 3 |
| 7 | Settings + personal-decks routes | `tamiyo_scroll_routers/settings.py`, `personal_decks.py` | Phases 2–6 |
| 8 | meta-decks + matches + card-tests routes | `tamiyo_scroll_routers/meta_decks.py`, `matches.py`, `card_tests.py` | Phases 2–6 |
| 9 | Stats routes + `main.py` mounting | `tamiyo_scroll_routers/stats.py`, `tamiyo_scroll.py`, `main.py` | Phases 7, 8 |
| 10 | Tests | `tests/tamiyo_scroll/` | All |

---

## Points requiring attention

- **Archiving vs. cascade (resolved — see Option G)**: archiving
  (`archived_at`) replaces SQL `DELETE` for
  `ts_personal_decks`/`ts_meta_decks`, so `ts_personal_decklist_versions`
  (attached to `ts_personal_decks`) are **never** cascaded by a user
  action — only account deletion (`users` → real cascade) purges them.
- **Version uniqueness**: `UNIQUE(personal_deck_id, version)` on
  `ts_personal_decklist_versions`, `version` computed server-side
  (`MAX(version) + 1`) in the same transaction as the insert to avoid
  a race between two concurrent requests (`SELECT ... FOR UPDATE` on
  the parent deck, a pattern already used for upserts in
  `app/services/decklist/importer.py`).
- **`ts_user_settings` created on demand**: no hook on account
  creation (which stays in the `auth` domain, out of BFF scope) — the
  first read/write creates the row with default values
  (`data_shared=False`, `active_personal_deck_id=None`).
- **404 vs. 403 on cross-owner writes**: always 404, so as not to
  confirm the existence of an ID belonging to a third party
  (consistent with the "don't disclose an account's existence"
  principle in constitution §23.2, extended here to resources).

---

## Open point — future compatibility (non-blocking, not to be implemented now)

The handoff README explicitly mentions a future BFF extension
automating metagame import and Moxfield scraping. The current
`ts_meta_decks` model has no column linking it to
`dl_decks`/`dl_tournaments` — this is deliberate (YAGNI, constitution
§39/§48) but flagged here so Agent 0 can confirm that nothing in the
chosen schema will prevent a future reconciliation (e.g. later adding
a nullable `linked_dl_deck_id` column).

---

## Implementation notes (2026-07-15)

- Files delivered: 6 ORM models (`app/models/ts_*.py`), migration
  `7ba66089f77e`, request/response schemas (`app/schemas/tamiyo_scroll.py`,
  `responses_tamiyo_scroll.py`), services (`app/services/tamiyo_scroll/`
  — `ownership.resolve_owner`, `stats.compute_archetype_summary`/
  `compute_matchup_summary`, `decklist_coloring.color_decklist`, all
  pure functions independently tested), routes
  (`app/api/v1/tamiyo_scroll_routers/*`, aggregated in
  `app/api/v1/tamiyo_scroll.py`, mounted in `main.py`).
- 16 endpoints exposed, matching the plan's route map
  (verified via `app.openapi()`, not just by reading the code).
- `ResolvedOwner = Annotated[User, Depends(resolve_owner)]`: every GET route
  using it automatically exposes `owner_id` as a query param (the
  `resolve_owner` parameter gets promoted by FastAPI) — no write
  route declares this parameter, so `owner_id` in the query string on
  a POST/PUT/DELETE route is silently ignored (explicitly tested
  in `tests/tamiyo_scroll/test_ownership.py`).
- Minor deviation from the initial plan: decklist coloring and
  win rate/archetype summaries are implemented as pure functions
  operating on lists of already-loaded ORM objects (no nested SQL
  queries) — simpler to test at 100%, consistent with the
  `services/tolaria/helpers.py` pattern.
- Tests: 127 tests (30 pure functions + 97 HTTP), all passing. `ruff`
  and `mypy` clean across all of `app/`. Full project suite: 991
  passing tests, the same 9 pre-existing, unrelated failures
  (`tests/tolaria/` fixtures) as before this implementation.
- Same validation environment limitation as documented in
  `docs/signup_email_verification/00_plan_general.md` (Python 3.14 not
  installable in this sandbox, validation done under 3.13 with
  strictly local `from __future__ import annotations` fixes,
  never committed) — to be re-run with `--cov` on real CI/3.14 for a
  reliable coverage figure.
- **Option C confirmed by the client (2026-07-15)**: win rate is indeed
  computed at the game level (`game1`/`game2`/`game3`), not at the match level.
  Implemented behavior is final, no change required.

## Post-delivery fixes (2026-07-16)

Two bugs reported by the client after the frontend went live
(see `docs/frontend_bootstrap/`, feedback phase), both fixed
on the backend since they touch business logic (constitution §4.1/§4.2):

- **`ts_card_tests` leaking across personal decks**: the table had
  no column linking it to `ts_personal_decks` — a test result created
  while testing one deck stayed visible (and colored the decklist) on
  any other personal deck belonging to the same user. Added
  `personal_deck_id` (nullable FK to `ts_personal_decks`, migration
  `a3f8c1d9e2b7`). Nullable in the database to avoid losing existing
  rows during the migration; becomes mandatory in
  `CardTestWrite` for any new write. `GET /card-tests` and
  `GET /personal-decks/{id}/decklist-view` now filter on the deck
  being viewed — rows created before this fix (`personal_deck_id`
  NULL) match no filter and stay invisible (no arbitrary
  server-side re-association).
- **`archetype-summary` wasn't excluding archived decks**:
  `list_meta_decks` filters `archived_at IS NULL` by default, but
  `get_archetype_summary` didn't — a deleted roster deck kept
  reappearing indefinitely in the "Archetype breakdown" cards,
  even after a full reload (this wasn't a frontend cache issue).
  `matchup-summary` deliberately stays unfiltered: an already-logged
  match must keep showing the opponent's name even if their roster
  deck has since been archived.

Regression tests added in `tests/tamiyo_scroll/test_card_tests.py`
(filtering by `personal_deck_id`, 404 on a foreign personal deck),
`tests/tamiyo_scroll/test_personal_decks.py` (`decklist-view` ignores
tests from another deck), and `tests/tamiyo_scroll/test_stats_routes.py`
(archived deck excluded from `archetype-summary`).
