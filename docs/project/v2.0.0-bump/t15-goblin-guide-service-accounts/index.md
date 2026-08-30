# T15. Goblin Guide — admin service-account management

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `libs/goblin_guide/`, `apps/goblin_guide/`, `docs/content/front/goblin_guide/bootstrap.md`, `docs/content/ops/architecture/decisions.md` (ADR-17) | / |
| **Initial date** | 2026-08-30 | / |
| **Status** | 🟨 **Service-account slice done (2026-08-30)** — `G-03` step 5 / `G-04` on `feat/goblin-guide-login`. Library `npm run build` + 85 tests green; shell `npm run build` + 14 tests green; `oxlint` + `prettier --check` clean on both. This completes `G-03`. Host mounting in `tamiyo_scroll` / `tolaria_news` and the deploy playbook remain **out of scope**. | / |
| **Source** | [Goblin Guide — Bootstrap](../../../content/front/goblin_guide/bootstrap.md) `G-03` / `G-04`, [Barrin's Identity — Integration Contract](../../../content/back/barrins_identity/integration.md) §4.6 | / |
| **Dependency** | **T14** (the account-settings slice this builds on — reuses the `gg-` section/danger styling and the shell's `RequireAuth` `?next=` return path). | / |

---

## Context

T14 landed `G-03` step 4 (account settings + delete). The locked `G-03`
order (bootstrap.md §3) puts **admin service-account management** last —
it is `G-04`, resolved 2026-08-29 (ADR-17) as part of the Goblin Guide
library rather than a separate CLI-only surface. The backend is already
on the release line and tested
(`apps/barrins_identity/app/api/v1/service_accounts.py`): `GET
/api/v1/service-accounts`, `POST /api/v1/service-accounts`, `POST
/api/v1/service-accounts/{client_id}/revoke` — wire contract frozen in
[integration.md §4.6](../../../content/back/barrins_identity/integration.md#46-service-accounts).
This slice is frontend only; no backend change.

**Decisions (user, 2026-08-30 — four-question round):**

- **Screen home** — a dedicated shared-library `ServiceAccountsScreen`
  on its own shell route (`/service-accounts`), **not** a section of
  `AccountScreen`. Keeps self-service and the admin tool separate.
- **Non-admin access** — an in-app "administrator access required"
  panel for an authenticated non-admin; a logged-out hit bounces to
  `/login?next=/service-accounts` via the existing `RequireAuth` (T14),
  and returns after sign-in.
- **Design canvas first** — same as T13/T14. Canvas "Goblin Guide
  Service Accounts" (list / one-time secret reveal / revoke confirm /
  first-run empty / 403) approved before code.
- **Endpoint scope** — create / list / revoke only. `POST
  /api/v1/service-token` is **excluded**: it is a `client_credentials`
  exchange a consuming service performs with its own stored secret, not
  an action an admin takes in this UI.

## Design

- **`libs/goblin_guide/`**
  - `schemas.ts` — `serviceAccountSchema` (`{id, client_id, description,
    scopes, is_active, created_at}`), `serviceAccountListSchema`, and
    `serviceAccountCreatedSchema` (adds `client_secret`).
  - `client.ts` — `IdentityClient` gains `listServiceAccounts()` (GET,
    authed), `createServiceAccount({description?, scopes})` (POST;
    `description` omitted from the body when `undefined`; the parsed
    result carries the one-time `client_secret`), and
    `revokeServiceAccount(clientId)` (POST `…/{client_id}/revoke`,
    `client_id` URL-encoded, resolves on `204`; `404` → `IdentityError`).
    Plus the `ServiceAccountCreateInput` type. All three go through
    `authed` / `authedJson`, so they get the single silent-refresh
    retry.
  - `hooks.ts` — `useServiceAccounts` (query, enabled once
    authenticated), `useCreateServiceAccount` and
    `useRevokeServiceAccount` (both invalidate the list on success — a
    revoked account stays in it, now `is_active: false`).
  - `ServiceAccountsScreen` — a `useCurrentUser()` gate delegating to an
    inner `ServiceAccountsAdmin` for an `admin` principal, and to a
    `ForbiddenPanel` (`ShieldMark` + copy + an optional "Back to my
    account" button wired to `onBack`) for anyone else. `Admin` is a
    three-branch render on the `gg-` token CSS:
    - **default** — a "New service account" section (a `.gg-input`
      description field + a `.gg-taginput` chip editor: Enter / `,`
      adds, Backspace on an empty draft removes the last, a non-empty
      draft is folded in on submit, ≥ 1 enforced client-side) above an
      "Existing accounts · N" section (loading / error / empty states,
      then `ServiceAccountCard`s sorted active-first then newest-first —
      `client_id`, a `StatusChip`, description or "No description",
      scope chips, `Created <date>` via `Intl.DateTimeFormat`, and a
      small `.gg-button-danger--outline` Revoke on active accounts
      only).
    - **created** — the whole screen becomes the one-time secret panel:
      a warning banner, read-only `client_id` + `client_secret`
      `.gg-cred` rows with `.gg-icon-btn` copy buttons
      (`navigator.clipboard`, best-effort), the scope chips, and a
      "Done — I've saved these credentials" button back to the list.
    - **revoking** — the whole screen becomes the revoke confirm: the
      target account card, a `--gg-danger`-toned section, a danger
      banner naming the `client_id`, a permanence note, the
      `.gg-button-danger` confirm, and a "Cancel" link.
  - `styles.css` — `.gg-taginput` / `.gg-tag` / `.gg-tag-field`,
    `.gg-cred` / `.gg-cred-val`, `.gg-sa-list` / `.gg-sa-card` /
    `.gg-sa-head` / `.gg-sa-id` / `.gg-sa-desc` / `.gg-sa-chips` /
    `.gg-sa-chip` / `.gg-sa-meta` / `.gg-sa-created`, `.gg-status`
    (`[data-tone]`) + `.gg-status-dot`, `.gg-button--sm`, `.gg-sa-empty`.
    No new token.
  - `icons.tsx` — `CopyIcon`, `CloseIcon`.
  - `index.ts` exports `ServiceAccountsScreen` + props, the three hooks,
    `ServiceAccountCreateInput`, `ServiceAccount`, `ServiceAccountCreated`.
- **`apps/goblin_guide/`**
  - `ShellFrame.tsx` — the authenticated header + centered `<main>`
    extracted out of `Shell.tsx` (the `useCurrentUser` gate, the
    `isError` → `/login?expired=1` redirect, the user chip + role + log
    out). Adds an admin-only nav link that toggles Account (`/`) ↔
    Service accounts (`/service-accounts`) by `useLocation()`.
  - `Shell.tsx` — now `<ShellFrame><AccountScreen …/></ShellFrame>`.
  - `ServiceAccountsRoute.tsx` — `<ShellFrame><ServiceAccountsScreen
    onBack={() => navigate('/')} /></ShellFrame>`.
  - `App.tsx` — a `/service-accounts` route behind `RequireAuth`,
    registered before `/`.
- **CI** — no workflow change: the `goblin_guide` job and its
  `apps/goblin_guide/** + libs/goblin_guide/**` paths filter (T11)
  already cover this slice.

## Done statement

- `libs/goblin_guide/` — `npm run build` green (ES bundle + CSS +
  `dist/*.d.ts`), 85 vitest tests (the T14 set plus `client` service
  accounts ×6 and `ServiceAccountsScreen` ×6), `oxlint` + `prettier
  --check` clean. `CHANGELOG.md` + `README.md` updated.
- `apps/goblin_guide/` — `npm run build` green, 14 vitest tests (the 11
  earlier-slice cases plus the `/service-accounts` `?next=` bounce, the
  admin screen, and the non-admin access panel), `oxlint` + `prettier
  --check` clean.
- Docs: `bootstrap.md` status banner + `G-03` / `G-04` rows + §6;
  ADR-17 gains a T15 consequence bullet; this tracker; project index
  T15 row and the T14 "Not done" list trimmed; `apps/goblin_guide/README.md`;
  `docs/CHANGELOG.md`.
- One logical commit (constitution §18.3). **Not touched:**
  `apps/tamiyo_scroll/**`, `apps/tolaria_news/**`,
  `apps/barrins_identity/**`, `ops/**`, `.github/**`.

## UAT (manual)

- [x] `cd libs/goblin_guide && npm run build` — `tsc` clean, Vite emits
      `dist/goblin-guide.js` + `.css` + `dist/*.d.ts` (new
      `ServiceAccountsScreen` declaration included).
- [x] `cd libs/goblin_guide && npm test` — 85 passed.
- [x] `cd apps/goblin_guide && npm run build` + `npm test` — 14 passed.
- [x] `npm run lint` + `prettier --check` — clean in both packages
      (line endings aside — this Windows checkout is CRLF; CI runs LF).
- [ ] Run the shell against a live `barrins_identity` (`npm run dev`,
      sign in as an `admin`, create a service account and copy the
      one-time secret, revoke it, confirm a non-admin sees the access
      panel) — deferred to the cutover/playbook phase; no live service
      is running yet.

## Non-regression tests

- `libs/goblin_guide/src/auth/client.test.ts` — `service accounts`:
  `listServiceAccounts` sends the bearer token and parses the array;
  `createServiceAccount` sends `{description, scopes}` and returns the
  `client_secret`, and omits `description` when it is `undefined`;
  `revokeServiceAccount` POSTs to `…/{client_id}/revoke` and resolves on
  `204`; the `404` and the non-admin `403` surface as `IdentityError`.
- `libs/goblin_guide/src/components/ServiceAccountsScreen.test.tsx` — a
  non-admin sees the access panel and no list fetch is made; an admin
  sees the list with active/revoked badges and one Revoke button;
  the empty state; a no-scope create is blocked with an inline error and
  no request; a create with two scopes sends `{description, scopes}`,
  reveals the secret, and returns to the list showing the new account; a
  revoke walks list → confirm (cancel path, then confirm → `/revoke`
  POST → back to the list with the Revoke button gone).
- `apps/goblin_guide/src/App.test.tsx` — an unauthenticated
  `/service-accounts` bounces to `/login` with `next=%2Fservice-accounts`;
  an admin who signs in with `?next=/service-accounts` lands on the
  screen and the header shows the "Account" toggle; a non-admin lands on
  the access panel.
- CI: the existing `goblin_guide` job runs both packages on any change
  under `apps/goblin_guide/**` or `libs/goblin_guide/**`.
