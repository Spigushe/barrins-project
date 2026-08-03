# F6. Fix stale `/health` claim in `deployment/backend.md`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `docs/content/ops/deployment/backend.md` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — trivial, found during v2.0.0 planning | / |
| **Source** | `v2.0.0-bump/index.md` §0, F6 | / |
| **Dependency** | None | / |

---

## Context

`deployment/backend.md`'s "Validation" section states "no dedicated
`/health` route in `barrins_api` today." This is false: `GET /health` is
implemented (`app/api/general/health.py`, mounted via
`app/api/general/router.py`, confirmed by reading the code directly),
and `operations/index.md`'s own "Open items summary" table already lists
it correctly as implemented. The two docs contradict each other.

## Done statement

- `deployment/backend.md`'s "Validation" section updated to reference
  `curl -I https://api.barrins-codex.org/health` (or equivalent)
  instead of claiming the route doesn't exist.

## Tasks

- [ ] Update the "Validation" bullet in `deployment/backend.md`.
- [ ] Grep the rest of the docs tree for any other stale reference to
      "no `/health` route" before considering this done.

## UAT (manual)

- [ ] `curl -I https://api-staging.barrins-codex.org/health` returns
      `200`, matching the corrected doc text.

## Non-regression tests

- N/A (documentation-only fix).
