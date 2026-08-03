# F7. Broken references to nonexistent planning docs

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | Multiple files — see list below | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — found during v2.0.0 planning | / |
| **Source** | `v2.0.0-bump/index.md` §0, F7 | / |
| **Dependency** | None | / |

---

## Context

Five distinct paths are cited from code comments and docs, but do not
exist anywhere in the repository (verified by full-repo search):
`docs/decklist_integration/`, `docs/tolaria_news/00_plan_general.md`,
`docs/tamiyo_scroll_tracker/00_plan_general.md`,
`docs/signup_email_verification/00_plan_general.md`, and
`docs/auth_roles/10_deploiement.md`. Citing files:
`docs/content/back/barrins_api/bff/tamiyo_scroll.md`,
`docs/content/back/barrins_api/signup_email_verification.md`,
`docs/content/front/tamiyo_scroll/bootstrap.md`,
`apps/barrins_api/scripts/create_admin.py`, and comments inside
`app/services/tamiyo_scroll/*.py`, `app/models/tamiyo_scroll.py`,
`app/core/security.py`, `app/services/email/*.py`.

## Done statement

One of two outcomes, decided deliberately rather than left ambiguous:

- **Recreate**: if the design decisions these paths are cited for still
  need a durable home, write them under `docs/content/` (or wherever the
  project's current convention places planning docs) and repoint every
  citing reference at the new location.
- **Redirect**: if the content was never real / is superseded by what
  now lives in `docs/content/back/barrins_api/bff/tamiyo_scroll.md` and
  similar, update every citing file/comment to stop pointing at a dead
  path (either removing the reference or pointing at the doc that
  actually contains the relevant decision today).

## Tasks

- [ ] Decide recreate vs. redirect (likely per-path, not all-or-nothing
      — e.g. `bff/tamiyo_scroll.md` may already contain everything
      `docs/tamiyo_scroll_tracker/00_plan_general.md` was meant to hold).
- [ ] Update each citing file/comment accordingly.
- [ ] Re-run the full-repo search from this planning process
      (`grep -rn` for each of the five paths) to confirm zero remaining
      dangling references.

## UAT (manual)

- [ ] The same search that found the five broken references, re-run
      after this fix, returns either real files at each path or zero
      citations left pointing at it.

## Non-regression tests

- N/A (documentation/comment-only fix, unless a decision doc is
  recreated with real content worth its own review).
