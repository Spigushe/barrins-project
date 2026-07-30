# S1. Re-enable and extend global results sharing

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/tamiyo_scroll`, `apps/barrins_api` | / |
| **Initial date** | 2026-07-30 | Completed 2026-07-30 |
| **Status** | ✅ Done — account-settings popup (`z_handoff_params_popup`) implemented; single global toggles, not per-sharer | / |
| **Source** | Request item 2.5 | / |
| **Dependency** | None for the "share" half; I1 only for the new "receive" half | / |

---

## Context

Read-only cross-user sharing already exists and is fully tested:
backend enforcement (`ownership.resolve_owner`,
`ts_user_settings.data_shared`, 127 tests) has been live since v1.0.0.
The frontend half (`components/layout/SharingControls.tsx`) was built,
tested, then deliberately extracted and gated off
(`const SHARING_ENABLED = false`) before the v1.0.0 launch — see
`docs/project/v1.0.0-bump/a2-sharing-extraction/index.md`
for the original reasoning (UI maturity, not backend readiness). The
request adds one genuinely new piece: a "toggle to receive" — today, any
user can view any sharer's data via the "View: {user}" selector with no
opt-in on the *viewing* side; the request wants that to become explicit.

## Done statement

- `SHARING_ENABLED` flipped to `true` (or the constant removed entirely
  if no longer needed) — the existing "Share my data" checkbox and
  "View: {user}" selector are visible again, unmodified from their
  tested v1.0.0 state.
- A new opt-in exists on the *receiving* side: a user only appears able
  to view another's shared data if they've also opted in to receiving
  (exact UX — a checkbox, a per-sharer follow action — not yet decided,
  flagged below).
- No change to `ownership.resolve_owner`'s existing write-side
  enforcement (still: writes only ever target `current_user`, regardless
  of `owner_id`).

## Tasks

- [x] Flip `SHARING_ENABLED` (removed the gate entirely — dead flag with
      no remaining callers).
- [x] Design the "toggle to receive" concept: **decided (2026-07-30) —
      per-sharer opt-in** (new `ts_receive_opt_ins` table), escalated per
      Constitution §16.2. **Superseded same day** by the
      `z_handoff_params_popup` handoff: single global
      `receive_shared_data` toggle on `ts_user_settings`, matching
      `data_shared`'s existing shape. `ts_receive_opt_ins` was dropped via
      a follow-up migration (never reached `staging`, only a feature
      branch) — see `a9f27e6c1b34_replace_receive_opt_ins_with_toggle.py`.
- [x] `GET /shared-users` requires both `data_shared = True` on the
      sharer and `receive_shared_data = True` on the viewer.
- [x] New `PATCH /api/v1/auth/me` route (`app/api/general/auth.py`) for
      self-service `display_name` updates — needed by the popup's "Nom
      affiché" field, didn't exist before (shared-identity field per
      Constitution §13.1, not Tamiyo-Scroll-scoped).
- [x] Built the account-settings popup (`AccountSettingsDialog.tsx`) per
      the handoff: display name field, "Share my data"/"Receive shared
      data" switches (custom `components/ui/switch.tsx` — no new
      dependency added), Cancel/Save footer. Replaces the header's old
      inline checkbox.
- [x] **"View: {user}" selector — built, then retired the same day.**
      Per the handoff, first extracted out of the popup into its own
      `ViewingSelector.tsx` component in `AppShell`'s header.
      **Bug found during 2-account manual UAT (2026-07-30)**: it was
      removed from `AppShell` mid-session as apparently redundant, and
      the now-unused `useSharedUsers`/`listSharedUsers`/`sharedUserSchema`
      chain was swept as dead code in the same pass — silently breaking
      "receive" end-to-end (`useViewingOwner`/`applyOwnerParam`/
      `GET /shared-users` were still correctly wired through every read
      hook, but with no UI calling `setViewingOwner`, a receiving user had
      no way to actually view a sharer's data). First fixed by restoring
      the selector — then **superseded for good** by the automatic-merge
      overhaul below, which makes an explicit "view as" selector
      unnecessary. `ViewingSelector.tsx`, `useSharedUsers`,
      `listSharedUsers`, `sharedUserSchema`, and the backend
      `GET /shared-users` route are all **deleted**, not just unused.
- [x] **Overhauled (2026-07-30) from "view as" to automatic read-only
      merge.** Per the user's real-world 2-account test (a personal deck
      named "King T'Challa" existing under two different accounts): a
      sharer's data no longer requires switching into a separate "view
      as" mode. Instead, once both toggles are on, a sharer's personal
      deck merges automatically — matched by **exact deck name**
      (trimmed, case-insensitive; no team/per-sharer linkage exists yet,
      see S2) — directly into the viewer's own Journal (matches,
      read-only) and Metagame (roster + archetype/matchup stats). Roster
      reconciliation: a name match uses the **viewer's own** tier/
      category (their ranking wins); no match adds the sharer's roster
      entry as a new read-only line. New backend module
      `app/services/tamiyo_scroll/sharing_merge.py`; `ResponseMatch`/
      `ResponseMetaDeck`/`ResponseDeckWinrate`/`ResponseMatchupRow` all
      gained `is_readonly`/`shared_by`. Frontend: read-only matches hide
      **both** Edit and Delete (View-only), and show a "from: {sharer}"
      badge both on the collapsed row and in the View popup; read-only
      roster rows are non-editable with the same badge. The popup also
      gained an explanatory line: sharing is matched by deck name.
- [x] **Team section intentionally omitted** from the popup — the handoff
      fully specifies team creation/join/leave/delete inline in this
      popup, but that duplicates/conflicts with the separate, not-yet-
      started `s2-team-sharing/index.md` spec. Team buttons stay hidden
      until S2 implementation starts; see the conflict list recorded
      there.
- [x] **Privacy fix (2026-07-30): `shared_by` never exposes an email.**
      The merge originally fell back to the sharer's email when
      `display_name` was unset — a real GDPR/privacy breach (any
      receiving account could read a sharer's email off a match/roster
      badge). Fixed in `sharing_merge.py`: falls back to the generic
      label `"a kind user"` instead. Covered by new assertions in
      `test_matches.py`/`test_meta_decks.py` (`shared_by` is never the
      raw email; using `display_name` when set still works).
- [x] **Bug fix (2026-07-30): archiving a name-matched roster entry
      silently dropped the foreign opponent.** `sharing_merge.py` matched
      a foreign opponent deck against the viewer's own roster **including
      archived entries** — so archiving the viewer's own same-named deck
      left the merged match still pointing at that (now-hidden) archived
      id instead of falling back to a fresh read-only line, showing "?"
      as the opponent name in the Journal and no read-only line in the
      roster. Fixed: only **non-archived** owner roster entries count as
      a name match; an archived match falls back to the sharer's own
      entry as a new read-only line, same as "no match at all." Covered
      by `test_own_ranking_wins_when_names_match`'s new sibling
      `test_archiving_own_matched_deck_falls_back_to_a_read_only_line`.
- [x] **Decided (2026-07-30): new accounts default to sharing.**
      `ts_user_settings.data_shared` now defaults `True` (opt-out) for
      newly-created settings rows; `receive_shared_data` still defaults
      `False` (opt-in) — asymmetric on purpose. Existing rows are
      untouched (migration only changes the column default for future
      inserts, never retroactively opts an existing user in). Caveat: the
      default only takes effect once a `ts_user_settings` row actually
      exists for that account — rows are still created on demand
      (`_get_or_create_settings`, first touched by `GET /me/settings`,
      which `AppShell` calls on every load), not eagerly at signup
      (`general/auth.py` and the Tamiyo Scroll domain remain decoupled).
      For all practical purposes this means "on first app load," not
      literally "at signup" — flagged in case that distinction matters
      later.

## UAT (manual)

- [x] On staging (2 real accounts, 2026-07-30): user A (martin.cuchet)
      shares only, user B (spigushe) shares **and** receives, both with a
      personal deck named "King T'Challa" — confirmed B's own
      journal/metagame stayed empty before the fixes above (neither the
      selector-removal bug nor the automatic-merge overhaul had landed
      yet), and after both fixes B's Journal/Metagame show A's matches
      and roster merged in, read-only, under B's own "King T'Challa".
- ~~Confirm the "View: {user}" selector shows/restores correctly~~ — no
  longer applicable; the selector is deprecated and deleted, superseded
  by the automatic merge above.
- [x] Confirm every write-side backend test from
      `tests/tamiyo_scroll/test_ownership.py` still passes unmodified —
      validated by running the suite directly (2026-07-30): 6/6 passed.
- [x] Confirm the account-settings popup saves display name + both
      toggles together, and Cancel discards in-progress edits.

## Non-regression tests

- Backend: `test_ownership.py` (6 tests), `test_settings.py`
  (global-toggle semantics, default-sharing), `test_auth.py::TestUpdateMe`,
  plus merge-behavior coverage in `test_matches.py` (`TestSharedDataMerge`,
  including the privacy/email-leak assertions), `test_meta_decks.py`
  (`TestSharedRosterMerge`, including the archived-deck regression), and
  `test_stats_routes.py` (`TestSharedDataInStats`) — 277 backend tests,
  98.05% coverage, all passing.
- Frontend: `AccountSettingsDialog.test.tsx` (pre-fill, save, cancel,
  team section absent, deck-name-matching explanation),
  `MatchJournalSection.test.tsx` (read-only matches hide Edit/Delete,
  show the "from:" badge), `AppShell.test.tsx` — 71 tests, all passing.
  `ViewingSelector.test.tsx` deleted along with the component.

**Not done here**: broader manual UAT beyond the one 2-account pass above
(e.g. roster tier-conflict reconciliation on staging) is not yet run.
