# Issue scoping — post-v2.0.0 Tamiyo Scroll feature requests

Internal project tracking, not part of the public docs site
(`docs.barrins-codex.org`): like `docs/project/v1.0.0-bump/` and
`docs/project/v2.0.0-bump/`, this directory lives outside
`docs/content/` (mkdocs' `docs_dir`), so it isn't built or published —
only version-controlled and reviewed via PR.

## What this folder is

Five GitHub issues were open on the repo at triage time (2026-09-08),
all Tamiyo Scroll. One was a plain bug and is fixed. The other four are
feature requests that the
[Tamiyo Scroll feature roadmap](../../content/front/tamiyo_scroll/roadmap.md)
already buckets at **v3 / v3+**, and that Constitution §16.2 / §52
require a written *Context / Alternatives / Trade-offs / Decision /
Consequences* pass on **before** any implementation starts —
"never guess requirements … changing API behavior; changing user
workflow" both apply.

Each page here is that pass. It stops at **"Decision needed"** — it does
**not** pre-commit an approach, add anything to a release plan, or
authorise implementation. Promoting one of these into an actual release
still needs the escalate-don't-guess step, same as every `S*` / `T*`
item in `v2.0.0-bump/`.

## The five issues

| Issue | Title | Status | Page |
| --- | --- | --- | --- |
| [#126](https://github.com/Spigushe/barrins-project/issues/126) | I can't change session type? | ✅ **Fixed** — branch `proj/session-type-edit` | below |
| [#141](https://github.com/Spigushe/barrins-project/issues/141) | Feature Request: Archive card log | 🟡 Approach decided (2026-09-08), 3 minor questions | [141-archive-card-log.md](141-archive-card-log.md) |
| [#124](https://github.com/Spigushe/barrins-project/issues/124) | Feature Request: Counter to track both side's misplays | 🔲 Scoped, decision needed | [123-124-structured-match-log.md](123-124-structured-match-log.md) |
| [#123](https://github.com/Spigushe/barrins-project/issues/123) | Feature Request: Add a counter for mulligans per game on both side | 🔲 Scoped, decision needed | [123-124-structured-match-log.md](123-124-structured-match-log.md) |
| [#104](https://github.com/Spigushe/barrins-project/issues/104) | Feature Request: Commander swap tracking | 🔲 Scoped, decision needed | [104-commander-swap-tracking.md](104-commander-swap-tracking.md) |

Issues #123 and #124 share one page: both say "Refactor match log form"
verbatim and both add structured per-game, per-side counters to the same
`ts_matches` record and the same `MatchFormFields` form. Splitting them
would produce two migrations and two form reworks touching the same
lines.

## #126 — I can't change session type? (fixed)

**Root cause (verified 2026-09-08):**
[`SessionPatch`](../../../apps/barrins_api/app/schemas/tamiyo_scroll.py)
never carried a `type` field, and
[`update_session`](../../../apps/barrins_api/app/api/tamiyo_scroll/sessions.py)
never assigned `ts_session.type`. On the frontend the Type selector
existed only in the "New session" form —
[`SessionEditFields`](../../../apps/tamiyo_scroll/src/pages/sessions/SessionsSections.tsx)
had no Type control and `draftToPatch` never sent one. So a session
mislabeled `tournament`/`training` at creation had no correction path.

**Fix (branch `proj/session-type-edit`, not yet merged):**

- `SessionPatch` gains `type: SessionType | None = None`; `update_session`
  applies it when present (no "clear" state — a session always has a
  type). Invalid value → 422.
- `sessionPatchSchema` (frontend) gains `type: sessionTypeSchema.optional()`.
- `SessionEditFields` gains a Type `<Select>`; `SessionDraft` /
  `draftFromSession` / `draftToPatch` thread `type` through. The create
  form keeps its own dedicated `newType` state, so `draftToFields` stays
  shared between create and patch without it.
- Tests: `test_changes_session_type` + `test_invalid_session_type_is_rejected`
  (backend), one `SessionsSections.test.tsx` case (frontend). Full
  suites green — backend 65 sessions/report/matches tests, frontend
  32 files / 291 tests.
- Both CHANGELOGs updated under `### Fixed`.

**Downstream checked, no impact:** the only readers of `session.type`
are the tournament-only Expected-Metagame block in
`SessionSummarySection`, the PDF report subtitle, and the
`SessionTypeBadge` — all just re-render on the new value. Stats
(`compute_period_stats`) don't branch on type.

## Convention for these pages

- Named by issue number(s), not an `S`/`T` number — they are not part of
  the committed release plan and shouldn't look like they are.
- Every claim about current behaviour is verified against the code with
  a `path:line` reference, per the `v2.0.0-bump/` house style.
- **Alternatives** carry explicit trade-offs; **Decision** is left open
  with a recommendation, never silently chosen (§16.2, §5).
- When an approach is picked, the page moves to `v2.0.0-bump/`-style
  status tracking (or a future `v3.0.0-bump/`), and the roadmap row is
  updated to link here.
