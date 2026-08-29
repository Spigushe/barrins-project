# T11. Goblin Guide — frontend (login slice)

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `libs/goblin_guide/`, `apps/goblin_guide/`, `.github/workflows/CI.yml`, `docs/content/front/goblin_guide/bootstrap.md`, `docs/content/ops/architecture/decisions.md` (ADR-17) | / |
| **Initial date** | 2026-08-29 | / |
| **Status** | 🟨 **Login slice done (2026-08-29)** — `G-03` step 1 on `proj/v2.0.0-bump`. Library `npm run build` + 17 tests green; shell `npm run build` + 3 tests green; `oxlint` + `prettier --check` clean on both. Signup / reset / settings / admin slices, host mounting, and the deploy playbook are **out of scope** (each a later slice or phase). | / |
| **Source** | [ADR-17](../../../content/ops/architecture/decisions.md#adr-17-shared-code-lives-in-a-top-level-libs-directory), [Goblin Guide — Bootstrap](../../../content/front/goblin_guide/bootstrap.md), [Barrin's Identity — Integration Contract](../../../content/back/barrins_identity/integration.md) §4.1 / §8.1–§8.2 | / |
| **Dependency** | **T10** (the identity service the frontend talks to). One of T10's three deferred phases — the other two (the `barrins_api` cutover, the `ops/my-server/barrins_identity.yml` playbook) are unrelated to this item. | / |

---

## Context

T10 landed the identity service and shared verifier but deliberately left
the Goblin Guide frontend out. [Bootstrap.md](../../../content/front/goblin_guide/bootstrap.md)
settled the *shape* (ADR-17: a shared library plus a thin standalone
shell) but flagged delivery order (`G-03`), token storage (`G-05`) and
all UX as "confirm before building".

**Decisions (user, 2026-08-29):**

- **Placement** — `libs/goblin_guide/` holds the shared library (Vite
  library mode); `apps/goblin_guide/` is the standalone shell; the shell
  consumes the library as a `file:../../libs/goblin_guide` npm path
  dependency. (No JS workspace tooling exists in the monorepo.)
- **Scope of this increment** — scaffolding + `G-03` step 1 only
  (login, silent refresh, `GET /auth/me` account view), one logical
  commit.
- **`G-03` delivery order** — locked as proposed: login → signup +
  email verification → password reset → account settings + delete →
  admin service-account management.
- **UX** — mockups approved first via a design canvas ("Goblin Guide
  Login Slice"), then matched in code against `tamiyo_scroll`'s existing
  `LoginPage` and the shared CSS token contract.

## Design

- **`libs/goblin_guide/` (`@barrins/goblin-guide`)** — React 19 + TS,
  Vite **library mode** (`formats: ['es']`, `react` / `react-dom` /
  `react/jsx-runtime` / `@tanstack/react-query` externalized as peer
  dependencies). `build` = `tsc -b` (typecheck) + `vite build` (JS +
  CSS) + `tsc -p tsconfig.build.json` (`.d.ts` emit → `dist/`). No new
  dependency beyond `zod`.
  - `createIdentityClient` — framework-free `fetch` client. `login`
    posts the email as the OAuth2 `username` field (`Q-05` deferred);
    `me` / `logout` go through an authed wrapper with a **single-flight
    silent-refresh retry** on `401` (`POST /auth/refresh`; on failure the
    token store is cleared and an `IdentityError(401)` is thrown).
  - `TokenStore` / `createMemoryTokenStore` — pluggable client-side
    storage (`G-05`). Default keeps both tokens in memory; a host can
    pass its own (e.g. an `HttpOnly`-cookie BFF) with no other change.
  - `IdentityProvider` + `useIdentity` / `useCurrentUser` / `useLogin` /
    `useLogout` — TanStack Query hooks; the provider sits under the
    host's `QueryClientProvider`.
  - `LoginScreen` — the approved mockup. Default / invalid-credentials
    (`role="alert"`) / in-flight (form + button locked) /
    session-expired (`role="status"`) states. Navigation is the host's
    job via an `onAuthenticated` callback; `onForgotPassword` /
    `onCreateAccount` render links only when a handler is supplied.
  - `styles.css` — every value resolves a host CSS custom property
    (`--color-*`, `--radius-*`, `--font-sans`) with a fallback (the
    "Suivi" palette), so the library renders in each host's theme.
    Classes are `gg-`-prefixed; no Tailwind dependency.
- **`apps/goblin_guide/`** — router + `QueryClientProvider` +
  `IdentityProvider` + the default token theme in `index.css`. Routes:
  `/login` → `LoginRoute` (redirects out when already authenticated,
  reads `?expired=1` for the banner), `/` → `RequireAuth` → `Shell`
  (the `GET /auth/me` read-out per the mockup; on a query error it
  redirects to `/login?expired=1`). `VITE_IDENTITY_SERVICE_URL`
  (default `http://localhost:8001`).
  - `vite.config.ts` sets `resolve.dedupe` for `react`, `react-dom`,
    `react-router-dom`, `@tanstack/react-query` and inlines
    `@barrins/goblin-guide` for vitest — the path dependency is
    symlinked with its own `node_modules`, so without dedupe React
    resolves to a second copy and the hooks dispatcher breaks.
- **CI** — a dedicated `goblin_guide` job: `npm ci` + `lint` +
  `format:check` + `build` + `test` for the library, then the same for
  the shell (library first — the shell needs its `dist/`). New
  `apps/goblin_guide/**` + `libs/goblin_guide/**` paths-filter entry;
  `goblin_guide` added to `ci-required`.
- **`strict: true`** in both `tsconfig.app.json`s — greenfield, and this
  is auth-adjacent code; the older frontends omit it.

## Done statement

- `libs/goblin_guide/` present on `proj/v2.0.0-bump` — `npm run build`
  green (ES bundle + CSS + `dist/*.d.ts`), 17 vitest tests
  (`tokenStore` 3, `client` 8, `LoginScreen` 6), `oxlint` +
  `prettier --check` clean.
- `apps/goblin_guide/` present — `npm run build` green, 3 vitest tests
  (`App` smoke: redirect, session-expired banner, login → shell),
  `oxlint` + `prettier --check` clean. `README.md` rewritten from the
  placeholder (syncs to `docs/content/front/goblin_guide/index.md`).
- `.github/workflows/CI.yml` runs both via the new `goblin_guide` job,
  wired into `ci-required`.
- Docs: `bootstrap.md` status flipped ⬜ → 🟨, `G-03` marked Resolved,
  `G-05` marked partly settled, tests-first note updated; ADR-17 gains a
  T11 consequence bullet; this tracker; project index row.
- One logical commit (constitution §18.3). **Not touched:**
  `apps/tamiyo_scroll/**`, `apps/tolaria_news/**`, `apps/barrins_identity/**`,
  `ops/**`.

## UAT (manual)

- [x] `cd libs/goblin_guide && npm run build` — `tsc` clean, Vite emits
      `dist/goblin-guide.js` (107 kB) + `dist/goblin-guide.css` +
      `dist/index.d.ts` and per-module `.d.ts`.
- [x] `cd libs/goblin_guide && npm test` — 17 passed.
- [x] `cd apps/goblin_guide && npm install` symlinks
      `@barrins/goblin-guide` → `../../libs/goblin_guide`;
      `npm run build` + `npm test` — 3 passed.
- [x] `npm run lint` + `npx prettier --check .` — clean in both packages.
- [ ] Run the shell against a live `barrins_identity` (`npm run dev`,
      `VITE_IDENTITY_SERVICE_URL` pointed at a local instance) — deferred
      to the cutover/playbook phase; no live service is running yet.

## Non-regression tests

- `libs/goblin_guide/src/**/*.test.ts(x)` (17): memory token store
  set/get/clear + subscribe/unsubscribe; login stores the pair / 401
  throws `IdentityError` with the parsed detail and stores nothing;
  bearer header attached; `401` → one refresh → retry with the rotated
  token; refresh failure clears the store and throws; no-refresh-token
  path makes no network call; concurrent `401`s coalesce to one
  refresh; `logout` clears local state even when the request rejects;
  `LoginScreen` renders / blocks empty submit with no request / calls
  `onAuthenticated` / surfaces the uniform `401` / shows the
  session-expired banner / locks the form in flight.
- `apps/goblin_guide/src/App.test.tsx` (3): unauthenticated `/` →
  login screen; `/login?expired=1` → banner; type + submit → account
  shell shows the principal.
- CI: the new `goblin_guide` job runs both packages on any change under
  `apps/goblin_guide/**` or `libs/goblin_guide/**`.
