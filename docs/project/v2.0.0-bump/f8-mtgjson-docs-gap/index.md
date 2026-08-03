# F8. MTGJSON import documented but not implemented

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `docs/content/back/barrins_api/auth_roles.md` | Documentation fix, but see S8 for the real gap it points to |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — found 2026-07-26 while scoping S4 | / |
| **Source** | Discovered while scoping S4 (`v2.0.0-bump/index.md` §1) | / |
| **Dependency** | None | Blocks nothing directly; motivates S8 |

---

## Context

Same category of gap as F7 (planning docs that don't exist), inverted:
here a doc describes a **route/feature as already implemented** that
isn't. `docs/content/back/barrins_api/auth_roles.md`'s role table and
security matrix describe:

- `POST /mtgjson/import` (admin-only, "Replaces `X-Admin-Key`").
- `GET /sets/`, `GET /sets/{code}`, `GET /sets/{code}/cards` (anonymous,
  public).
- `GET /cards/{uuid}`, `/cards/{uuid}/prices`, `/cards/by-name/{name}`
  (anonymous, public).
- The `admin` role's description: "Everything, including MTGJSON import
  and user management."

**Verified 2026-07-26, none of it exists**: a full-repo search for
`mtgjson` (case-insensitive) matches **zero Python files** — only
markdown docs (`auth_roles.md`, `bff/tamiyo_scroll.md`,
`signup_email_verification.md`, `CHANGELOG.md`, `cspell.json`) and
`apps/barrins_api/README.md`. `apps/barrins_api/app/models/` has no
`Card`/`Set` model (only `tamiyo_scroll.py`, `user.py`,
`email_verification.py`, `base.py`, `_types.py` — the same list already
confirmed in the project index's §0). No `routers/mtgjson.py`, no
`sets`/`cards` routers anywhere in `app/api/`.

This was first surfaced because S4 ("better decklist display") and S2's
team deck-validation gate were both originally planned assuming this
pipeline "already existed" — both assumptions were wrong, corrected in
`../index.md` §1.6 and `../s2-team-sharing/index.md`.

## Done statement

- `auth_roles.md`'s role table and security matrix either: (a) mark the
  `mtgjson`/`sets`/`cards` rows as **not yet implemented** (matching the
  🔲 convention already used elsewhere in that same file for `role_c`),
  or (b) are removed until S8 actually builds the feature, whichever the
  user prefers — not decided here.
- No other doc in the repository is left describing this as existing
  behavior.

## Tasks

- [ ] Confirm with the user: mark as not-yet-implemented, or remove
      until built.
- [ ] Update `auth_roles.md` accordingly.
- [ ] Cross-check `bff/tamiyo_scroll.md` and
      `signup_email_verification.md`'s `mtgjson` mentions for the same
      issue (found in the same grep, not yet individually reviewed).

## UAT (manual)

- [ ] N/A — documentation-only item.

## Non-regression tests

- N/A — covered by the existing docs CI job (markdownlint/spellcheck).
