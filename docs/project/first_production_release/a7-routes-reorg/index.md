# A7. API routes reorganization

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` | / |
| **Initial date** | 2026-07-24 | / |
| **Status** | ✅ Implemented | one UAT item (visual skim on GitHub) not yet performed |
| **Source** | Naming inconsistency found while starting A3 | `ts_router.py` next to `bff/ts_router/`, same pattern for `v1_router.py`/`v1/` |
| **Dependency** | A1 | branched from `proj/v1.0.0-bump` after merging A1 — needed A1's `health.py` to move it |

---

## Context

Emerged while starting A3 (Moxfield import): `app/api/ts_router.py` (a
file) sat next to `app/api/bff/ts_router/` (a directory) — two different
things sharing the same name at different nesting levels, same pattern
for `app/api/v1_router.py` next to `app/api/v1/`. Confusing to navigate
and easy to mix up when adding a new route. The API layer also used the
abbreviation `ts` while models/schemas/services already used
`tamiyo_scroll` consistently — a real naming inconsistency, not just a
stylistic nit.

## Design

Each domain gets exactly one package containing everything about it,
including its own router aggregator (named `router.py`, ending the
file/directory name collision):

```text
app/api/
├── general/            # was: root '/' in main.py + api/health.py + api/v1/ (auth)
│   ├── router.py       # aggregates health + root redirect + /api/v1/auth
│   ├── health.py
│   └── auth.py         # merged in from the old api/v1/ package (v1 had only auth)
└── tamiyo_scroll/      # was: api/ts_router.py + api/bff/ts_router/*
    ├── router.py
    ├── personal_decks.py
    ├── settings.py
    ├── matches.py
    ├── meta_decks.py
    ├── card_tests.py
    └── stats.py
```

`v1/` was folded into `general/` rather than kept as its own package —
it only ever held `auth.py`, so a dedicated package was premature
structure; the `/api/v1/auth` URL prefix is preserved exactly
(`router.include_router(auth.router, prefix="/api/v1/auth", ...)`).

None of the individual route files (`personal_decks.py`, `auth.py`,
etc.) imported from their sibling router files — they only import from
`app.database`, `app.dependencies`, `app.models`, `app.schemas`,
`app.services` (all unchanged) — so this was a pure structural move, zero
business-logic risk. Only the aggregator files
(`ts_router.py`/`v1_router.py` → `tamiyo_scroll/router.py` /
merged into `general/router.py`) and `main.py`'s imports changed.

**Sequencing note**: this branch is based on `proj/v1.0.0-bump` *after*
merging A1 (`a1-monitoring-health`) into it directly (not via a separate
GitHub PR step) — A1 added `app/api/health.py`, which this reorg needed
to move into `general/`. Confirmed via
`git merge-base --is-ancestor origin/a1-monitoring-health origin/proj/v1.0.0-bump`
before starting.

## Tasks

- [x] Move `api/bff/ts_router/*.py` → `api/tamiyo_scroll/*.py` (`git mv`,
      no import changes needed inside each file).
- [x] Move `api/ts_router.py` → `api/tamiyo_scroll/router.py`, update its
      internal import.
- [x] Remove the now-empty `api/bff/` directory.
- [x] Create `api/general/` (`__init__.py`, `router.py`); move
      `api/health.py` → `general/health.py` and `api/v1/auth.py` →
      `general/auth.py`; remove the `api/v1/` package.
- [x] Update `app/main.py`'s imports and `include_router` calls; move the
      root `/` redirect out of `main.py` into `general/router.py`.
- [x] Full backend suite green: 225/225 tests, 98.15% coverage,
      `ruff check`/`ruff format --check`/`ty check` all clean.

## Done statement

New package layout in place; every route resolves to the exact same URL
it did before (`/`, `/health`, `/api/v1/auth/*`,
`/bff/tamiyo-scroll/*`); full test suite green with no code changes
needed inside any individual route file.

## UAT (manual)

- [X] On `staging`, confirm `GET /`, `GET /health`, `POST /api/v1/auth/token`,
      and a `/bff/tamiyo-scroll/*` route all resolve exactly as before —
      no URL should have changed.
- [X] Skim `app/api/` in the GitHub UI and confirm the new layout reads
      clearly (the actual goal of this item).

## Non-regression tests

- Automated: full existing suite (225 tests) passes unchanged — this
  item deliberately touches no test files, since route *behavior* is
  identical, only file locations changed.
- No new tests added (nothing new to cover; a pure structural move).
