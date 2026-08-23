# S13. Confirmation before every deletion

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/tamiyo_scroll` (React/Vite) only | No `barrins_api` change |
| **Initial date** | 2026-08-23 | Drafted 2026-08-23 |
| **Status** | Not started | / |
| **Source** | GitHub issue [#79](https://github.com/Spigushe/barrins-project/issues/79), reported 2026-08-23 — a user clicked Delete instead of Edit in the Match journal with no confirmation at all | / |
| **Dependency** | None | / |

---

## Context

**Verified against the code (2026-08-23, `feat/tolaria_news_backend`):** seven
places in `apps/tamiyo_scroll` have a Delete action. Four have **no
confirmation whatsoever** — the exact bug reported in #79:

| Location | Entity | Confirmation today? |
| --- | --- | --- |
| `pages/suivi-bo3/MatchJournalSection.tsx:238-247` | Match (journal row) | **None** — `onClick` calls `deleteMatch.mutateAsync(match.id)` directly |
| `pages/suivi-bo3/CardTestsSection.tsx:448-457` | Card test | **None** — `onClick` calls `deleteTest.mutateAsync(test.id)` directly |
| `pages/decklist/VersionHistorySection.tsx:39-48` | Decklist version | **None** — `onClick` calls `deleteVersion.mutateAsync(...)` directly |
| `pages/sessions/SessionsSections.tsx:454-463` | Session (archive) | **None** — `onClick` calls `handleArchive(session.id)` directly |
| `pages/metagame/MetaDecksSections.tsx:212-378` (`RosterRow`) | Meta/roster deck | **Has it** — S12 item 12, `Dialog`-based, `confirmingDelete` local state |
| `components/layout/PersonalDeckSelector.tsx:277-312` | Personal deck | **Has it** — same `Dialog` pattern, `pendingArchive` state |
| `components/layout/AccountSettingsTeamSection.tsx:51-190` | Team (hard delete) | **Has it**, plus a stronger step: user must retype the team's invite code before the destructive button enables; backend also enforces this (`TeamDelete.invite_code`) |

**No shared confirm-dialog component exists.** `components/ui/dialog.tsx`
only wraps `@radix-ui/react-dialog` (generic modal). The 3 working confirm
flows above all hand-roll the same markup independently: local pending-
target state → `Dialog` + `DialogContent` + `DialogTitle` → body text
("It will disappear from ... This can't be undone.") → `Cancel`
(`variant="outline"`) + destructive action (`variant="destructive"`,
already defined in `components/ui/button.tsx`). `@radix-ui/react-alert-
dialog` is **not** an installed dependency — no new dependency is needed
to fix this, the existing `Dialog` primitive is sufficient.

## Design decisions

- **Extract a shared `ConfirmDialog` component**, rather than adding a
  4th/5th/6th/7th copy of the same inline markup. This goes slightly
  beyond #79's literal ask (which only names Match journal), but the
  fix generalizes to all 4 unprotected spots at once, and consolidating
  the 3 already-working copies onto the same component (Constitution
  §4.5, prefer composition) is a small, low-risk touch on top of that —
  each of those 3 already tests the same interaction shape, so the
  refactor is mechanical, not a design change.
- Built on the existing `Dialog` primitive — no `@radix-ui/react-alert-
  dialog` dependency added (Constitution §22/§4.7).
- `AccountSettingsTeamSection` keeps its extra retype-invite-code step;
  it can adopt the shared component for its title/button chrome without
  losing that stronger flow.

## Done statement

- A new `components/ui/confirm-dialog.tsx` exports `<ConfirmDialog
  open onOpenChange title description confirmLabel="Delete"
  onConfirm variant="destructive" />`.
- Clicking Delete on a Match journal row, a Card test row, a Decklist
  version row, or a Session's archive action opens a confirmation
  dialog naming the target; the mutation only fires on explicit
  confirm, never on the initial click.
- `MetaDecksSections`, `PersonalDeckSelector`, and
  `AccountSettingsTeamSection` are refactored onto `ConfirmDialog`
  (the team flow keeps its extra invite-code-retype input on top);
  behavior for all three is unchanged from a user's perspective.

## Tasks

### 1. Shared component

- [ ] Build `components/ui/confirm-dialog.tsx`.

### 2. Wire into the 4 unprotected spots

- [ ] `MatchJournalSection.tsx` delete action.
- [ ] `CardTestsSection.tsx` delete action.
- [ ] `VersionHistorySection.tsx` delete action.
- [ ] `SessionsSections.tsx` archive action.

### 3. Refactor the 3 existing spots onto the shared component

- [ ] `MetaDecksSections.tsx` (`RosterRow`).
- [ ] `PersonalDeckSelector.tsx`.
- [ ] `AccountSettingsTeamSection.tsx` (title/button chrome only — keep
      the invite-code-retype step).

## Open questions (flagged, not guessed)

1. **Exact confirm copy per entity type.** The existing pattern's body
   text ("It will disappear from ... This can't be undone.") is a
   reasonable template; exact wording per entity (Match/Card test/
   Decklist version/Session) is unconfirmed — pick reasonable copy
   during implementation unless the user has a preference.

## UAT (manual)

- [ ] Click Delete on a Match journal row → confirm dialog appears
      naming the match; Cancel leaves it in place, Confirm deletes it.
- [ ] Same for a Card test row, a Decklist version row, and a Session's
      archive action.
- [ ] Existing archive/delete flows for a roster deck, a personal deck,
      and a team still work exactly as before after the refactor.

## Non-regression tests

- Frontend: existing tests for `MetaDecksSections`/`PersonalDeckSelector`/
  `AccountSettingsTeamSection` confirm-then-delete flows still pass
  after the refactor onto `ConfirmDialog`.
- Frontend: new tests for the 4 previously-unprotected delete flows,
  covering both Cancel (mutation never called) and Confirm (mutation
  called once).

## See also

- [s12-uiux-polish/](../s12-uiux-polish/index.md) — item 12 there is
  the origin of the confirm-before-delete pattern this item generalizes.
