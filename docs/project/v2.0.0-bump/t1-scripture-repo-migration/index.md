# T1. Barrin's Scripture — repo location & migration

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | New: `apps/barrins_scripture` (monorepo, rewrite per §1.1 Option 3) | / |
| **Initial date** | / | Not started |
| **Status** | 🟡 In progress — schemas/parsers/utils/services/CLI, CI job (`.github/workflows/CI.yml`), and the `ops/my-server/barrins_scripture.yml` + `roles/scripture_scraper/` deploy playbook all written and test-driven (130 tests, 95%+ coverage — see Tasks below, corrected 2026-08-02: CI/ops were previously listed as open here but are done, per PR #41); **2026-08-07**: `mtg_scraper`/old `mtg_decklist_cache` both transferred + archived to `barrins-archive`, and `Spigushe/mtg_decklist_cache` created fresh (not a history transfer — see Context). Still open: wiring the actual git submodule into `scripture_scraper`, and backfilling the new archive (MTGTop8 `--id-from` now supports this; MTGO's `--date-from`/`--date-to` already did) | / |
| **Source** | Request item 1; `v2.0.0-bump/index.md` §1.1 | / |
| **Dependency** | None (this is the first domino) | Blocks T2, T3 |

---

## Context

`mtg_scraper` (`barrins-project/mtg_scraper`, public) is a real, working
Python 3.13 scraper, its own repo with its own CI, versioning
(`CHANGELOG.md` at `0.2.0`), and a `scraped/` git submodule
(`mtg_decklist_cache`). §1.1 decided (2026-07-25) that
`apps/barrins_scripture` is a **new** implementation superseding
`mtg_scraper` (Option 3), archiving `mtg_scraper` once feature parity is
reached.

**Related, clarified by the user (2026-07-26): not a deadline, a given.**
The `barrins-project` GitHub org hosting both `mtg_scraper` and
`mtg_decklist_cache` will eventually be deleted — but only by the user's
own deliberate action, once this release has shipped and the org is no
longer needed. There's no race and no data-loss risk to mitigate: the
user won't delete it until the transfer below is done and confirmed.
**What this does mean for this item**: don't conclude
`mtg_decklist_cache` (or `mtg_scraper`) stays at its current
`barrins-project` name/location — both get transferred (full history
preserved, e.g. `git clone --mirror` + push) to a durable location (a
different org, or under the `Spigushe` account — **not yet specified**)
as a normal part of this item's own migration work, whenever there's
confidence to do so.

**Decided (2026-07-29), while implementing this item:**

- **Scheduling**: the recurring scrape runs on the VPS via a new
  `ops/my-server/barrins_scripture.yml` playbook (a `systemd` `.service` +
  `.timer` pair, the same pattern `ops/my-server/roles/postgres_backup/`
  already uses) — not GitHub-Actions-native cron like `mtg_scraper` uses
  today. Not built yet; the rewrite itself (below) came first.
- **Transfer timing and destinations**: `mtg_scraper` stays in the
  `barrins-project` org until v2.0.0 ships, then moves to the
  **`barrins-archive`** organization. `mtg_decklist_cache` moves to
  **`Spigushe/mtg_decklist_cache`**, timed right before the v2.0.0
  release is cut (not a vague "sometime post-release" step). Until that
  cut, `apps/barrins_scripture` doesn't assume a submodule at all — see
  the next point.
- **Superseded (2026-08-07): fresh repo, not a history-preserving
  transfer.** The plan above assumed moving the *existing*
  `mtg_decklist_cache` (full history via `git clone --mirror`). Decided
  instead: `Spigushe/mtg_decklist_cache` is a **new, empty** repository —
  the old archive's data isn't guaranteed to match the new
  implementation's schema (confirmed while investigating: `Deck.result`
  changed `int | None` → `str | None` to stop truncating MTGTop8 tie
  brackets like `"5-8"` to `5`, so old untied-result files are
  differently-typed and old tied-result files have already lost the
  bracket data — see fixtures under `apps/barrins_scripture/tests/
  fixtures/`). The old `mtg_scraper`/`mtg_decklist_cache` pair still
  follows its own retirement path (archived once parity is confirmed,
  per the Done statement below) — this only changes what
  `Spigushe/mtg_decklist_cache` itself contains. **Repo created
  2026-08-07**, public, README-only:
  <https://github.com/Spigushe/mtg_decklist_cache>.
  `scripture_scraper` owns it operationally per T8's 2026-08-07 decision
  (clone via the shared `github_token`, commits pushed by T3's sweep).
- **`--output-dir` instead of assuming a submodule immediately**: rather
  than wiring a git submodule into `apps/barrins_scripture/scraped/` now
  (pointing at a location that's still going to move per the point
  above), the CLI takes an `--output-dir` flag (`scrape_mtgo`/
  `scrape_mtgtop8` gain a matching `output_dir` param) that overrides
  the default archive path. `apps/barrins_scripture/scraped/` is
  git-ignored and only ever a plain local directory until the actual
  submodule gets wired up — a deployment can point `--output-dir`
  wherever it manages the real clone in the meantime.

## Done statement

- Barrin's Scripture's new code lives at `apps/barrins_scripture` in
  this monorepo.
- `mtg_scraper` and the old `mtg_decklist_cache` are both transferred,
  full history intact, to a durable location outside `barrins-project`.
  **Done (2026-08-07)** — both now live archived under `barrins-archive`.
- CI adapted to this monorepo's `.github/workflows/CI.yml`
  `changes`/path-filter pattern (a new `scripture` filter + job,
  mirroring `back`/`front`).
- `mtg_scraper` is archived (pointing at its new, non-`barrins-project`
  location). **Done (2026-08-07)** — ahead of the original "once parity
  is confirmed" gate: per the 2026-08-07 decision above, the old
  archive's data doesn't carry forward as-is (schema change), so
  retiring `mtg_scraper` isn't blocked on the new implementation
  matching its exact output first.
- ~~No gap in scrape coverage throughout — the old scraper keeps running
  on its existing schedule until the new one is proven equivalent.~~
  **Superseded (2026-08-07)**: moot, since a from-scratch backfill of
  `Spigushe/mtg_decklist_cache` is the plan regardless of the old
  schedule's continuity — see the id-range/date-range backfill task
  above.

## Tasks

- [x] Confirm the new durable location for `mtg_scraper`/
      `mtg_decklist_cache` with the user. **Confirmed (2026-07-29)**:
      `mtg_decklist_cache` → `Spigushe/mtg_decklist_cache`; `mtg_scraper`
      → `barrins-archive/mtg_scraper`. Doesn't unblock the transfer
      itself yet — that's still timed per the decisions above (right
      before the v2.0.0 cut for the archive, once v2.0.0 ships for
      `mtg_scraper`).
- [x] `Spigushe/mtg_decklist_cache` created (2026-08-07) — **not** a
      history-preserving transfer, see the 2026-08-07 decision above: a
      fresh, empty, public repo, README-only so far. Backfilling it (MTGO
      via `--date-from`/`--date-to`, already supported; MTGTop8 via the
      new `--id-from`/`--span` id-range option) is a separate, not-yet-run
      task.
- [x] Both `mtg_scraper` and the old `mtg_decklist_cache` transferred
      (2026-08-07, user action) via GitHub's repo-transfer feature (full
      history intact by construction) to `barrins-archive/mtg_scraper`
      and `barrins-archive/mtg_decklist_cache`, and archived there
      (verified via `gh repo view`, `isArchived: true` on both) — ahead
      of the "once v2.0.0 ships" timing this item originally planned, and
      resolving the old `mtg_decklist_cache`'s previously-undecided fate
      the same way. No scrape-coverage-gap mitigation needed for this:
      per the 2026-08-07 decision above, the old archive's data doesn't
      carry forward as-is regardless (schema change), so `mtg_scraper`'s
      retirement isn't gated on the new implementation reaching parity
      first — a full backfill of `Spigushe/mtg_decklist_cache` from
      scratch is the planned path either way (see the `--id-from`/
      `--date-from` backfill task above), not a continuation of the old
      schedule.
- [x] Write `apps/barrins_scripture` from scratch (rewrite, per §1.1
      Option 3 — not a `git subtree`/history-preserving merge): MTGO +
      MTGTop8 scraping. `schemas`, `parsers`, `utils`, `services`, and
      the CLI (`uv run scrape --source {mtgo,mtgtop8}`) are all written
      and verified against real archived tournaments. Still open: the
      daily/biweekly-gap-check *scheduling* itself (see the ops-playbook
      task below — the rewrite runs correctly on demand, but nothing
      triggers it on a schedule yet).
- [x] Add a `scripture` path filter + CI job to `.github/workflows/CI.yml`
      (mirrors the existing `back`/`front` jobs' shape — no Postgres
      service, per §1.2's no-direct-DB-access decision). A local CI
      runner (`apps/barrins_scripture/scripts/workflow_ci.py`, mirroring
      `barrins_api`'s) backs the job, same as `back` does.
- [x] Add `ops/my-server/barrins_scripture.yml` + a new
      `ops/my-server/roles/scripture_scraper/` role (`systemd`
      `.service`/`.timer` pair, patterned on `roles/postgres_backup/`) so
      the scrape actually runs on a schedule, per the scheduling decision
      above. `ansible-lint` (run via WSL, since it doesn't run natively
      on Windows) passes clean on both the role and the playbook — no
      failures, no warnings. **Still not deployed to the real VPS** —
      lint-clean confirms syntax/structure, not that a live run actually
      schedules and executes a scrape end-to-end; that's still open.
- [ ] Point the new implementation at `mtg_decklist_cache`'s new,
      durable location as the dump sub-repo per §1.3 (wire up the actual
      git submodule at `apps/barrins_scripture/scraped/` — until then,
      `--output-dir` is the interim way to point a real run at wherever
      the archive is actually managed). **Decided (2026-08-07)**:
      `scripture_scraper` owns this submodule operationally — the role
      clones it (reusing the shared `github_token`, same auth pattern
      every other app-deploying role here already uses) and T3's sweep
      (see T3's 2026-08-07 decision) commits + pushes newly-written JSON
      files as part of its own periodic tick. A failed push is treated
      like a failed sweep tick — retried next tick, no special-casing —
      rather than left as a manually-synced, unbacked-up directory. Repo
      location itself is unchanged: `Spigushe/mtg_decklist_cache`, per
      the destination already confirmed above.
- [ ] Once feature parity is confirmed, archive `mtg_scraper` (at its
      new, non-`barrins-project` location), redirecting its README to
      `apps/barrins_scripture`, so contributors don't keep opening PRs
      against a retired repo.

## UAT (manual)

- [ ] Both repos exist at their new location with full history intact.
- [ ] A scheduled scrape run (daily or manual dispatch) completes
      successfully from `apps/barrins_scripture`, writing to the same
      (relocated) `mtg_decklist_cache` archive.

## Non-regression tests

- Existing `mtg_scraper` test/lint tooling (whatever exists today —
  `pyproject.toml`'s configured checks) is re-established for
  `apps/barrins_scripture`'s rewrite before this is considered done.
  **Done, and gone beyond**: `mtg_scraper` itself had no tests and no
  enforced lint/type-check in CI (only `pip-audit`, inside the scheduled
  workflows). This rewrite is test-driven throughout — 118 tests, 95%+
  coverage, `ruff`/`bandit`/`ty` all clean, matching `apps/barrins_api`'s
  tooling conventions rather than `mtg_scraper`'s older ones. Parsers are
  verified against real archived Duel Commander tournaments (one MTGO,
  one MTGTop8) pulled from `mtg_decklist_cache` — see
  `apps/barrins_scripture/tests/fixtures/README.md`. Five real bugs
  inherited from `mtg_scraper` were found and fixed along the way (see
  `apps/barrins_scripture/CHANGELOG.md`'s Fixed section for the list).
