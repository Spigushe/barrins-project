# v2.0.0 — Tolaria News, Tamiyo Scroll Expansion & Ecosystem Hardening

**Project orientation for the upcoming weeks/months.** This document is
the foundation for every work item below — read it before picking up any
individual item.

Internal project tracking, not part of the public docs site
(`docs.barrins-codex.org`): like `docs/project/v1.0.0-bump/`,
this directory lives outside `docs/content/` (mkdocs' `docs_dir`), so it
isn't built or published, only version-controlled and reviewed via PR.

**Status of this document**: planning draft, **updated 2026-07-25** with
the user's decisions on §1.1, §1.2, §1.3, §1.5, §1.6 and §1.7;
**updated 2026-07-26** with the decision on §1.4, an addition to
§1.1/§1.3 (the `barrins-project` org's eventual, non-urgent deletion —
the user's own deliberate action, not a deadline), the `bs_*` naming
decision for T2's schema, a new item §1.9 (Tolaria News BFF access
restriction), a flagged enhancement idea on S3 (Moxfield staleness
check), a **discovered gap** (F8: MTGJSON is documented as implemented
in `auth_roles.md` but doesn't exist in code at all) that produced **S8**
(the real MTGJSON pipeline, now blocking S4 and S2's deck-validation
gate), and **I8** (S5's PDF-library choice, confirmed to require an ADR);
and **updated again 2026-07-27** with: **I8 resolved** (WeasyPrint,
researched against the user's stability/security/no-data-loss criteria),
**§1.9/I7 resolved** (Option 4 — public routes stay open, restricted by
rate-limiting rather than caller identity, which itself surfaces a new
gap tracked as `consitution-amendment.md` Proposal 6), a narrowing
constraint on S3's Moxfield enhancement (opportunistic use only, never a
dedicated call), and a **new item, S9** (tournament/training session
grouping for Tamiyo Scroll, raised in conversation and scoped/decided the
same day — resolves S5's previously-open "what is a training session"
report-scope question; S5's dependency row now includes S9); and, while
R5 was drafting the ADRs for these decisions, **S2's deck-validation gate
deferred to v3.0.0** (§1.6), the same treatment already given to S10 —
S2 no longer depends on S8 for v2.0.0; **updated again 2026-07-30** with
a new item, **I9/§1.10** (a card-name validation gap discovered while
scoping T3: `bs_deck_cards.card_name` has no authoritative MTG card list
to validate against, since S8 doesn't exist yet — decided that T3 now
**blocks on S8** rather than ingesting unvalidated strings, reopening
S8's scope to cover T3 in addition to S4; the `proj/v2.0.0-bump` T-group
work is on hold behind this until S8 is scoped); and, the same day, a new
item **S12** (UI/UX polish bundle — four small, independent
`tamiyo_scroll`-only fixes carried in from the feature-roadmap backlog:
a green `[new]` label on personal-deck creation (no icon library
needed), tested-cards/BO3-opponent select parity, the "Final turn"
label rename, and the matchup-summary "Games" → "Matches" column
rename; no schema/API impact); and, the same day, **a missed
dependency on S2's row corrected**: S2's Done statement/UAT already
assumed team members can open a shared deck's PDF report (S5's
deliverable), but S2's dependency row never listed S5 — now added,
alongside a reciprocal "blocks S2" note on S5's row; and **S3 completed**
— the remaining Moxfield-staleness sub-feature (brought into scope
2026-07-27) shipped, storing the full raw Moxfield response per version
(`moxfield_data` JSONB) rather than a single timestamp column, and
surfacing a `moxfield_deck_changed_since_last_import` flag on re-import,
tested against a real fetched Moxfield response
(`tests/fixtures/moxfield_deck_response.json`), not a hand-written
guess. **Every item in §1 is now decided.** A decision recorded
here is not yet a committed ADR — per Constitution §16.2 ("never guess
requirements... changing deployment architecture, introducing a
dependency, handling secrets"), each item was written in the
Context/Alternatives/Trade-offs shape used by `architecture/decisions.md`
before being decided, and R5 still needs to turn each resolved item into
a real ADR. **Updated again 2026-08-02**: a documentation-sync pass —
the Group S/T/F status cells below (S1, S2, S9, T1, T2, F9) had fallen
behind their own subfolder pages and actual merged PRs; corrected here
to match. T1's subfolder page also had a stale **Status** row (claimed
CI/ops playbook were still open; PR #41 already shipped both) — fixed.
Per-app `CHANGELOG.md` files and `docs/content/` are being brought back
in sync in the same pass, see those files' own history for specifics.
**Updated again 2026-08-03**: a second documentation-sync pass — S6,
S10, and S11's own pages (and their Group S table rows below) still said
"Not started" despite being fully merged (`feat/v2-tamiyo-upgrade`,
ahead of `proj/v2.0.0-bump`); corrected. Same day, a new item **§1.11**
records the decision to cut an early **`v2.0.0-alpha`** release scoped to
Tamiyo Scroll only, ahead of the full v2.0.0 (which still needs Group T's
remaining items, S4, and S8) — see the new **Group RA** table in §2.
**Later the same day**, executing RA2 surfaced a structural gap in this
repository's branch protection (squash-only merges never advance the
git merge-base between two long-lived branches, so a conflict between
`proj/v2.0.0-bump` and `staging`, once squash-resolved in one direction,
resurfaces immediately in the other) — recorded as
[`consitution-amendment.md`](consitution-amendment.md) **Proposal 7**,
not yet reviewed, ahead of Group R's own `proj/v2.0.0-bump` → `staging`
promotion hitting the same thing later this release. **RA2 and RA3 both
completed the same day** using Proposal 7's workaround — RA3 hit it at
much larger scale (`main`/`staging` share no real ancestry since this
repo's first commit), confirming the mechanism generalizes beyond the
one pair of branches it was first found on. `v2.0.0-alpha` is now on
`main`; RA4 (tag) and RA5 (deploy) remain.
**Later still the same day**: preparing the Group T/D deployment chain
(D1 → S8 → {S4, T3} → T6 → {T7, T8} → D2) surfaced that **T7 and D2 each
depend on an item outside that chain** (T7 needs T4/T5; D2 needs F1) —
the user chose to fold F1/T4/T5 into the same tracked chain rather than
leave them dangling. **D1 completed the same session**: the checklist
lives at `docs/content/ops/deployment/new-service-checklist.md`. Starting
it surfaced that T1 had already built a concrete scheduled-job precedent
(`scripture_scraper`/`barrins_scripture.yml`) ahead of D1 existing — T8's
page and this table's T8 row are corrected accordingly (Barrin's
Scripture half partially done, not "not started"). Next up in the chain:
S8 (now unblocked on D1) and F1 (always unblocked, feeds D2) can both
start; T3 stays blocked on S8; T4 stays blocked on T2 (done).
**Updated again 2026-08-08**: a third documentation-sync pass — this
table had fallen behind its own subfolder pages again, this time by
several days of real progress (2026-08-05 through 2026-08-08) rather
than a wording gap. Corrected here to match. **S8's core pipeline
shipped 2026-08-05** (`Card`/`MTGSet` models, admin-gated
`POST /mtgjson/import`, public `GET /sets/*`/`GET /cards/*` reads),
immediately unblocking T3; a chunked-upsert performance fix followed
2026-08-07 (a 45-minute import cut to low minutes). Only S8's scheduled-
refresh mechanism remains open; S4 still hasn't started. **T3 landed
complete 2026-08-07**: `POST /internal/scripture/ingest`, the card-name
resolver validating against S8's data, and the standalone
`barrins-scripture-sweep` entry point are all built and test-driven —
superseding the originally-planned push + maintenance-gate + backoff
design with a periodic idempotent sweep (the archive stays the sole
handoff point, so a failed tick just gets picked up next tick; no
scraper-side retry logic needed). Not yet exercised against staging with
real data — see T3's own UAT. **T1's transfer work completed 2026-08-07**:
`mtg_scraper` and the old `mtg_decklist_cache` are both archived under
`barrins-archive`, and a fresh (not history-preserving — the old data's
schema doesn't carry forward, see T1's page) `Spigushe/mtg_decklist_cache`
now exists. Remaining: wiring the actual git submodule into
`scripture_scraper` and backfilling the new archive. **T8 closed its
remaining D1-checklist gaps and scheduled the sweep 2026-08-08**: the
sweep now runs on its own timer (independent of the daily scrape),
`SCRIPTURE_INGEST_TOKEN` is documented across `ops/my-server/secrets/`,
and a `deploy_env` var lets the sweep be validated against staging before
a production cutover. This also closes half of **D3**'s scope ahead of
D3 itself starting — D3's own page is corrected to reflect that only its
`docs/content/ops/security/secrets.md` write-up is still open, not the
`.env.example`/`ops/my-server/secrets/README.md` documentation. **T6 is
now startable**: its last two dependencies (T2, T3) are both done, on top
of I4 already being resolved — alongside F1, which remains untouched.
**Later still, same day**: T1's remaining "wire up the git submodule"
task landed — `scripture_scraper` now clones `output_dir` as a real
working copy of `Spigushe/mtg_decklist_cache` (not a plain directory),
and the sweep wrapper commits + pushes any pending archive changes at
the start of every tick, ahead of ingestion. Prompted by this: T8's
`SCRIPTURE_INGEST_TOKEN` documentation task (above) is **also revised**
— the "duplicate the value across both apps' secrets files, no automated
sync" decision is superseded by a new `scripture_ingest_token` role
(mirrors `github_token`), so the value now lives in exactly one place
per environment (`secrets/scripture/{staging,production}_ingest_token.txt`)
instead of two hand-synced copies. Both changes are code-complete but
**not yet exercised against real infra** — see T1's own UAT, in
particular confirming the shared `github_token` PAT actually has push
(not just read) access to `Spigushe/mtg_decklist_cache`.
**2026-08-10, ADR-12**: mtgo.com started blocking the VPS's static
outbound IP specifically (see
`docs/content/service/barrins_scripture/incidents/2026-08-10-mtgo-network-block.md`).
Two same-day MTGO scraper fixes (eager page-load strategy, page-load
timeout scaled across retries) did not resolve it — the network block is
IP-specific, not a client-side timing issue. Fix: scrape+sweep scheduling
moved off the VPS's `scripture_scraper` systemd timers entirely, onto
`.github/workflows/scripture-scrape.yml` (GitHub Actions' rotating
runner IPs, confirmed unaffected). T1's and T8's rows are corrected
accordingly; the VPS role stays in the repo, dormant, as a rollback path
only. **2026-08-11**: a local `--mode full` sweep against a dev
`barrins_api` populated `bs_rounds`/`bs_standings` for the first time,
the MTGO-only fields T3's page flagged as unverified — not yet the
staging exercise T3's UAT calls for, but the first confirmation the
ingestion path works end to end for MTGO data at all.
**2026-08-14**: T5 started — confirmed unblocked (T4 shipped 2026-08-11
fully public/no-auth; I1's project-wide resolution already covers this
case) and scaffolded against T4's real routes. A previously-undiscovered
design handoff (`t5-tolaria-news-frontend/handoff/design_handoff_tolaria_news/`)
surfaced mid-build, describing a much larger, speculative app against an
unimplemented `/bff/v1/*` API; scoped by the user to a **restyle only**
of the already-scoped T5 — visual design system adopted, the handoff's
larger IA/BFF not built. `/metagame`/`/archetypes`/`/trends` are prepared
ahead of T4 iteration 2 behind a new `VITE_FEATURE_KARN_TABLETS` flag
(default off), mirroring the same not-yet-built-but-ready pattern already
used elsewhere in this plan. See T5's own page for full detail.
**Same day, S4 shipped** (previously blocked on S8, done since
2026-08-05): a structured Commander/Library decklist view
(`ResponseDecklistView`, superseding the old flat colored-line list),
card-type sort/grouping shared between `tamiyo_scroll` and
`tolaria_news` via a new `app/services/decklist_sort.py` module, and a
disk-cached Scryfall image proxy (`GET /api/v1/cards/{scryfall_id}/image`,
`app/services/scryfall/`) used by both apps' new hover-card image
previews. Shipped against a written spec rather than a hifi mockup, and
narrower than originally decided in two respects — sort is a fixed
order, not the two-criteria user-selectable sort originally spec'd, and
no dedicated face-A-Land rule was implemented for multi-face cards; see
S4's own page for the full gap list. `barrins_api` now 500 tests
passing, 97.20% coverage; `apps/tamiyo_scroll` 232 tests,
`apps/tolaria_news` 14 tests, both frontends typecheck/build/lint clean.
**2026-08-18, F10 implemented**: `TSMetaDeck.personal_deck_id` (required
FK) + `TSMetaDeck.updated_at` (new, not in the original task list —
needed by the item 5/6 "most recently updated wins" rule, which had no
timestamp to compare against before this), backfilled via two chained
Alembic migrations
(`e91a4c7f2b56_add_personal_deck_id_to_ts_meta_decks.py`,
`f4b6d3a8c17e_add_metagame_roster_scope_to_ts_user_.py`) written inline
with locally-declared `sa.table()` mirrors rather than importing the live
ORM models, per Alembic's own convention. `_sync_opponent_deck_games`
reworked to duplicate-and-allocate instead of overwriting a differently-
owned opponent row in place. `build_merged_view` gained a separate
`filter_meta_decks_by_personal_deck` opt-in flag rather than overloading
its existing `personal_deck_id` parameter — `stats.py` and the
personal-deck PDF report route already relied on that parameter
returning the *full* roster with only matches narrowed, and reusing it
for `TSMetaDeck` filtering too would have silently changed their output;
caught by their own tests failing partway through implementation, not by
design. See F10's own page for the full implementation breakdown. Every
existing Tamiyo Scroll backend test that created a roster entry needed
`personal_deck_id` added to its payload (nine files) once that field
became required. `barrins_api` now 582 tests passing, 97.40% coverage.
**2026-08-23**: four new items, **S13-S16**, added from GitHub issues
[#79](https://github.com/Spigushe/barrins-project/issues/79)-[#82](https://github.com/Spigushe/barrins-project/issues/82)
(reported the same day, not part of the original v2.0.0 request) — a
missed accidental deletion in the Match journal (no confirmation dialog
existed anywhere for it) prompted a wider audit finding 4 of 7 delete
actions across the app unprotected (**S13**); a session-management
overhaul covering rename, editable dates, sort/pagination, per-session
color, a Match-journal session tag, and archive search/restore/auto-
archive (**S14**, all 9 of the issue's items, including the four it
labeled "related possible change," confirmed in scope by the user); the
long-requested ability to actually view/diff past decklist versions
(**S15**) — the version history list has existed since S3 but never
exposed a version's content, only its metadata; and a full semantic
pivot of the "Tested Cards" feature into a Removed/Added-card change log
(**S16**), the largest and only breaking one of the four — reusing
`tester`/`card_name` under new names rather than adding new columns,
which raises an unresolved question (kept open, not guessed) about what
happens to existing rows recorded under the old semantics. All four
scoping decisions (full pivot vs. additive for S16, full 9-item scope
for S14, editable end-date alongside start-date, shared `ConfirmDialog`
extraction for S13) were made by the user the same day, in the same
Context/Alternatives/Trade-offs shape as every other item in this
document. **Same day, S13 shipped**: `components/ui/confirm-dialog.tsx`
(no new dependency, built on the existing `Dialog` primitive) is wired
into the 4 previously-unprotected delete/archive actions (Match journal,
Card test, Decklist version, Session archive) and the 3 already-protected
spots (roster deck, personal deck, team) are refactored onto it, the
team flow's two-step invite-code-retype step preserved unchanged. Note:
an earlier same-day commit (`631e868`) had a docs-only diff (the `s13`–
`s16` planning pages themselves) but a commit message body describing
S13-S16 as already implemented — verified false before starting this
work; see S13's own page, "Implementation note," for detail. 232 → 248
`apps/tamiyo_scroll` tests, `tsc -b`/`oxlint` clean.
**2026-08-24, S14 shipped**: all 9 items — `ts_sessions` gains
`started_at`, a separate freely-editable `ended_at`, `hue`, and
`location`; the pre-existing `ended_at` (Close/Reopen's workflow state)
is renamed `closed_at` (tracked separately from the new `ended_at`, per
the user, reversing this doc's original single-column plan); `GET
/sessions` gains `sort_by`/`sort_dir`/`limit`/`offset`/`search`; a `PATCH
.../restore` flag backs a new "Archived sessions" dialog. Auto-archive
(item 9) turned out not to need a periodic job at all — the user
redirected it to an event-triggered sweep (runs inside
`personal_decks.py`'s decklist-version creation, both Moxfield and
plain-text import), sidestepping the scheduler open question entirely.
Hue is a native `<input type="range">` (no new dependency) and replaces
the type-based color on every session tag app-wide (`SessionTypeBadge`),
not just where the picker is shown — see S14's own page, "Implementation
notes," for the full list of decisions made during implementation.
**Same day, S14 follow-up**: the "New session" form originally kept its
pre-S14 shape (`name`/`type` only), leaving `location`/`notes`/
`started_at`/`ended_at`/`hue` edit-only despite S14 adding them to the
schema — closed by extending `SessionCreate` (`POST /sessions`) to
accept the same fields `SessionPatch` already does, and having the
create form reuse `SessionEditFields` (the shared component the row and
archived-dialog edit surfaces already used) instead of two raw inputs.
No schema/migration change — `started_at`/`ended_at`/`hue` already
existed as nullable columns on `TSSession` since S14.
**2026-08-24, S15 shipped**: `GET
/personal-decks/{id}/versions/{version_id}` returns the same structured
`ResponseDecklistView` shape as the existing latest-version
`decklist-view` route, for one specific past version; `GET
.../versions/{version_id}/diff` returns a **card-level** diff against
the immediately-prior version (by `version` number, correctly skipping
any version deleted in between) — resolved open question 1 in favor of
matching by card name (`decklist_diff.py`) rather than a plain line
diff, so reordering a decklist never appears as added+removed; lines
that aren't a card line still get a plain `difflib` line diff, same
fallback shape as `unparsed_lines`. `TSUserSettings.show_decklist_
version_diff` gates whether `VersionHistorySection`'s expand-in-place
view shows a version's full content or its diff against the prior
version — the two are mutually exclusive, not shown together (an
implementation-time refinement over this doc's original "diff is also
available" framing). Defaults **`true`** for every account — reversing
this doc's own default-`false` assumption, a same-day decision made
after the migration was first drafted with `false`.
**2026-08-24, S16 shipped**: Open question 1 resolved by the user —
option 1, existing `ts_card_tests` rows keep their pre-pivot values
under the new `removed_card_name`/`added_card_name` column names,
documented as a known migration artifact, nothing cleared.
`TSUserSettings.validate_removed_card_in_decklist` ships defaulting
**on**, not off as originally drafted — a same-day decision made after
reviewing the migration, mirroring S15's `show_decklist_version_diff`
opt-out convention; `validate_added_card_exists` stays opt-in (default
off) since it resolves against `mj_cards`, Magic-only. Beyond the
drafted scope, a **post-approval addition**: a card test whose
removed/added names match a real decklist change (anywhere in a deck's
version history, matched independently per half) has its note shown as
a comment on that diff line in `VersionHistorySection`; a card test
matching nothing shows up instead in a standalone list on
`CurrentDecklistSection` — both gated by `show_decklist_change_log`
(new `app/services/tamiyo_scroll/card_test_matching.py`, new `GET
/card-tests/change-log`, `card_test_notes` added to the existing
decklist-diff response). The stale "prefill Removed Card with my own
display name" autofill — a leftover from the pre-pivot "who's testing"
semantics — is removed outright, not renamed. Full backend suite green,
`ruff format`/`ruff check`/`ty check` clean; frontend `tsc -b`/`oxlint`/
`prettier --check` clean on every touched file (one pre-existing,
unrelated gap: `src/demo/api/personalDecks.ts` never implemented S15's
`getDecklistVersionView`/`getDecklistVersionDiff`, not fixed here).
**2026-08-24, new item S17 added**: a further split of the same
`TSCardTest` table S16 just pivoted — a "card log" (removed/added card
name only) separated from a new, one-to-many "match-up evaluation" child
entity (opponent deck + rating), addable only from the edit form, plus a
new "pending"/blue decklist state for a card log with no evaluations yet,
on-the-fly name dropdowns on both fields, and an inline removed→added
row display directly in the decklist (replacing the separate "card change
being considered" block S16 added). Unlike S13-S16, **not** sourced from a
GitHub issue — came from a user-authored scratch note
(`docs/project/v2.0.0-bump/new-s17.md`), formalized into
`s17-card-log-matchup-evaluations/index.md` and removed. Verified against
the code before writing the page: `GET /cards/search-by-name/{name}` is,
despite its name, an exact-match lookup, not the partial/prefix search
item 2 needs — a new endpoint is required, not a reuse. Four points in the
draft were genuinely underspecified and recorded as blocking Open
questions rather than guessed, per Constitution §16.2 and the same
precedent S15/S16 set for their own open questions. **Resolved the same
day**: a new `TSCardTestEvaluation` table holds `opponent_deck_id` (now
required, unlike today's optional field), `rating`, and its own optional
`notes`, many per card log — `TSCardTest` keeps its own overall `notes`
plus the removed/added names; existing rows are backfilled one evaluation
each, carrying over their old `opponent_deck_id`/`rating` unchanged, no
data lost. Decklist-line coloring keeps today's behavior of pooling
evaluations across every card log sharing an added-card name (not scoped
to the single most recent one). The "pending"/blue open question turned
out to be miscast as a binary choice between the two originally-drafted
readings — the user's actual answer reframes it: pending has nothing to
do with evaluation count on the *added* card, it's whether the swap has
been executed in the decklist yet. A line is pending when its card name
matches a card log's `removed_card_name` **and** that name is still
present in the current decklist content — rendered inline as the
struck-through-name → arrow → new-name row item 3 described. Pending and
the evaluation-based states (`validated`/`rejected`/`in_test`/`neutral`)
are independent axes; `in_test` is untouched. Scoping is now complete —
implementation has not started.
**Same day, S17 implementation started and surfaced a new, project-wide
gap**: the first cut of `DELETE /card-tests/{id}` was a real SQL DELETE,
and because `TSCardTestEvaluation.test_id` cascades, deleting a card log
silently destroyed every evaluation logged against it. The user's
correction was general, not S17-specific: **by default, every delete
action in this application is a disguised archive** — the row leaves the
user's active view but stays in the database. Recorded as Constitution
Amendment **Proposal 8**
(`docs/project/v2.0.0-bump/consitution-amendment.md`), applied the same
day as the new `§11.8` (unlike Proposals 2-7, which are still awaiting
their ADR/merge pass). An audit of every delete route in
`apps/barrins_api` found the same inconsistency already existed
project-wide: `TSPersonalDeck`/`TSMetaDeck`/`TSSession` already
soft-delete via `archived_at`, but only `TSSession` can actually be
restored; `TSCardTest`/`TSCardTestEvaluation`, `TSMatch`, `TSTeam`'s full
cascade family, and `TSPersonalDecklistVersion` were all real hard
deletes. `TSCardTest`/`TSCardTestEvaluation` were converted immediately
as part of finishing S17 (new `archived_at` columns, migration
`6cf95145f67e`); the rest is tracked as new item **S18**. Two conflicts
with prior deliberate design decisions were resolved by the user the same
day: Team deletion converts to archive (dropping its "intentional
exception" status); decklist version deletion stays a hard-delete
exception, per the existing Option G rationale.

---

## 0. What's verified before writing this plan

Everything below was confirmed directly against the repositories on
2026-07-25, not assumed:

- `Spigushe/barrins-project` (`staging` branch): `apps/barrins_api`
  (FastAPI) + `apps/tamiyo_scroll` (React/Vite) are the only apps with
  real code. `apps/tolaria_news` contains only a one-line `README.md` and
  a placeholder `CHANGELOG.md` — confirmed via the repo, matching what
  `docs/content/ops/roadmap.md` already states. `apps/barrins_identity`
  likewise has only a `README.md`/`CHANGELOG.md`, no application code.
- `ops/my-server/tolaria_news.yml` already exists and explicitly notes
  in its own comments that `apps/tolaria_news` "currently has no
  application code (README.md only)". It deploys `apps/tolaria_news`
  **from this same monorepo** (`react_frontend_repo_subdir:
  apps/tolaria_news`), not from a separate repository — this matters for
  §1 below, since it means Tolaria News is expected to live in-repo, not
  as an external service.
- `docs/content/back/barrins_api/bff/tamiyo_scroll.md` (the Tamiyo Scroll
  BFF implementation plan) explicitly describes the scraped-tournament
  domain as a **separate, pre-existing thing** ("mirroring the `dl_`
  prefix used by `docs/decklist_integration/` for the scraped tournament
  domain", "Same router/service separation as `tolaria_news`
  (`docs/tolaria_news/00_plan_general.md`)"). Neither
  `docs/decklist_integration/` nor `docs/tolaria_news/00_plan_general.md`
  exist anywhere in the repository (checked by full-repo search). Nor do
  `dl_decks`/`dl_tournaments` ORM models — `apps/barrins_api/app/models/`
  only contains `tamiyo_scroll.py`, `user.py`, `email_verification.py`,
  `base.py`, `_types.py`. **The scraped-tournament data domain does not
  exist in code today.** It's referenced as if it already existed, but it
  doesn't — see item **F7** below.
- `mtg_scraper` (public, `barrins-project/mtg_scraper`) is a real,
  working Python 3.13 scraper (MTGO + MTGTop8 sources), run daily via
  GitHub Actions (`.github/workflows/daily_scraping.yml` +
  `biweekly_check_gaps.yml`). It writes JSON output into a `scraped/`
  git submodule pointing at `mtg_decklist_cache`, and pushes commits to
  that submodule directly from CI (`secrets.PAT_TOKEN`) — **there is no
  database in this pipeline today.**
- `mtg_decklist_cache` (public, `barrins-project/mtg_decklist_cache`) is
  a pure JSON-file archive, organized `<source_domain>/<year>/<month>/
  <day>/<slug>.json` (e.g. `mtgo.com/2026/03/23/legacy-league-2026-03-
  2310381.json`). This **already is** the "save scrapes as JSON so they
  can be replayed" mechanism the user asked about in §1 — it's not a new
  idea, it's the current system of record, just not queryable by an API
  yet.
- `barrins-project/tolaria_news` (the third connected repo listed in the
  request) returns **HTTP 404** — it does not exist, or is private with
  no public landing page. It could not be cloned or read. Nothing below
  is based on its contents; if it exists privately, its content is
  unknown to this plan.
- "Karn Tablets" and "Barrin's Scripture" appear nowhere in the
  `barrins-project` repository, its docs, or its constitution
  (`docs/content/CLAUDE.md`, 2270 lines, checked). These are new names
  introduced in this conversation, not carried over from prior planning.
  The same is true of **"Goblin Guide"** (the future frontend for
  Barrin's Identity) — not found anywhere in the repo either. Barrin's
  Identity itself *is* already named in
  `docs/content/back/barrins_identity/platform.md`, but only as a
  "Future consideration," with no committed timeline before now.
- `apps/tamiyo_scroll/src/components/layout/SharingControls.tsx`
  **already exists**, fully built and tested
  (`SharingControls.test.tsx`), but is gated off by a
  `const SHARING_ENABLED = false` constant
  (see `docs/project/v1.0.0-bump/a2-sharing-extraction/`).
  The backend enforcement (`ownership.resolve_owner`,
  `ts_user_settings.data_shared`) is live and has its own test suite
  (127 tests total for the Tamiyo Scroll BFF). This is highly relevant
  to item **2.5** below — re-enabling read-only sharing is mostly
  already done.
- Every app is currently at `1.0.0`, released 2026-07-24
  (`docs/CHANGELOG.md`, `apps/*/CHANGELOG.md`), one version number shared
  across the monorepo.

---

## 1. Scope decisions requiring the user's input before work starts

These follow the same escalate-don't-guess pattern as
`architecture/decisions.md`'s ADRs. None are answered definitively here.

### 1.1 Where does Barrin's Scripture's code live, relative to `mtg_scraper`?

**Context.** The request describes "Backend service: `barrins_scripture`
under `apps/barrins_scripture`" — i.e. inside the `barrins-project`
monorepo, the same pattern `tolaria_news` already follows. But the
scraping code that actually exists today is a **separate, standalone
public repository** (`barrins-project/mtg_scraper`), with its own CI,
its own submodule (`mtg_decklist_cache`), its own versioning
(`CHANGELOG.md` at `0.2.0`).

**Alternatives.**

1. Merge `mtg_scraper`'s code into the monorepo at `apps/barrins_scripture`
   (via `git subtree`/`filter-repo` to preserve history), retire the
   standalone repo (archive it, redirect its README), and either keep
   `mtg_decklist_cache` as an external submodule or fold its role into
   the new service.
2. Keep `mtg_scraper` as its own repository (rename it
   `barrins-project/barrins_scripture` on GitHub), and have the monorepo
   reference it the way `ops/my-server/` references any external
   dependency — no `apps/barrins_scripture` folder in the monorepo at
   all, just a deployment playbook that clones the external repo.
3. Treat `apps/barrins_scripture` in the monorepo as a **new**
   implementation that supersedes `mtg_scraper` (a rewrite, not a
   migration), and archive `mtg_scraper` once feature parity is reached.

**Trade-offs.** Option 1 matches the literal wording of the request
("under `apps/barrins_scripture`") and the precedent already set by
`tolaria_news`, but is real migration work (history-preserving merge,
CI workflow rewrite from a per-repo GitHub Actions setup into whatever
this monorepo's `.github/workflows/CI.yml` does) and means losing
`mtg_scraper`'s independent release cadence. Option 2 is the least
migration work but contradicts the "under `apps/barrins_scripture`"
framing and the `tolaria_news` precedent, and keeps a second,
differently-structured CI/release process alongside the monorepo's own.
Option 3 avoids a risky history-rewrite but throws away a working,
already-scheduled, already-tested (0.2.0, several bugfix releases)
scraper and re-derives its logic from scratch.

**Decided (2026-07-25): Option 3.** `apps/barrins_scripture` is a **new**
implementation that supersedes `mtg_scraper` — a rewrite, not a
history-preserving migration. `mtg_scraper` is archived (repo archived on
GitHub, README redirected to the new location) once
`apps/barrins_scripture` reaches feature parity: MTGO + MTGTop8 scraping,
the same daily/biweekly-gap-check scheduling, and the same JSON-archive
output (§1.3). This unblocks I2 and every Group T item depending on it
(T1–T3).

**Addition, clarified by the user (2026-07-26): not a time constraint,
a given.** The GitHub organization currently hosting
`mtg_scraper` and `mtg_decklist_cache` (`barrins-project`) **will be
deleted** — but only by the user's own deliberate action, once
everything is shipped and the org is no longer needed. There is no
deadline and no data-loss race: the user won't delete it until the
transfer is done and confirmed. **What this does mean for planning**:
T1 must not conclude `mtg_decklist_cache` stays at its current name/
location in `barrins-project` indefinitely — it *will* move. Both repos
get transferred (full history preserved, e.g. `git clone --mirror` +
push) to a durable location (a different org, or under the `Spigushe`
account — **not yet specified**) whenever there's confidence to do so.
This can be sequenced as a normal part of T1's migration work, not a
rushed, decoupled emergency step ahead of it.

### 1.2 Does Barrin's Scripture get direct database access?

*This is the question the user asked to be formulated, not answered
unilaterally — presented in the same shape as the existing ADRs.*

**Context.** Barrin's Scripture's job is scrape → normalize → persist.
Constitution §4.1 ("Backend owns business logic") and §26.1 ("one
application, one playbook", independent deployability) both push toward
keeping data-model ownership inside `barrins_api`, which is already the
sole owner of every other domain table (`users`, `ts_*`). Constitution
§13.1 ("do not create application-specific user tables") is precedent
for "one app owns identity" that generalizes naturally to "one app owns
the schema."

**Alternatives.**

1. **Barrin's Scripture holds its own `DATABASE_URL` and writes directly**
   to `bs_*`-style tables it also owns/migrates (`bs_` naming decided
   2026-07-26, see the Group T table's T2 row below).
2. **Barrin's Scripture never touches Postgres.** It scrapes, writes the
   JSON archive (as today), and calls a private, backend-only ingestion
   route on `barrins_api` (e.g. `POST /internal/scripture/ingest`,
   authenticated by a service credential, never exposed to any frontend)
   that performs the actual insert/upsert. `barrins_api` remains the sole
   owner of the schema and its Alembic migrations.
3. Barrin's Scripture writes to a **separate database/schema** it owns,
   and `barrins_api` reads from it (via a read replica, a foreign data
   wrapper, or a second `DATABASE_URL` configured read-only) to serve the
   Tolaria News BFF.

**Trade-offs.**

- Option 1 is the simplest data path (no extra HTTP hop) but duplicates
  what §26.1's "one application, one playbook" already warns against for
  infrastructure, applied here to schema ownership: two codebases
  (`barrins_api`'s Alembic and Barrin's Scripture's own migration
  tooling) would both need to agree on the same tables' shape, and a
  schema change in one has to be coordinated with the other by hand. It
  also means shipping a second Postgres credential with write access to
  production data to a scheduled scraper — a wider secret-exposure
  surface than today's single `barrins_api` `.env` (ADR-1's model).
- Option 2 keeps exactly one thing (`barrins_api`) owning the schema and
  the migrations, consistent with every other domain in this project
  (`users`, `ts_*`) and with `signup_email_verification.md`'s existing
  pattern of a dedicated internal service boundary. It costs one more
  internal-only route and a service-to-service credential (same shape as
  the already-existing `github_token`/Moxfield-credential precedent:
  narrow-scope, backend-only, never reaching a browser). It also means
  Barrin's Scripture can be redeployed, rolled back, or reworked without
  ever needing a database migration of its own.
- Option 3 avoids any HTTP coupling but introduces a second database (or
  schema) to operate, back up (Constitution §36 already flags backups as
  a real operational cost — a second DB doubles that surface), and
  monitor, for a marginal benefit over option 2's single extra route.

**Decided (2026-07-25): Option 2**, for the reasons already given above
— zero new infrastructure, one schema owner, and Barrin's Scripture stays
as replaceable/independently deployable as `tolaria_news` or
`tamiyo_scroll` are today.

**Additional requirement, confirmed by the user**: the internal ingestion
route (`POST /internal/scripture/ingest`) must be able to **contain
(reject or queue) upsert requests during maintenance windows**, rather
than either failing opaquely or writing against a database mid-migration.
Concretely, this needs a maintenance-mode gate `barrins_api` checks
before performing the write — e.g. a settings-backed flag or a narrow
`maintenance_mode` check scoped specifically to this route (not a global
maintenance page; the rest of the API keeps serving normally). Barrin's
Scripture's scraper keeps running on its own schedule regardless — the
gate sits on the ingestion call, not on the scrape itself — so a scrape
taken during a maintenance window is simply retried against
`/internal/scripture/ingest` once the window closes; the JSON archive
(§1.3) makes that a safe replay, not a lost scrape. Designing this gate
belongs to T3; recorded here since it's a direct consequence of this
decision.

### 1.3 Should scrapes still be archived as JSON, outside the database?

**Answering the specific question asked**: yes — but this isn't a new
requirement to design, it's the **existing** behavior of
`mtg_scraper`/`mtg_decklist_cache`, which already writes every scrape to
a JSON file, committed to git, before (today: instead of) any database
write. Whatever Barrin's Scripture becomes, keeping this archive is cheap
(it's already built, tested in production since well before this
conversation) and gives exactly the "replay after a server issue"
property asked for: the DB can be dropped and fully rebuilt by replaying
the JSON archive through the ingestion path (§1.2 option 2's route, or
a bulk-load script). The only open question is **where** that archive
lives once Barrin's Scripture moves (§1.1) — as the same `mtg_
decklist_cache` git submodule, or migrated to object storage (e.g. the
VPS's disk, rotated like `postgres_backup`'s dumps) if the git-submodule
approach doesn't scale as scrape volume grows.

**Decided (2026-07-25)**: archiving continues, and the monorepo structure
itself now needs a dedicated **dump sub-repo** for it — not just "the
same `mtg_decklist_cache` submodule, left as-is." The archive is already
gigabytes in size today, and every additional data-heavy domain this
release adds (Tolaria News' scraped-tournament data, Barrin's Scripture's
own output once it moves per §1.1) compounds that. Cloning
`barrins-project/barrins-project` should stay cheap regardless of how
much archived scrape data accumulates, so the archive keeps living in its
**own** git repository (a submodule — either the existing
`mtg_decklist_cache` or a renamed successor), never inlined into the
monorepo's own history. This is no longer "not urgent" — it's a
constraint T1 and T3 need to design against from the start, since
retrofitting it once the archive has grown further only gets more
expensive. Flagged for T1 (repo migration) and T3 (ingestion pipeline) to
apply; see also [`consitution-amendment.md`](consitution-amendment.md)
for the durable "heavy data stays out of the primary repo" rule this
generalizes to.

**Compounding with §1.1's addition above**: "either the existing
`mtg_decklist_cache` or a renamed successor" isn't a permanent-location
question — it *will* move eventually, per the user. The dump sub-repo's
new, durable home needs picking (same open question as §1.1: a
different org, or under `Spigushe`) as part of T1's transfer whenever
that happens, not on any particular deadline.

### 1.4 Karn Tablets' scope for v2.0.0

**Context.** The request describes Karn Tablets as "the backend service
in charge of computing/providing ML and DL data" with no further detail,
and no prior planning for it exists anywhere in the repository or
constitution.

**Original recommendation (superseded below)**: scope Karn Tablets **out
of v2.0.0's delivered features**, landing only a placeholder
`apps/karn_tablets/README.md` + docs stub, on the grounds that a full
ML/DL service is a substantial, open-ended scope (model choice, training
data volume, inference hosting, a fourth backend to secure and monitor)
that risks absorbing the whole release if pulled in now. Kept here for
context — no longer the decision.

**Decided (2026-07-26): Karn Tablets ships real, if deliberately basic,
functionality in v2.0.0** — not placeholder-only. Scope, as confirmed by
the user:

- **Clustering**: cluster the metagame (deck archetypes seen in scraped
  tournament results) over a defined time window. Two candidate
  windowing strategies were both named, not narrowed to one:
  1. A **rolling 30-day window** — always the most recent 30 days of
     data as of the run date.
  2. A **banlist-period window** — non-overlapping periods aligned to
     Magic's Banned & Restricted announcement rhythm: each period runs
     from the **last Tuesday of an odd-numbered month** to the **last
     Monday of the following odd-numbered month** (e.g. the last Tuesday
     of March to the last Monday of May) — the metagame is expected to
     shift meaningfully at each banlist change, so clustering per-period
     rather than on a fixed rolling window may better reflect a stable
     format snapshot.
  Whether v2.0.0 needs both modes or just one as a default is not yet
  decided — flagged as a task for T6, not guessed here.
- **Aggregation**: aggregate the clustering output specifically to
  visualize **deck-type** distribution (i.e. archetype share of the
  metagame within the chosen window), not raw per-deck predictions.
- **"Predictions"** is named in scope but not further specified — read
  here as the natural next step once deck-type clusters exist (e.g.
  matchup/impact estimation per Constitution §45's already-anticipated
  "card impact weighting... matchup analysis"), not a separate,
  unscoped deliverable. Exact prediction targets still need defining
  before implementation.
- **Tooling**: no ML library/framework is chosen here. Per the user:
  if additional tools are needed beyond what's already a project
  dependency, the existing dependency-approval process applies
  (Constitution §4.7/§22 — problem, alternatives, maintenance impact,
  approval before adding), not a new constitution rule. This work also
  falls squarely under Constitution §45 (Machine Learning Integration,
  already anticipating "macro archetype classification") and must
  follow §45.1 (ML stays isolated from frontend/auth/reports/core
  domain) and §45.2 (validated data, reproducible pipelines, documented
  datasets; every result carries source data/version/model info) — no
  constitution amendment needed for this decision.
- **Data dependency**: this needs real scraped-tournament data to
  cluster, so Karn Tablets' real implementation depends on T2 (schema)
  and T3 (ingestion pipeline) actually landing data, not just on I4
  being confirmed — see the Group T table below for the updated
  dependency.

This resolves I4. Karn Tablets moves from "placeholder scaffold" to a
real, scoped v2.0.0 deliverable — T6's page needs a full rewrite to
match, and T8's deployment-playbook item is no longer deferrable
alongside a placeholder.

### 1.5 Shared identity — carried over from the current roadmap

Already flagged in `docs/content/ops/roadmap.md` before this plan existed:
Constitution §13.1 requires one account across every application;
`barrins_identity` is unmerged. Adding **two** more applications this
release (Tolaria News frontend, and Team accounts for Tamiyo Scroll,
§2.1 below) makes this decision more urgent, not less — every new
"multi-user" feature (team membership, cross-app login) is easier to
build once, correctly, than twice. **This is the single most
schedule-critical open decision in this plan** — items T5, T7, S2 and
S1's "toggle to receive" extension all touch identity in some way.

**Decided (2026-07-25)**: delay `barrins_identity`'s implementation until
**two** front-end applications with real user management have shipped —
today only `tamiyo_scroll` qualifies; per T4/T5, Tolaria News is a
public, read-only BFF with no accounts feature planned for v2.0.0. This
generalizes the same v2/v3 split already confirmed for the admin metrics
dashboard in §1.7: don't build the standalone identity service
speculatively, wait until a second real consumer exists to design
against.

**The condition attached to this delay, stated explicitly by the user**:
it must not create technical debt. Concretely, every v2.0.0 feature that
touches identity (Tolaria News, if it ever gains accounts; Team
membership, §1.6) keeps using `barrins_api`'s existing single `users`
table and JWT auth directly, per Constitution §13.1 ("do not create
application-specific user tables") — rather than inventing an interim
account model per app that would later need migrating onto
`barrins_identity`. As long as that holds, delaying `barrins_identity`
costs nothing extra later: there's only ever one `users` table to
eventually move, not several divergent ones to reconcile. This resolves
I1 as **"not blocking, with a condition"** rather than "must be built
before T5/S2 start."

### 1.6 How are Teams created and who can create one? (item 2.1)

**Context.** The request flags this explicitly as undecided ("Need to
workout how the team is created"). No existing concept of a group/team
exists anywhere in the schema — `ts_*` tables are all single-owner.

**Alternatives.**

1. Any authenticated user can create a team and becomes its first
   member/owner; other users join via an invite code or a direct add by
   the team owner.
2. Teams are admin-provisioned only (matches `docs/content/back/
   barrins_api/auth_roles.md`'s existing admin/user role split, if
   team creation is judged sensitive enough to gate).
3. Defer "team" as its own entity entirely, and instead reuse the
   **existing** read-only sharing primitive (`ts_user_settings.
   data_shared`, already live) extended to a **set** of viewers instead
   of "anyone who knows to look" — i.e. no new `teams` table, just a
   `ts_share_grants` table (`owner_id`, `viewer_id`) replacing today's
   single boolean.

Option 3 is the cheapest to build (extends an already-tested mechanism
rather than inventing a new entity) but doesn't give a "Team Decks"
selector a real group identity to filter on unless a lightweight
`ts_teams`/`ts_team_members` pair is added on top — likely still needed
for item 2.1's "Team Decks" selector regardless of which option is chosen
for creation semantics.

**Decided (2026-07-25): Option 1, with a real `ts_teams`/`ts_team_members`
entity** (confirming the note above — a lightweight team identity is
needed regardless, so it's built now rather than deferred). Full spec, as
confirmed by the user:

- **Creation**: any authenticated user can create a team and becomes its
  first member/owner. No admin gate for v2.0.0.
- **Future gating, not v2.0.0**: team creation may later be restricted to
  the **"Advanced User" tier** — confirmed (2026-07-25) as the existing
  `role_c` placeholder (ordinal level 2 in `auth_roles.md`'s `UserRole`
  enum), finalized under that name in
  [`consitution-amendment.md`](consitution-amendment.md). **Not built
  now** — v2.0.0 ships open team creation; the gate is a later-release
  option, recorded so the `ts_teams` schema doesn't need reshaping to
  add it later (an owner/creator role check on an existing table, not a
  new one). **Per the user (2026-07-26): no reason for this future gate
  is stated here** (specifically, no paywall/monetization framing —
  see `consitution-amendment.md` Proposal 2's "What changed"). **Amended
  2026-07-26**: user roles are owned by `barrins_api` until
  `barrins_identity` is implemented (not framed as already
  `barrins_identity`'s concept beforehand). The API returns each user's
  actual role as-is, plus a separate backend-owned flag for whether that
  user may be moved up to Advanced User — that flag, not a frontend
  guess, determines when the UI shows a "this may evolve" comment.
- **Joining**: an 8-character invite code, generated per team, given out
  by existing members to anyone they want to invite.
- **Team page**: a dedicated page per team — name, description, member
  list, and one dedicated chat-like discussion thread **per deck under
  test** (not one thread per team) — which decks get a thread is decided
  by the team admin (the creator/owner).
- **Deck validation gate**: a deck shared into a team has its name (and
  cards) validated against backend-held MTG data before it's usable in
  that context. **Correction (2026-07-26)**: this was originally written
  assuming an existing `mtgjson`/`sets`/`cards` upsert pipeline —
  verified false. `auth_roles.md` and other docs describe a
  `POST /mtgjson/import` route and card/set data, but **zero Python
  files in the repository reference `mtgjson`** — no route, no `Card`/
  `Set` model, nothing beyond aspirational documentation (see new item
  **F8** and **S8** below). This deck-validation gate now depends on S8
  (building that pipeline from scratch), not on data "already in place."
  **Deferred to v3.0.0 (2026-07-27)**: rather than wait on S8, this gate
  is dropped from v2.0.0 scope entirely, the same treatment already given
  to S10. v2.0.0 accepts a team-shared deck the same way a personal deck
  is accepted today — unvalidated — so this introduces no new
  inconsistency; S8 itself stays in v2.0.0 scope (S4 still needs it) but
  S2 no longer depends on it.
- **Reporting**: team members get access to the PDF report (S5) of each
  deck shared into the team.
- **Deletion isolation**: removing a deck from a team never affects that
  deck's owner's individual results on their own profile — team-level and
  personal-profile data are independent views over data the owner still
  owns; deleting the team-share link is not deleting the deck or its
  match history.

**Ownership, added 2026-07-26** (`consitution-amendment.md` Proposal 3):
teams are groups of persons, modeled once ecosystem-wide (not
Tamiyo-Scroll-specific). `barrins_api` is the **interim** owner for
v2.0.0 (matching where `ts_teams`/`ts_team_members` actually live);
ownership transfers to `barrins_identity`/Goblin Guide once released. A
full generic "groups" subsystem (superseding this interim schema) is
expected to ship alongside `barrins_identity`'s own build-out — not
necessarily its first wave, timing not yet decided. Backend validation
of shared content (the deck-validation gate above) is **not** a
constitutional rule tied to teams — it stays a working direction to keep
pursuing in later Tamiyo Scroll releases, feature-by-feature, per the
user's explicit instruction not to over-generalize it.

This resolves I5. See [s2-team-sharing/](s2-team-sharing/index.md) for
the implementation breakdown of this spec.

### 1.7 Admin usage/metrics dashboard for Tamiyo Scroll

**Confirmed by the user since this was first scoped**: the metrics
portal itself must be available starting **v2.0.0** — but it is a
**v2.0.0-only interim shape**. Long-term, it externalizes into its own
standalone application, covering every publicly-deployed frontend (not
just Tamiyo Scroll), gated through a dedicated user-management pair:
**Barrin's Identity** (backend — already named in
`docs/content/back/barrins_identity/platform.md` as a future
consideration, not yet built) and **Goblin Guide** (frontend for it —
a name introduced in this conversation, appearing nowhere in the
repository, its docs, or the constitution before now, exactly like
Barrin's Scripture and Karn Tablets before it). Both are **explicitly
v3.0.0-scoped by the user — not to be embarked before then.** This
resolves one narrow piece of §1.5 (shared identity): for *this specific
feature*, v2.0.0 does not wait on `barrins_identity`. Tolaria News' own
auth and Tamiyo Scroll's team-sharing were **not** resolved by this at
the time this section was drafted — they were a separate question. Both
have since been decided in their own subsections (§1.5's delay-without-
debt condition, §1.6's team spec); this paragraph is kept as originally
written for context.

**What this means concretely for v2.0.0's scope**:

- The dashboard ships **embedded** in the existing apps for v2.0.0:
  backend routes live in `barrins_api` (not a new service), the UI lives
  in `apps/tamiyo_scroll` (not a new frontend), and admin access is
  gated by the **existing** `AdminUser`/`require_role(UserRole.admin)`
  mechanism already described above — no new auth system for v2.0.0.
- No premature app scaffold: unlike Barrin's Scripture/Karn Tablets
  (§1.1–1.4), there is **no `apps/`-level placeholder to create now**
  for the future standalone metrics app, Barrin's Identity, or Goblin
  Guide — all three are v3.0.0 work, out of scope for the
  `proj/v2.0.0-bump` branch entirely. (Whether `barrins_identity`'s
  existing README/CHANGELOG-only placeholder needs any update to mention
  Goblin Guide is a documentation nicety, not a blocker — not addressed
  here.)

**What v2.0.0's implementation needs to anticipate, per Constitution
§39** ("anticipate future features... without implementing them
prematurely" — simple today, extensible tomorrow), so the v3.0.0
externalization doesn't force a rewrite:

1. **Keep metrics computation as its own service module**
   (e.g. `app/services/metrics/`), not inlined into
   `app/services/tamiyo_scroll/` — a module boundary costs nothing now
   and is what actually gets lifted out wholesale when this becomes its
   own application later.
2. **Design the aggregated data with an app/source dimension from day
   one**, even though v2.0.0 only ever populates it with one value
   (`tamiyo_scroll`) — retrofitting a "which app is this metric about"
   column after Tolaria News and others start feeding the same rollup is
   exactly the kind of avoidable rework §39 is about. This does not mean
   building a multi-app aggregation *pipeline* now (YAGNI, Constitution
   §39/§48) — just not modeling the single-app case in a way that has to
   be undone.
3. **Don't couple the metrics routes' authorization directly to
   `barrins_api`'s specific role enum** any more than necessary — the
   v3.0.0 version authenticates admins via Barrin's Identity/Goblin
   Guide instead, a different provider. Depending on `AdminUser` (the
   convenience alias) is fine for v2.0.0; scattering direct
   `UserRole.admin` checks through the route bodies (rather than through
   the one dependency) would make the later swap harder than it needs to
   be.

**Still open, unchanged from before**: what "métrique" concretely means
(assumed: product/usage analytics — signups, active users, decks,
matches, sharing adoption — see the options considered above) and the
absence of any privacy/data-retention policy in the constitution. Neither
is resolved by the v2/v3 split; both still need confirmation before
S6 starts.

**Options considered for "métrique," restated for context**:

1. **Product/usage analytics**: signups over time, active users
   (daily/weekly), personal decks created, matches logged, card-tests
   submitted, sharing adoption (`data_shared` opt-in rate) — all
   derivable from existing `ts_*`/`users` tables with aggregate queries,
   no new data collection needed. *(Assumed default, unconfirmed.)*
2. **Operational/infrastructure metrics**: request latency, error rates,
   endpoint call volume — this overlaps with, and would likely duplicate,
   the existing HetrixTools setup (`operations/index.md`) rather than
   extend it; Constitution §4.2 ("no duplicated business logic")
   arguably generalizes to "no duplicated monitoring surface." If this is
   what's meant, it may belong in Group D (ops tooling) rather than as a
   Tamiyo Scroll admin page.
3. **Per-user moderation/support view** (e.g. "which accounts exist,
   when did they last log in") — touches account data more directly than
   1 or 2, and has sharper privacy implications.

**A gap worth naming plainly**: this project's constitution
(`docs/content/CLAUDE.md`, 2270 lines, checked) contains no privacy,
data-retention, or analytics policy at all — no section addresses
whether/how aggregate user data may be collected, retained, or shown to
admins. That's not a blocker for option 1 above (it aggregates data the
backend already holds for its normal function, nothing new is collected),
but it is a real, currently-undocumented gap that a dedicated admin
metrics *page* makes more visible than the data merely existing in the
database already did — and one that matters more, not less, once a
future *separate* application (with its own operator/access surface)
is the one showing it in v3.0.0. Worth a short written policy alongside
this feature, even if brief, rather than shipping it silently.

**Architecture for v2.0.0**: a new BFF sub-router
(`app/api/tamiyo_scroll/admin.py`, since v2.0.0 is explicitly
Tamiyo-Scroll-scoped per the user and the future cross-app version is
v3.0.0's job, not this one's), gated by `AdminUser`, calling into the new
`app/services/metrics/` module (point 1 above) which computes aggregates
server-side (Constitution §4.1/§4.2 — no raw data dump to the frontend
for it to compute on), plus a new admin-only route and page in
`apps/tamiyo_scroll`.

**Decided (2026-07-25): Option 1 confirmed** (product/usage analytics),
**staged**: ship the simplest signals first — account count, decks
created, matches recorded — specifically to establish whether the app is
being adopted at all, before investing in anything deeper. More in-depth
metrics (retention, per-feature engagement, sharing-adoption breakdowns)
are explicit follow-on work, not v2.0.0 scope. "Smart KPIs" beyond
adoption tracking are deferred until there's usage data to justify which
ones matter. Production analytics via this embedded dashboard is judged
**sufficient for v2.0.0** — no separate analytics tooling or vendor is
being introduced.

This confirmed the gap named above (no privacy/data-retention/analytics
policy in the constitution) was real and blocking in practice, not just
in theory. **Resolved 2026-07-26**:
[`consitution-amendment.md`](consitution-amendment.md) Proposal 1 (the
privacy/analytics policy this gap required) was reviewed and **accepted**
by the user, with one condition (any future GDPR alignment must extend
this policy, not replace it). Still outstanding: actually applying
Proposal 1's text to `docs/content/CLAUDE.md` (tracked via R5, not a
blocker for S6 starting design/implementation work).

---

### 1.8 Tutorial / demo interface for Tamiyo Scroll, no persistence

**Decided by the user**: option 1 (pure frontend, in-memory, no network
calls) — and demo + tutorial ship as **one single interface**, not two
separate deliverables or a fast-follow. Fixture data is authored in a
JSON file. Restated below with the decision folded in; the alternatives
considered are kept for the record.

**Request restated precisely**: a tutorial and demo interface, in one,
with pre-filled sample data from a JSON file, so visitors can discover
the app — explicitly **no persistence** of anything added during that
session.

**What exists to build on.** Routing is a plain `react-router-dom`
`<Routes>` tree in `App.tsx`; every real screen
(`MetagameTab`/`SuiviBo3Tab`/`DecklistTab`) is already wrapped
individually in `<ProtectedRoute><AppShell>...` — nothing else gates
access today besides that one component
(`components/layout/ProtectedRoute.tsx`, ~10 lines: redirects to
`/login` if `session.accessToken === null`). Every data-fetching hook
(`usePersonalDecks`, `useMatches`, `useMetaDecks`, `useCardTests`,
`useStats`, ...) is a thin TanStack Query wrapper around one of the
`src/api/*.ts` modules, which all funnel through the single
`src/api/client.ts`. There is currently no mocking layer in the
production dependency tree (`package.json` has no MSW or equivalent —
only `vitest`/`@testing-library/*`, dev-only).

**Confirmed design**:

- A parallel data-source module mirrors each `src/api/*.ts` file's
  function signatures (the shapes the existing hooks already expect),
  backed by fixture data loaded once from a single JSON file (e.g.
  `src/demo/fixtures.json`, a static import — Vite/TypeScript both
  support importing `.json` directly, no runtime `fetch` needed) and
  held afterward in local component/context state, reset fresh on every
  page load. A `DemoModeProvider` (or equivalent context) supplies this
  module in place of the real one; the existing tab components
  (`MetagameTab`, `SuiviBo3Tab`, `DecklistTab`) render **unmodified**
  against whichever source is active — the demo reuses the real UI, it
  doesn't fork it.
- The demo/tutorial route (e.g. `/demo`) is fully public — no
  `ProtectedRoute`, no token ever issued, no call to `barrins_api` at
  any point. This is what makes "no persistence" a structural guarantee
  rather than an operational promise: there is nothing to reset,
  isolate, or leak between visitors, because nothing ever leaves the
  browser tab.
- One single interface, confirmed: the guided tutorial is presented
  through the same seeded demo screens (e.g. a step/tooltip overlay
  pointing at the pre-filled data already on screen) rather than as a
  separate walkthrough or a second route — one PR, one experience.

**Alternatives considered before this was decided** (kept for context,
not live options anymore):

- **Real backend, a dedicated sandbox account whose writes get
  discarded** (scheduled reset or per-request rollback) — rejected:
  turns "no persistence" into an operational promise, has cross-visitor
  collision risk on a shared account, and is the first feature in this
  plan that would need a publicly reachable, unauthenticated **write**
  path into the real backend, against the spirit of Constitution
  §33/§34 (restrictive CORS, minimal exposed surface).
- **Real frontend, server-side ephemeral session store** — rejected:
  real new backend infrastructure (session store, expiry job) for a
  feature whose entire purpose is onboarding, not core product logic.

**Remaining open points** (not yet decided, listed so they aren't lost):

- Exact fixture content for `fixtures.json`: enough sample decks,
  matches, and card-tests across all three tabs to make the tour
  meaningful — invented for this purpose, never real user data, never
  derived from any real account.
- Entry point: most likely a link from `LoginPage` (which already has a
  footer line, "Account managed by `barrins_api`") — e.g. "Try the demo"
  — and/or from `RootRedirect` in `App.tsx`, which today sends every
  unauthenticated visitor straight to `/login` with no alternative
  offered.

**Decided**: the guided-tour overlay is hand-rolled with the existing
Radix/shadcn primitives already in `src/components/ui/`
(`popover.tsx`, `dialog.tsx`, `card.tsx`, ...) — no new dependency. This
also settles the Playwright question raised for this item (see the note
right after this section): a dedicated tour library was the only
plausible reason to bring Playwright into the demo/tutorial work, and
that path is no longer taken.

---

### 1.9 Restricting Tolaria News' public BFF routes to the Tolaria News app

**Context.** T4 decided the Tolaria News BFF routes are public reads,
requiring no `CurrentUser` (no per-user authentication — this is
unauthenticated tournament/metagame data, not personal data). The user
flagged (2026-07-26) that "public" shouldn't mean "open to any caller" —
these routes should be restricted to the Tolaria News frontend
specifically, "one way or the other," tentatively suggesting an agent
key. **Decided 2026-07-27** (Option 4 below): keep the routes open,
restrict by rate-limiting rather than by caller identity. Recorded per
Constitution §16.2 — the subjective boundary-vs-friction choice was
escalated to the user rather than guessed, and this entry captures the
answer.

**A constraint worth naming before the alternatives**: `apps/tolaria_news`
is planned as a static SPA (`react_frontend` deployment shape, per T5 —
"calling `barrins_api`'s BFF only," no server-side component of its own).
A secret embedded in a public static frontend's built JS bundle is
readable by anyone who opens browser devtools or downloads the bundle —
it doesn't function as a real access boundary, only as friction against
casual reuse. Any alternative below that assumes a hidden client-side
secret should be read with that limitation in mind. (This is why the
chosen option does not rely on a client-held credential.)

**Alternatives.**

1. **CORS restriction only** (§33): locks `Access-Control-Allow-Origin`
   to Tolaria News' origin. Stops other websites' JS, not direct scripts.
2. **A shared "agent key"** in the frontend build: extractable from the
   public bundle per the constraint above — friction, not a boundary,
   and cuts against §34 ("no secrets in the bundle").
3. **Reverse-proxy-injected header**: Tolaria News' own nginx vhost
   proxies `/api/*` to `barrins_api`, injecting a secret header the
   browser never sees — a real boundary, but flips T5's cross-origin BFF
   call into a same-origin proxy (nginx changes under §29/§26.1).
4. **Accept CORS + rate-limiting as sufficient** — "restricted to the
   Tolaria News app" as a soft goal, not a hard boundary, on the grounds
   that aggregated, already-public tournament results aren't sensitive
   enough to justify option 3's infrastructure.

**Trade-offs.** Options 1 and 2 are cheap but raise friction, not a
boundary, against a determined caller. Option 3 is the only real access
boundary but changes T5's calling pattern and adds an nginx-layer
credential to document (adjacent to `consitution-amendment.md` Proposal
4/5). Option 4 is honest about the trade-off rather than shipping
something that looks like security but isn't — its cost is that it does
not, and does not claim to, keep non-Tolaria callers out; it caps abuse
volume instead.

**Decision (2026-07-27).** Option 4. These routes stay open public reads.
The access posture is CORS (§33, existing `ALLOWED_ORIGINS`) as
browser-only friction, plus inbound rate-limiting as the anti-abuse
control. "Restricted to the Tolaria News app" is explicitly recorded as a
soft goal, not a boundary. Rationale: the data is aggregated,
already-public tournament/metagame results with no `CurrentUser` and no
personal data. The two realistic threats are (a) scraping-for-reuse and
(b) load/cost from abuse; only (b) is a harm independent of the data's
public nature, and rate-limiting addresses (b) directly. A true caller
boundary (option 3) buys protection against (a) that the public nature of
the data does not justify paying for. Option 4 is also the only choice
that leaves T4 and T5 unchanged (see Consequences).

**Risks / residual exposure.**

- **Volume control, not identity control.** A scraper pacing requests at
  a human-like rate is indistinguishable from a real reader and will not
  be blocked. The soft goal is genuinely soft — accepted, not mitigated.
  No one should later read the CORS entry as access control against
  scripts.
- **No inbound rate-limiting exists yet.** The only limiter in
  `barrins_api` today is the Moxfield importer's *outbound* limiter
  (module-level `asyncio.Lock`, per-process only — it politely caps our
  calls *to* Moxfield, ≤1 req/s), and inbound limiting on `POST
  /auth/token` is a recommended-not-done open item (P-03). So this
  decision is net-new work, not a config toggle.
- **Per-process trap.** A naïve in-app limiter under multiple
  `barrins_api` workers multiplies the effective limit by the worker
  count (the same single-process caveat the Moxfield limiter carries). A
  correct limit needs either a shared counter (Redis/DB, keyed per
  client) or enforcement at nginx (`limit_req`/`limit_conn`) — and since
  nginx already fronts every backend on `127.0.0.1:<port>` (§29) and is
  shared across all workers by construction, the nginx layer is the
  lower-effort, on-pattern home for coarse per-IP limits on these
  unauthenticated reads.
- **Tuning tension, undefined policy.** Per-IP limits are blunt: too
  tight throttles NAT'd / mobile-carrier / corporate clusters of
  legitimate users together; too loose stops nothing. The key, threshold,
  window, `429` response, and whether the limit is scoped to the public
  BFF routes or global are all currently undefined — a follow-up before
  these routes ship (tracked as a task on T4's page).

**Consequences for T4 / T5.**

- T4's done-statement ("no `CurrentUser` dependency") is **preserved** —
  rate-limiting adds no per-caller identity dependency to the route.
- T5's calling pattern is **unchanged** — the SPA keeps calling the BFF
  cross-origin; no same-origin reverse-proxy flip (that was option 3
  only).
- New work moves out of "route/auth" and into an **anti-abuse / infra**
  task: implement the rate limiter for the public reads with the policy
  above — at nginx (§29) if coarse per-IP is enough, or as a
  shared-state limiter in `barrins_api` if finer control is later needed.

This resolves I7. See also
[`consitution-amendment.md`](consitution-amendment.md) Proposal 6 for
the durable rule this surfaces: `barrins_api` has no inbound
rate-limiting anywhere today, a gap wider than just this one route.

---

### 1.10 Card-name validation gap discovered while planning T3

**Context.** While designing T3's ingestion route
(`POST /internal/scripture/ingest`), it surfaced that `bs_deck_cards.card_name`
(T2's schema) is a bare string with nothing to validate it against — no
authoritative MTG card list exists anywhere in this codebase yet (F8: the
MTGJSON pipeline described in `auth_roles.md` was never actually built).
Neither T3 nor **T6** (Karn Tablets' metagame clustering, the next real
consumer of this data — its archetype clustering keys off these exact
strings) currently routes through S8 in the dependency graph above. A
scraping glitch or an inconsistent/foreign spelling would go straight into
production `bs_*` data with nothing to catch it, and T6 would inherit
whatever noise results.

**Alternatives.**

1. **Ingest raw scraped strings verbatim, no validation** — mirrors the
   reasoning that deferred S2's deck-validation gate to v3.0.0 (§1.6):
   don't block v2.0.0 work on S8, which doesn't exist yet.
2. **Light normalization only** (trim whitespace/case) inside the ingestion
   route, with no check against any real card list — catches trivial
   scraper noise without waiting on S8.
3. **Block T3 on S8 outright**: validate every scraped card name against
   S8's card data at ingestion time.
4. **Ingest raw now, but record a tracked follow-up gap** (same treatment as
   F7/F8) so T6's clustering quality isn't silently assumed correct later.

**Trade-offs.** Options 1/2/4 ship T3 now but leave `bs_*` (and therefore
T6's clustering) built on unvalidated card-name strings, with no guarantee
scraped data will ever match a real card. Option 3 is the only one that
guarantees correct data from day one, at the cost of reopening S8's scope —
previously scoped to block only S4 — and pausing T3 (and transitively T6)
behind a pipeline that doesn't exist in code at all yet.

**Decided (2026-07-30): Option 3.** T3 is blocked on S8.
`POST /internal/scripture/ingest` will validate each scraped card name
against S8's card data before storing it, rather than accepting unvalidated
strings the way S2's now-deferred gate would have.

**Consequences.**

- S8's dependency/notes row (its own page, and the Group T/S tables below)
  now lists T3 alongside S4 as blocked items.
- T3's dependency row becomes T1, T2, S8 (was T1, T2) — its own page and
  the Group T table are updated accordingly. T6 (already depending on T3)
  is blocked transitively.
- The `proj/v2.0.0-bump` T-group branch goes on hold until S8 is scoped;
  work continues on Group S (Tamiyo Scroll) items in the meantime, which
  don't depend on this chain.
- Groundwork already designed for T3 during this scoping pass — the
  reject-not-queue (`503`) maintenance-gate behavior, the
  delete-and-reinsert approach for `bs_deck_cards` (needed because MTGO
  decklists are mutable for ~3 days after publication, not immutable as
  originally assumed), and the `X-Scripture-Token` service-credential shape
  — is recorded on T3's own page for whenever this resumes, not implemented
  yet.

This resolves **I9**.

---

### 1.11 Cutting an early `v2.0.0-alpha` release, scoped to Tamiyo Scroll only

**Context.** By 2026-08-03, every Group S (Tamiyo Scroll) item except S4
and S8 is done — S1, S2, S3, S5, S6, S7, S9, S10, S11, S12 are all merged
on `feat/v2-tamiyo-upgrade`, which branches directly off `proj/v2.0.0-
bump`'s current head (T1 + T2 already merged there, §1.1–§1.3). Group T's
remaining items (T3–T8: the ingestion pipeline, Tolaria News BFF/frontend,
Karn Tablets, docs, deployment playbooks) haven't started — T3 is still
on hold behind S8 (§1.10), and S8 (MTGJSON) itself hasn't started either.
At the current pace, the full `v2.0.0` (everything in this document) is
still some way off, while a large, user-facing batch of deck-management
improvements has been sitting done and undeployed. The user's call:
Tolaria News is not related to Tamiyo Scroll except insofar as S4/S8 use
MTGJSON card data to improve the decklist display — that piece can wait
for the full release. Ship the rest now, as its own tagged, deployed
pre-release, so real users can try the new deck-management features and
give feedback while Group T continues in parallel.

**Decided (2026-08-03): cut `v2.0.0-alpha`** from the current state of
`feat/v2-tamiyo-upgrade` — a real, tagged, production-deployed release
(not a staging-only preview), following the same branch → `staging` →
`main` → tag → deploy flow as every prior release (§3, mirrors v1.0.0's
B-group). In scope: every done Group S item (S1, S2, S3, S5, S6, S7, S9,
S10, S11, S12) — entirely `apps/tamiyo_scroll` + the Tamiyo Scroll BFF in
`apps/barrins_api`. Out of scope, unchanged from the full v2.0.0 plan:
S4, S8, and all of Group T (T3–T8) — none of it is done, none of it is
pulled forward.

**Two scoping calls made explicitly by the user, recorded here per the
same "escalate, don't guess" convention as the rest of §1:**

1. **T1 (Barrin's Scripture rewrite) and T2 (`bs_*` schema) ride along
   inert, rather than being stripped out of the alpha.** Both are already
   merged onto `feat/v2-tamiyo-upgrade` *ahead of* the Tamiyo Scroll work
   (it branched from `proj/v2.0.0-bump`'s post-T1/T2 head), so keeping
   them out would mean cherry-picking ~40 Group-S commits onto a fresh
   branch off `staging` and re-basing S10/S11's Alembic migration (which
   chains on top of T2's `49c50188ee55`) by hand — real rework and risk
   for a purely cosmetic diff. Instead: merge as-is, and rely on the
   existing per-app Ansible playbook structure (`ops/my-server/*.yml`,
   Constitution §26.1 — one playbook per application, run independently)
   to keep Barrin's Scripture **undeployed**: `barrins_scripture.yml`
   (the scraper's systemd service/timer) is simply not run during this
   release's deploy step (RA5 below). The `bs_*` Alembic migration still
   applies to production (it's additive — new, empty tables unrelated to
   any `ts_*`/`users` data — so there's no behavioral risk to Tamiyo
   Scroll), but no Barrin's Scripture code ever executes.
2. **The plan is written the same way as the rest of this document** — a
   new **Group RA** (Release Alpha) table in §2, mirroring Group R's
   shape (R1–R5) but scoped to just this cut, with its own per-item pages
   under `ra1-…`–`ra5-…`.

**What this does not change.** Group R (R1–R5) still describes the wrap
for the **full** `v2.0.0` tag, once Group T, S4, and S8 land — this
document now expects **two** tags in this release cycle
(`v2.0.0-alpha` now, `v2.0.0` later), not a renumbering of the existing
plan. `proj/v2.0.0-bump` keeps existing after RA-group work lands on
`staging`/`main` — Group T work (already on hold behind S8, §1.10)
resumes on it exactly where it left off.

**Left open, not guessed here:** whether every app's `CHANGELOG.md`/
version marker bumps to `2.0.0-alpha` together (continuing the "one
version number shared across the monorepo" convention noted in §0, even
for apps with zero changes this cut, e.g. `tolaria_news`) or only the two
changed apps (`barrins_api`, `tamiyo_scroll`) version-bump this time.
Flagged as a task on RA1's page rather than decided here.

This resolves nothing in the Group I table (it isn't a foundational
architecture decision — no new dependency, no secret, no deployment
architecture change) and so, per Constitution §16.2, doesn't need its own
ADR; R5's existing ADR-5–ADR-11 already cover every decision this alpha
actually ships.

---

### A note on Playwright — deferred, not part of v2.0.0

Playwright was suggested to the user during this planning process. It
doesn't fit item S7 (it's a browser-automation/E2E-testing framework,
not a tour-UI library — the primitives decision above settles that
question). Two other places in this project could plausibly use it,
and the user asked for a judgment call on each rather than a blanket
yes/no:

1. **A committed, CI-integrated E2E suite for `apps/tamiyo_scroll`.**
   Real value here isn't hypothetical: Playwright was already used
   informally during the original bootstrap
   (`docs/content/front/tamiyo_scroll/bootstrap.md` — "disposable
   Playwright scripts in the scratchpad" for phase 6-9 validation, and
   again for the 2026-07-16 regression check), and that same doc
   explicitly deferred committing it ("E2E can follow separately").
   Today, `.github/workflows/CI.yml`'s `front` job only runs
   `lint`/`build`/`npm test` (Vitest/Testing Library, unit+component) —
   no browser is ever launched in CI. Making this real means: adding
   `@playwright/test`, a browser-download step
   (`npx playwright install`), a new CI job that also needs
   `barrins_api` + Postgres running and a built frontend to point at
   (heavier than the existing `back` job, which only needs Postgres),
   and writing the scenarios themselves (signup, deck creation, match
   logging, sharing) — real, non-trivial work, not just configuration.
   **Judgment: defer, don't cancel.** It has already demonstrated value
   informally twice; v2.0.0's scope (three candidate new applications,
   several open architecture decisions) is heavy enough without also
   absorbing a first CI-integrated browser-test pipeline. Revisit as a
   dedicated item once v2.0.0's application-level work is further along
   — tracked here so it isn't lost, not scheduled.
2. **Replacing Selenium in the MTGO scraper** (relevant only once item
   T1's repo-migration decision lands). Contained footprint today: 4
   files, ~292 lines (`scraper/utils/selenium_driver.py`,
   `scraper/services/mtgo.py`, `scraper/utils/mtgo.py`), MTGO-only
   (MTGTop8 scraping doesn't use a browser at all). No open bug or pain
   point currently documented against Selenium in `mtg_scraper`'s
   `CHANGELOG.md` beyond one already-fixed reliability issue (0.2.0).
   **Judgment: defer, low priority.** Modernizing tooling with no active
   pain point isn't worth doing ahead of, or bundled into, the
   already-nontrivial T1 migration decision — if T1 lands on "merge into
   the monorepo" and whoever does that work wants to swap Selenium for
   Playwright at the same time, nothing here rules it out, but it isn't
   requested or required for v2.0.0.

Neither is part of the `proj/v2.0.0-bump` scope. Both are recorded here,
not in Group T/S's tables, specifically so they read as deferred
background context rather than committed work items.

---

## 2. Priorities and dependency graph

Work is grouped by theme (mirroring the `A`/`B` lettering convention from
`docs/project/v1.0.0-bump/`). Letters don't imply strict
sequential order within a theme, but the dependency column does.

### Group I — Foundational decisions (block everything else)

| # | Item | Depends on | Blocks | Status |
| --- | --- | --- | --- | --- |
| I1 | Resolve shared-identity approach (§1.5) | — | T5 (transitively, T7), S1 (receive-toggle), S2 | ✅ Resolved 2026-07-25 — delay confirmed, no-debt condition attached |
| I2 | Resolve Barrin's Scripture repo location (§1.1) | — | T1–T3 | ✅ Resolved 2026-07-25 — Option 3 |
| I3 | Resolve Barrin's Scripture DB-access model (§1.2) | I2 | T2, T3 | ✅ Resolved 2026-07-25 — Option 2 + maintenance-mode gate |
| I4 | Confirm Karn Tablets v2.0.0 scope (§1.4) | — | T6 | ✅ Resolved 2026-07-26 — real basic clustering/aggregation, not placeholder-only |
| I5 | Confirm Team creation model (§1.6) | — | S2 | ✅ Resolved 2026-07-25 — Option 1 + full spec |
| I6 | Confirm what "metrics" means for the admin dashboard, and confirm the v2.0.0-embedded / v3.0.0-externalized split (§1.7) | — | S6 | ✅ Resolved 2026-07-25 — Option 1, staged |
| I7 | Confirm how Tolaria News' public BFF routes are restricted to the Tolaria News app (§1.9) | — | T4 | ✅ Resolved 2026-07-27 — Option 4: stay open, restrict by rate-limiting, not caller identity |
| I8 | Choose the PDF-generation library for S5 (WeasyPrint vs. ReportLab vs. other) | — | S5 | ✅ Resolved 2026-07-27 — WeasyPrint, decided against the user's stability/security/no-data-loss criteria (see S5 page) |
| I9 | Confirm whether T3's ingestion validates scraped card names against real MTG data (§1.10) | — | T3 (transitively T6) | ✅ Resolved 2026-07-30 — Option 3: block T3 on S8, validate at ingestion |

**Nothing else in this document should start implementation before its
row in this table is resolved.** This mirrors how v1.0.0 itself required
resolving the backup-gating and monitoring-provider questions (ADR-4)
before B1/B6 could start. **Every Group I row is now resolved**, pending
R5 turning each into a real ADR.

### Group T — Tolaria News, Barrin's Scripture, Karn Tablets (request item 1)

| # | Item | Depends on | Notes | Page |
| --- | --- | --- | --- | --- |
| T1 | Migrate/create `apps/barrins_scripture` per I2's outcome | I2 | 🟡 **In progress — transfer done 2026-08-07, submodule wiring done 2026-08-08.** Rewrite (schemas/parsers/services/CLI), CI job, and the `ops/my-server` deploy playbook are done (130 tests, 95%+ coverage). `mtg_scraper` and the old `mtg_decklist_cache` are both archived under `barrins-archive`; a fresh `Spigushe/mtg_decklist_cache` exists (not a history transfer — old data's schema doesn't carry forward, see page). `scripture_scraper` now clones/pushes it as a real archive repo (the sweep commits+pushes each tick), not yet exercised against real infra (push-access UAT open). **2026-08-10**: mtgo.com started blocking the VPS's static outbound IP (see the service incident page and ADR-12) — scrape+sweep scheduling moved from the VPS's systemd timers to GitHub Actions' rotating runner IPs, confirmed unaffected. Still open: backfilling the new archive's history (MTGTop8 `--id-from` now supports this; MTGO's `--date-from`/`--date-to` already did) | [t1-scripture-repo-migration/](t1-scripture-repo-migration/index.md) |
| T2 | Design the scraped-tournament schema in `barrins_api` (the domain previously referenced as "`dl_*`" but never built — see §0, F7) | I3 | ✅ **Done (2026-08-11)** — `bs_*` models, Alembic migration (`49c50188ee55`), and 13 model tests done (253 passing, 98.30% coverage). Prefix decided as `bs_` (Barrin's Scripture), not `dl_` — `dl_` was inherited from a dead reference doc (F7), never a real convention. The `docs/decklist_integration/` doc decision (F7) is resolved (redirect, 2026-08-11). Migration confirmed applied to staging and every `bs_*` table confirmed populated by a real scrape (2026-08-11) — no longer blocking T4 | [t2-scraped-tournament-schema/](t2-scraped-tournament-schema/index.md) |
| T3 | Build the scrape → JSON-archive → ingest pipeline per I3's outcome | T1, T2, S8 (core done) | 🟢 **Both tasks implemented (2026-08-07), full-archive sweep confirmed against staging (2026-08-11)** — `POST /internal/scripture/ingest` (route, service credential, upsert/delete-reinsert logic, card-name resolver validating against S8) and the standalone `barrins-scripture-sweep` entry point (recent/full modes). **Design superseded 2026-08-07**: a periodic idempotent sweep replaces the originally-planned push + maintenance-gate + backoff — the JSON archive stays the sole handoff point, so a failed tick is just caught by the next one. **2026-08-11**: a `--mode full` sweep against staging confirmed every `bs_*` table populates correctly from a real scrape. Still open, not blocking T4: incremental-tick pickup and resilience when `barrins_api` is down mid-sweep — see page's UAT | [t3-scripture-ingestion-pipeline/](t3-scripture-ingestion-pipeline/index.md) |
| T4 | Tolaria News BFF routes (`/bff/tolaria-news/...`, corrected 2026-08-11 — see CLAUDE.md §12), publicly readable (no per-user `CurrentUser` requirement), access-restricted by rate-limiting per I7 (resolved) — already anticipated by a comment in `bff/tamiyo_scroll.md` ("unlike the Tolaria News BFF which is publicly readable") | T2 (done) | ✅ **Done (2026-08-11)** — `app/api/tolaria_news/` + `app/services/tolaria_news/` + `app/schemas/responses_tolaria_news.py`, mounted in `main.py`; 14 tests passing, full suite 455 passing/97.16% coverage, `ruff`/`ty`/`bandit` clean. **I7 resolved (Option 4, §1.9)**: no `CurrentUser`-style dependency added; nginx rate limiter written (`limit_req`, per-IP, `/bff/tolaria-news` scoped, `20r/s`/`burst=80`, tunable) via a new generic `backend_website_rate_limited_paths` role variable — not yet exercised against a live deploy. v1 route map: tournaments/decks/standings/decklist detail (+ derived commander/color-identity data) only — `/metagame`/`/archetypes` deferred to a T4 iteration 2 gated on T6/T8 (needs amending T6's admin-only consumption-surface decision) | [t4-tolaria-news-bff/](t4-tolaria-news-bff/index.md) |
| T5 | `apps/tolaria_news` real frontend (React/Vite), calling `barrins_api`'s BFF only — no direct DB/calculation client-side, per §4.1/§4.2 | T4 (done), I1 (resolved) | 🟡 **In progress (2026-08-14)** — app scaffolded against T4's real routes (tournament list/detail incl. bracket, deck detail), 12 tests/lint/typecheck/build all clean; `/metagame`/`/archetypes`/`/trends` prepared ahead of T4 iteration 2 behind `VITE_FEATURE_KARN_TABLETS` (default off); visual design restyled from the `handoff/design_handoff_tolaria_news/` design system (restyle only, not its larger speculative IA — see the page's Context). Staging deploy UAT not yet exercised. `ops/my-server/tolaria_news.yml` needs no changes. **I7 resolved as Option 4** — T5's calling pattern is unaffected (no same-origin proxy flip; that was option 3, not chosen) | [t5-tolaria-news-frontend/](t5-tolaria-news-frontend/index.md) |
| T6 | `apps/karn_tablets`: metagame clustering + deck-type aggregation per I4's decided scope (real service, not a placeholder) | I4, T2, T3 | 🔲 **Not started, but now unblocked** — T2 and T3 (this item's last two dependencies) are both code-complete as of 2026-08-07. Basic clustering/aggregation only for v2.0.0 (§1.4); windowing strategy (rolling 30-day vs. banlist-period) and prediction targets still need narrowing; any new ML dependency follows §4.7/§22 | [t6-karn-tablets-scaffold/](t6-karn-tablets-scaffold/index.md) |
| T7 | Docs: `docs/content/back/barrins_scripture/`, `docs/content/back/karn_tablets/` (now real content, not a stub), real content for `docs/content/front/tolaria_news/_links.md` | T1, T4–T6 | Follow the existing per-app docs pattern (`_links.md` + synced README) | [t7-new-apps-docs/](t7-new-apps-docs/index.md) |
| T8 | Deployment playbooks for Barrin's Scripture (scheduled job, not a web service) and Karn Tablets (real ML service per I4, shape TBD by T6) | T1 (done), T6, D1 (done) | 🟡 **Barrin's Scripture half done (2026-08-08), scheduling mechanism changed 2026-08-10** — `scripture_scraper` (shipped during T1) walked against D1's checklist (2026-08-05); the T3 sweep now runs on its own timer (independent of the daily scrape). `SCRIPTURE_INGEST_TOKEN` is now shared via the new `scripture_ingest_token` role (one value per environment, `secrets/scripture/`) rather than duplicated per app — supersedes this page's original per-app-file decision, same day. **ADR-12 (2026-08-10)**: after mtgo.com started blocking the VPS's static outbound IP, scrape+sweep scheduling moved off the VPS's systemd timers entirely, onto `.github/workflows/scripture-scrape.yml` (GitHub Actions' rotating runner IPs are unaffected) — the VPS's `scripture_scraper` role stays in the repo, dormant, as a rollback path only. Remaining: failure-notification (deliberately deferred to D2/F1, 2026-08-07 decision) — partially covered already, since a scheduled GitHub Actions workflow's failure emails the repo owner by default. Karn Tablets half still blocked on T6 | [t8-scripture-karn-playbooks/](t8-scripture-karn-playbooks/index.md) |

### Group S — Tamiyo Scroll changes (request item 2)

| # | Item | Depends on | Notes | Page |
| --- | --- | --- | --- | --- |
| S1 | Re-enable + extend global sharing (request 2.5) | — (I1 only for the new "toggle to receive" half) | ✅ **Done**, including the 2026-07-30 follow-up (share/receive coupling, account-settings popup separator). 277 backend / 71 frontend tests passing | [s1-global-sharing-reenable/](s1-global-sharing-reenable/index.md) |
| S2 | Team sharing: read-only "Team Decks" selector + flag-to-share | I5, S1, S5 | ✅ **Done (2026-08-01)**. Implementation revised mid-build from per-deck to name-based sharing (see the page's "Implementation note"). Deck-validation gate stays deferred to v3.0.0 (2026-07-27). 135 frontend tests, full backend suite green | [s2-team-sharing/](s2-team-sharing/index.md) |
| S3 | Auto-flag match result to a specific decklist version, editable after | — | ✅ **Done (2026-07-30)**. Schema change: nullable `decklist_version_id` FK on `ts_matches`, auto-stamped to the deck's latest version at creation, editable after. Moxfield staleness flag (brought into v2.0.0 scope 2026-07-30, constrained 2026-07-27 to opportunistic-only — no dedicated Moxfield call) also implemented: the full raw Moxfield response is stored per version (`moxfield_data` JSONB), and a re-import surfaces `moxfield_deck_changed_since_last_import` on the response | [s3-match-decklist-version/](s3-match-decklist-version/index.md) |
| S4 | Better decklist display (request 2.3, "UI TBD"), now including card images + sort-by-{type, mana value, color identity, mana cost} | S8 | ✅ **Done (2026-08-14)**. Structured Commander/Library view, card-type sort/grouping (fixed order, not the originally-decided two-criteria selectable sort), card images via a new Scryfall proxy, shared with `tolaria_news`. Shipped from a written spec, not a hifi mockup; face-A-Land rule not separately implemented — see §S4 page for the full as-shipped-vs-decided gap list | [s4-decklist-display-redesign/](s4-decklist-display-redesign/index.md) |
| S5 | PDF report of a training session for a specific deck | S3, S9 (S9 defines what a "training session" actually is — resolves this item's open scoping question) | ✅ **Done (2026-07-31)**. Backend-generated (Constitution §4.1: no client-side composition of computed stats), WeasyPrint (**I8 resolved 2026-07-27**, see S5 page). Session-scoped report **and** an added session-less deck-level report (last 30 days, S1 shared-data merge included) share one calculation path (`PeriodStats`) and one renderer. **Blocks S2** — team members' PDF-report access is part of S2's Done statement | [s5-pdf-training-report/](s5-pdf-training-report/index.md) |
| S6 | Admin metrics dashboard, embedded in `barrins_api`/`tamiyo_scroll` for v2.0.0 | — (role infrastructure already exists, see §1.7) | ✅ **Done**. Flat-count tiles plus the 2026-08-02 time-bucketed (day/week/month) comparison, charted via `recharts` (new dependency, §4.7/§22). v3.0.0-externalized into a standalone cross-app application accessed via Barrin's Identity/Goblin Guide (not scheduled before v3.0.0) | [s6-admin-metrics-dashboard/](s6-admin-metrics-dashboard/index.md) |
| S7 | Tutorial + demo interface, combined, pre-filled from a JSON fixture file, no persistence | — | **Decided**: option 1 (pure frontend mock, no backend). See §1.8 | [s7-demo-tutorial-interface/](s7-demo-tutorial-interface/index.md) |
| S8 | MTGJSON card/set data pipeline (models, admin-triggered import route, scheduled refresh) — added 2026-07-26, see F8 | D1 (playbook shape for the scheduled refresh) | 🟢 **Core pipeline done (2026-08-05)** — `Card`/`MTGSet` models, admin-gated `POST /mtgjson/import`, public `GET /sets/*`/`GET /cards/*` reads, all built from scratch (`auth_roles.md` described this as already existing, verified false, F8). Chunked-upsert performance fix 2026-08-07 (a 45-minute import cut to low minutes). **Unblocked T3 same day (2026-08-05)**, which has since landed (2026-08-07). Still open: the scheduled-refresh mechanism. **Still blocks S4** (not started). **No longer blocks S2** — its deck-validation gate deferred to v3.0.0 (2026-07-27) | [s8-mtgjson-ingestion-pipeline/](s8-mtgjson-ingestion-pipeline/index.md) |
| S9 | Tournament/training session grouping for Tamiyo Scroll — subgroups matches (not card-tests) under a named session, comparable against baseline history — added 2026-07-27, raised in conversation, not part of the original request | — | ✅ **Done**. Dedicated Sessions tab (manage/create/close/reopen/archive, comparison summary, relocated `ExpectedMetagameSection` for tournament-typed sessions), full stack tested. Resolves S5's "one training session" scope ambiguity | [s9-tournament-session/](s9-tournament-session/index.md) |
| S10 | Card-game field on `TSPersonalDeck`, required before logging/editing results — drafted 2026-07-27, **brought into v2.0.0 on 2026-07-28** (was deferred to v3.0.0) | — (coordinates with S3/S11 on the match-creation path; shares the new `PATCH /personal-decks/{id}` route with S11) | ✅ **Done**. `CardGame` enum (`magic`, `yu_gi_oh`, `pokemon`, `flesh_and_blood`, `one_piece`, `lorcana`), **nullable, no default/backfill** (`game par défaut = none`) — same shape as S11: explicit at creation, gate in `_validate_match_refs` blocks match create **and** edit on a NULL-game deck (`422 personal_deck_game_required`), historical decks unblocked via PATCH. 2026-08-03 follow-up: `game` cascades to opponent/meta decks | [s10-personal-deck-game-flag/](s10-personal-deck-game-flag/index.md) |
| S11 | Macrotype (archetype category) on `TSPersonalDeck`, required before logging/editing results — added 2026-07-28 | — (coordinates with S3 on the match-creation path) | ✅ **Done**. Reuses the roster's `ArchetypeCategory` enum + Postgres type (no new type) and the stats-block color identity (`ARCHETYPE_*_CLASS`). Nullable column, no backfill; the gate in `_validate_match_refs` blocks match create **and** edit on a NULL-macrotype deck (`422 personal_deck_macrotype_required`); new `PATCH /personal-decks/{id}` route (shared with S10) unblocks historical decks | [s11-personal-deck-macrotype/](s11-personal-deck-macrotype/index.md) |
| S12 | UI/UX polish bundle — four small frontend fixes brought into v2.0.0 from the feature-roadmap backlog (`docs/content/front/tamiyo_scroll/roadmap.md`, "v2.0.0 candidates" section), added 2026-07-30 | — | All four are frontend-only (`apps/tamiyo_scroll`), no schema/API change: personal-deck creation affordance gets a green `[new]` text label (no icon library needed — `apps/tamiyo_scroll` has none today); the "tested cards" matchup select is rebuilt on the same combobox pattern as the BO3 opponent select; "Final turn" label renamed; matchup-summary "Games" column (already counting `match_count`) relabelled "Matches" | [s12-uiux-polish/](s12-uiux-polish/index.md) |
| S13 | Confirmation dialog before every deletion — 4 of 7 delete actions (Match, Card test, Decklist version, Session) have none today; added 2026-08-23 from GitHub issue #79 | — | ✅ **Done (2026-08-23)**. Frontend-only, no new dependency — `components/ui/confirm-dialog.tsx` extracts a shared `ConfirmDialog` off the existing `Dialog` primitive; wired into the 4 unprotected spots and refactored onto by the 3 already-protected ones (roster deck, personal deck, team — team's two-step invite-code-retype flow preserved). 232 → 248 frontend tests | [s13-delete-confirmation/](s13-delete-confirmation/index.md) |
| S14 | Session overhaul — rename, editable start/end dates, sortable/paginated table, per-session hue, session tag in Match journal, archived-session search + restore, auto-archive by stale decklist version, plus a `location` field added during implementation — added 2026-08-23 from GitHub issue #80, all 9 items (5 core + 4 "related possible") confirmed in scope by the user | S3 (reads `decklist_version_id` for auto-archive) | ✅ Done (2026-08-24). `TSSession.ended_at` renamed `closed_at`; new `started_at`/`ended_at`/`hue`/`location`. Auto-archive is event-triggered (on decklist import), not a periodic job — no scheduler spike needed | [s14-session-overhaul/](s14-session-overhaul/index.md) |
| S15 | Decklist version history — view a past version's full content + card-level diff against the prior version, gated by a setting defaulting `true` — added 2026-08-23 from GitHub issue #81 | S4 (reuses `ResponseDecklistView`) | ✅ **Done (2026-08-24)**. Diff computed server-side via stdlib `difflib`, matched by card name (no new dependency) — see index.md's "S15 shipped" entry | [s15-decklist-version-diff/](s15-decklist-version-diff/index.md) |
| S16 | Tested Cards → deck change log: `tester`/`card_name` renamed to `removed_card_name`/`added_card_name`, plus validation (removed card must be in decklist — defaults **on**; added card must exist — opt-in) and a change-log display linking card tests to real decklist diffs — added 2026-08-23 from GitHub issue #82, full-pivot option confirmed by the user | S15 (`VersionHistorySection`'s diff rendering, extended here) | ✅ **Done (2026-08-24)**. Open question 1 resolved (kept existing rows, documented migration artifact); post-approval addition matches card tests against real decklist diffs anywhere in version history (`card_test_matching.py`, new `GET /card-tests/change-log`) — see index.md's "S16 shipped" entry | [s16-tested-card-changelog/](s16-tested-card-changelog/index.md) |
| S17 | Split `TSCardTest` into a card log (removed/added name + notes) + many match-up evaluations (opponent deck + rating + own notes, added from the edit form only); new "pending" (blue) decklist state for a removed card still present in the current decklist; on-the-fly name dropdowns (decklist cards for Removed, live DB search for Added); inline removed→added row display in the decklist itself — added 2026-08-24 from a user draft note, not a GitHub issue | S16 (splits the table S16 just pivoted; item 3 reuses `card_test_matching.py`) | 🔶 **In progress (2026-08-24)**. Backend done: schema split (`TSCardTestEvaluation`), decklist-coloring `pending` pass, `pending_added_card_*` fields, prefix name-search endpoint. Frontend: `CardTestsSection.tsx` split form + evaluations sub-list done; `DecklistCardRow` inline pending display and the name-search dropdowns still open. Deletion on both new tables corrected same-day to archive, not hard-delete, per Constitution §11.8 (S18) | [s17-card-log-matchup-evaluations/](s17-card-log-matchup-evaluations/index.md) |
| S18 | Deletion defaults to archive (soft-delete), not physical removal, project-wide — Constitution §11.8 (Amendment Proposal 8), surfaced while fixing S17's card-log delete cascading to destroy its evaluations. `TSCardTest`/`TSCardTestEvaluation` already converted as part of S17; this item covers the rest: fill the missing restore path on `TSPersonalDeck`/`TSMetaDeck` (only `TSSession` has one today), convert `TSMatch` deletion, and redesign the `TSTeam` cascade family (`TSTeamMember`/`TSTeamDeckFlag`/`TSTeamDeckThread`/`TSTeamDeckMessage`) to archive-alongside-parent instead of relying on `ondelete="CASCADE"` — added 2026-08-24 | S17 (shares the archival pattern just established there) | 🔲 **Not started — scoped 2026-08-24**. `TSPersonalDecklistVersion` deletion confirmed **out of scope**, stays the one hard-delete exception (prior Option G decision) | [s18-deletion-defaults-to-archive/](s18-deletion-defaults-to-archive/index.md) |

### Group RA — Release wrap for `v2.0.0-alpha` (Tamiyo Scroll only, §1.11)

An early, tagged, production-deployed pre-release cutting everything
done in Group S (minus S4/S8) out from under Group T, which continues
separately. Mirrors Group R's shape (R1–R5) at a smaller scope. Once
this ships, Group R below still runs, later, for the full `v2.0.0` tag.

| # | Item | Depends on | Page |
| --- | --- | --- | --- |
| RA1 | Confirm final `v2.0.0-alpha` scope, decide the version-bump convention, merge `feat/v2-tamiyo-upgrade` → `proj/v2.0.0-bump` | Every done Group S item (S1, S2, S3, S5, S6, S7, S9, S10, S11, S12) | [ra1-merge-proj-branch/](ra1-merge-proj-branch/index.md) |
| RA2 | `proj/v2.0.0-bump` → `staging` | RA1 | [ra2-merge-staging/](ra2-merge-staging/index.md) |
| RA3 | `staging` → `main` | RA2 | [ra3-promote-main/](ra3-promote-main/index.md) |
| RA4 | Tag `v2.0.0-alpha` | RA3 | [ra4-tag-release/](ra4-tag-release/index.md) |
| RA5 | Deploy from tag (production) — `barrins_api` + `tamiyo_scroll` only, **not** `barrins_scripture.yml` (§1.11) | RA4 | [ra5-deploy-production/](ra5-deploy-production/index.md) |

### Group F — Fixes flagged in docs and roadmap (request item 3)

**Carried over from `docs/content/ops/roadmap.md`'s existing "should
fix"/"pre-existing gaps" sections** (unchanged by this plan, restated
here for completeness):

| # | Item | Source | Page |
| --- | --- | --- | --- |
| F1 | HetrixTools free-tier 2-tracker cap — now more urgent: this release adds up to 2 more deployable services (Tolaria News frontend, Barrin's Scripture) on top of the existing `tamiyo_scroll` gap | `roadmap.md`, ADR-4 | [f1-hetrixtools-cap/](f1-hetrixtools-cap/index.md) |
| F2 | Release cutting is fully manual (ADR-2's flagged gap) — more repos/tags this release makes this worse | `roadmap.md`, ADR-2 | [f2-release-automation/](f2-release-automation/index.md) |
| F3 | Changelog aggregation heading-level bug in `docs/hooks/sync_changelogs.py` — every new app added (Tolaria News, Barrin's Scripture, Karn Tablets) hits this again | `roadmap.md` | [f3-changelog-heading-bug/](f3-changelog-heading-bug/index.md) |
| F4 | nginx security headers (HSTS, etc.) not implemented | `roadmap.md`, Constitution §29.1 | [f4-nginx-security-headers/](f4-nginx-security-headers/index.md) |
| F5 | Pre-commit secret-scanning is opt-in per developer, no server-side gate | `roadmap.md`, `security/secrets.md` | [f5-precommit-secret-scanning/](f5-precommit-secret-scanning/index.md) |

**Newly found while preparing this plan** (verified directly against the
repo on 2026-07-25, not previously written down anywhere):

| # | Item | Evidence | Page |
| --- | --- | --- | --- |
| F6 | `docs/content/ops/deployment/backend.md`'s "Validation" section states "no dedicated `/health` route in `barrins_api` today" — this is stale. `GET /health` is implemented (`app/api/general/health.py`, mounted in `main.py`) and `docs/content/ops/operations/index.md`'s own "Open items summary" table correctly lists it as implemented. The two docs contradict each other. | Direct code read: `apps/barrins_api/app/api/general/router.py`, `health.py` | [f6-health-doc-fix/](f6-health-doc-fix/index.md) |
| F7 | Several files reference planning documents that do not exist anywhere in the repository: `docs/decklist_integration/`, `docs/tolaria_news/00_plan_general.md`, `docs/tamiyo_scroll_tracker/00_plan_general.md`, `docs/signup_email_verification/00_plan_general.md`, and (found while scoping S6/§1.7) `docs/auth_roles/10_deploiement.md` — cited from `docs/content/back/barrins_api/bff/tamiyo_scroll.md`, `docs/content/back/barrins_api/signup_email_verification.md`, `docs/content/front/tamiyo_scroll/bootstrap.md`, `apps/barrins_api/scripts/create_admin.py`, and from code comments in `app/services/tamiyo_scroll/*.py`, `app/models/tamiyo_scroll.py`, `app/core/security.py`, `app/services/email/*.py`. Either these were real, unpublished planning docs that were never migrated into `docs/content/` during the docs restructuring, or the paths were always aspirational. Worth a deliberate decision: recreate them under `docs/content/` (if the design decisions they're cited for still need a home) or update every citing file to stop pointing at a dead path. 🟡 **`docs/decklist_integration/` resolved (redirect, 2026-08-11, via T2)** — four paths remain | Full-repo search, zero matches for any of the five paths as an existing file | [f7-broken-doc-references/](f7-broken-doc-references/index.md) |
| F8 | Same category of gap as F7, found 2026-07-26 while scoping S4: `docs/content/back/barrins_api/auth_roles.md` describes a `POST /mtgjson/import` route, an `admin`-gated MTGJSON import capability, and implies `sets`/`cards` read routes exist (`GET /sets/`, `GET /cards/{uuid}`, etc.) as part of the **already-implemented** role/security matrix. **None of it exists in code.** Zero Python files anywhere in the repository reference `mtgjson`; no `Card`/`Set` ORM model exists. This is purely aspirational documentation, not a resurrected or hidden feature — S4 and S2's deck-validation gate were both originally scoped assuming this pipeline already existed; both now depend on **S8** instead. | Full-repo search (`grep -ri mtgjson`), zero Python matches; `auth_roles.md`'s security matrix and role table are the only places this is described | [f8-mtgjson-docs-gap/](f8-mtgjson-docs-gap/index.md) |
| F9 | ✅ **Done** (PR #23) — branch protection & CI coverage gap for `proj/*` branches, decided 2026-07-26 (§3): `.github/workflows/CI.yml` only triggered on `pull_request`/`push` to `[staging, main]` — verified directly in the workflow file — so every `proj/*` PR (including this release's own `proj/v2.0.0-bump` and its sub-branches) ran **no CI at all**. No GitHub branch-protection ruleset covered `proj/*` either, so PRs into it weren't actually mandatory, only conventional. Both gaps closed: `proj/*` added to `CI.yml`'s triggers, and a new `proj-release-branch-protection` ruleset added; UAT confirmed (test PR ran CI, direct push rejected) | `.github/workflows/CI.yml` (direct read); carried-over open item from v1.0.0, now decided | [f9-proj-branch-protection/](f9-proj-branch-protection/index.md) |
| F10 | User-reported 2026-08-17: Tamiyo Scroll's Metagame tab (`GET /meta-decks`, `MetaDecksRosterSection`/`ExpectedMetagameSection`) isn't scoped to the active personal deck at all — switching decks (same game or a different one) never filters or clears the opponent roster. Traces back to S10's `TSMetaDeck.game` being a soft, unenforced ML-export tag, never wired to any UI filter, and the only roster-creation UI path never even sets it. ✅ **Done (2026-08-18)** — `TSMetaDeck.personal_deck_id` (required FK) + `TSMetaDeck.updated_at` (new), two chained migrations with an inline backfill, `metagame_roster_scope` per-user setting (default `"game"`), `_sync_opponent_deck_games` reworked to duplicate-and-allocate, `build_merged_view` gained a separate opt-in flag rather than overloading its existing `personal_deck_id` param (would have silently narrowed `stats.py`/the PDF report route). `barrins_api` 582 tests passing, 97.40% coverage. Not yet exercised against a database with real pre-F10 rows (backfill correctness) — see the page's own UAT | Direct code read: `meta_decks.py`, `MetaDecksSections.tsx`, `useMetaDecks.ts`, `models/tamiyo_scroll.py`, `sharing_merge.py`, `personal_decks.py` (`_sync_opponent_deck_games`); cross-referenced against S10's own scoping | [f10-metagame-cross-game-leak/](f10-metagame-cross-game-leak/index.md) |

### Group D — Deployment playbooks for new applications/services (request item 4)

| # | Item | Depends on | Notes | Page |
| --- | --- | --- | --- | --- |
| D1 | A documented **playbook template/checklist** generalizing Constitution §37/§26.1 for service *shapes* that don't exist yet in `ops/my-server/roles/` — today there's only `fastapi_backend` (web API) and `react_frontend` (static SPA). Barrin's Scripture is a **scheduled job**, not a long-running web service; Karn Tablets (real scope confirmed by I4, §1.4) is likely a third shape again — a periodic clustering job, possibly with a small results-serving API. | I2, I4 | ✅ **Done (2026-08-03)** — [`new-service-checklist.md`](../../content/ops/deployment/new-service-checklist.md). Found while starting this item: T1 already built a concrete scheduled-job instance (`scripture_scraper`) ahead of this template — used as a precedent instead of duplicated, see T8 | [d1-playbook-template/](d1-playbook-template/index.md) |
| D2 | Extend monitoring (HetrixTools or its successor per F1) to cover the new service(s) | F1, D1 | 🔲 Unblocked on D1 (done); still needs F1 | [d2-monitoring-extension/](d2-monitoring-extension/index.md) |
| D3 | Update `security/secrets.md` / `ops/my-server/secrets/README.md` for whatever new credential(s) I3 introduces (e.g. a Barrin's-Scripture-to-`barrins_api` service token) | I3 | ✅ **Done, 2026-08-11** — `SCRIPTURE_INGEST_TOKEN` documented in `ops/my-server/secrets/README.md` and per-app `*.env.example` files (byproduct of T8, 2026-08-08), plus the `docs/content/ops/security/secrets.md` narrative section ("Service-to-service credentials: `SCRIPTURE_INGEST_TOKEN`"). Same "never in git" pattern as ADR-1 | [d3-secrets-docs-update/](d3-secrets-docs-update/index.md) |

### Group R — Release wrap (mirrors v1.0.0's B1–B7)

| # | Item | Depends on | Page |
| --- | --- | --- | --- |
| R5 | Write the ADRs this release's decisions require (I1–I8, once resolved) — **resequenced 2026-07-26 to precede R1**, per §3.1's lesson | I1–I8 | ✅ ADR-5–ADR-11 merged via PR #24 — [r5-write-adrs/](r5-write-adrs/index.md) |
| R1 | Finalize release content, merge `proj/v2.0.0-bump` → `staging` | All of Groups T/S/F/D above that are in scope, **and R5** (ADRs merged before this point, not after — §3.1) | [r1-merge-staging/](r1-merge-staging/index.md) |
| R2 | Promote `staging` → `main` | R1 | [r2-promote-main/](r2-promote-main/index.md) |
| R3 | Tag and cut the release | R2 | [r3-tag-release/](r3-tag-release/index.md) |
| R4 | Deploy from tag (production) | R3, D1/D2 (new services need their playbooks *before* first deploy) | [r4-deploy-production/](r4-deploy-production/index.md) |

---

## 3. Branch strategy

Same convention as v1.0.0: all work aggregates on the integration branch
**`proj/v2.0.0-bump`**, branched off `staging`. Each work item above is
its own branch/PR merging into `proj/v2.0.0-bump`. Given this release's
scope (up to three new applications, versus zero in v1.0.0), consider
whether sub-integration branches per group (e.g.
`proj/v2.0.0-bump/scripture`, `proj/v2.0.0-bump/tamiyo-scroll`) are worth
the overhead — not decided here, flagged for whoever opens the first PR.

**Decided (2026-07-26)** — resolves the open item v1.0.0 carried
forward, plus two related gaps the user flagged the same day:

1. **PRs are mandatory into every `proj/*` branch** — no direct pushes,
   matching how `staging`/`main` already work (implicitly, per this
   plan's own "each work item is its own branch/PR" convention above,
   now made an explicit, enforced rule rather than just a convention).
2. **`.github/workflows/CI.yml` gets `proj/*` added to its trigger
   branches.** Verified 2026-07-26: today's config is
   `pull_request.branches: [staging, main]` / `push.branches: [staging,
   main]` — `proj/*` branches currently run **no CI at all** on their
   own PRs. This was the exact open item carried forward from v1.0.0,
   now decided rather than re-flagged.
3. **Extend `staging`'s branch-protection ruleset to `proj/*`
   branches** — the same required-review/required-status-check rules
   `staging` already has, applied to `proj/*` too, so point 1 (PRs
   mandatory) is actually enforced by GitHub, not just by convention.

Tracked as its own item — see **F9** in Group F below — since this is
real repo configuration work (workflow YAML + GitHub ruleset settings),
not just a documentation change.

---

### 3.1 Lesson from v1.0.0: documentation must land before the squash-merge

**Confirmed by the user (2026-07-26)**: v1.0.0 hit exactly this problem,
and it cost two extra reconciliation PRs. Verified against real history
(`git log`):

- `ba54ef4` — the actual squash-merge of the release PR into `main`.
- `c4949d8`, `49dae0b`, `e2959fb`, `e61d9f1`, `11ac754` — five separate
  doc-only commits made **directly on `main`, after the squash-merge**,
  confirming B4/B5/B6/B7 "done" and adding ADR-4. Because `ba54ef4` was
  a *squash* merge, `staging` never received these commits through the
  normal merge graph — they only existed on `main`.
- `6821380` — **"post-squash release-tracking follow-up (B2/B3/B4/A7)"
  (PR #21)** — a dedicated fix-up PR needed just to reconcile the
  divergence.
- `9fa40bf` — **"sync staging with main's v1.0.0 release-tracking state"
  (PR #22)** — a *second* dedicated PR, needed because #21 alone hadn't
  fully closed the gap.

Two extra PRs to reconcile documentation that should have been in one
place the whole time. **The rule going forward**:

- Anything that **can** be finalized before the squash-merge — ADRs for
  decisions already made (R5), any "done" checklist update for
  implementation work actually completed on `proj/v2.0.0-bump` — must be
  merged there (and into `staging` via R1) **before** R2 promotes to
  `main`. R5 is resequenced below to make this explicit: it now precedes
  R1, not just "whenever I1–I8 happen to resolve."
- Anything that **cannot** be finalized beforehand by its nature (R3's
  "tag pushed" confirmation, R4's "deployed" confirmation — these
  describe events that haven't happened yet at R1/R2 time) must be
  **immediately backported to `staging`** as its own small, defined step
  right after being written on `main` — not left to accumulate the way
  v1.0.0's five post-squash commits did before anyone noticed the
  divergence.

---

## 4. How each work item's page is structured

Same convention as `docs/project/v1.0.0-bump/`. Every page
under a work item follows the same shape:

1. **Done statement** — concrete acceptance criteria.
2. **Tasks** — the implementation breakdown.
3. **UAT** — manual steps to be performed personally by the user to
   confirm the change is applied correctly.
4. **Non-regression tests** — systematic tests added for this item.

**One difference from v1.0.0's pages, stated plainly**: v1.0.0's pages
were written after (or during) the work, describing what was actually
done. Most of this release's pages are written **before** the work,
some for items still blocked on an open decision from §1. Those pages
say so explicitly in their **Status** row (🔲 rather than ✅) and their
Done statement is conditioned on the blocking decision rather than
describing a finished result — nothing on a blocked item's page should
be read as already implemented.

---

## 5. What this document deliberately does not do

- It did not originally pick a winner for any item in §1 — those were
  the user's calls, framed in the ADR shape this project already uses
  for exactly this kind of decision. All of §1 has since been decided
  (2026-07-25 for §1.1–§1.3/§1.5–§1.7, 2026-07-26 for §1.4, 2026-07-27
  for §1.9) and is recorded inline.
- It does not invent a UI for item S4 ("better decklist display") —
  no design exists yet to describe.
- It does not assume `barrins-project/tolaria_news` (the third connected
  repo) contains anything, since it could not be read (404).
- It does not commit to a specific ML library/framework or a hosting
  choice for Karn Tablets — §1.4 confirms *what* it computes (metagame
  clustering + deck-type aggregation) but any new dependency still goes
  through §4.7/§22's approval process before it's chosen.
- It does not scope, design, or schedule the standalone metrics
  application, Barrin's Identity, or Goblin Guide themselves — all three
  are confirmed v3.0.0 work. This document only records the two
  forward-compatibility constraints (§1.7) that v2.0.0's embedded
  version needs to honor so that later externalization doesn't force a
  rewrite.

## See also

- [`../../content/ops/roadmap.md`](../../content/ops/roadmap.md) — the
  ecosystem-wide roadmap, updated alongside this plan.
- [`../../content/ops/architecture/decisions.md`](../../content/ops/architecture/decisions.md)
  — ADR-1 through ADR-4; ADRs for §1's resolved decisions should follow
  as ADR-5 onward.
- [`../v1.0.0-bump/index.md`](../v1.0.0-bump/index.md)
  — the v1.0.0 plan this document's structure is modeled on.
- [`consitution-amendment.md`](consitution-amendment.md) — proposed
  Constitution changes surfaced while resolving §1's decisions (privacy/
  analytics policy, account tiers, the team/group concept, the heavy-data
  repo pattern, maintenance-mode write containment, and inbound
  rate-limiting). **All six proposals reviewed and accepted**
  (2026-07-26/27). None yet applied to `docs/content/CLAUDE.md` — that's
  R5/ADR work.
