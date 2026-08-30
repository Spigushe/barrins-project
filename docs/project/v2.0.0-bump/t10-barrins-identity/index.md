# T10. Barrin's Identity — service implementation

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_identity/`, `libs/identity_client/`, `.github/workflows/CI.yml`, `docs/content/back/barrins_identity/*`, `docs/content/front/goblin_guide/*`, `docs/content/ops/deployment/identity.md`, `decisions.md` (ADR-16/17) | / |
| **Initial date** | 2026-08-29 | / |
| **Status** | 🟩 **Done (2026-08-29)** — service + shared verifier on `proj/v2.0.0-bump`, `uv run pytest` green in both packages, `ruff`/`ty`/`bandit` clean. Cutover / playbook / Goblin Guide deliberately **out of scope** (each a separate gated phase). | / |
| **Source** | Local branches `feat/barrins-identity` + `claude/barrins-identity-lifecycle-settings-4g2lyh`; [ADR-16](../../../content/ops/architecture/decisions.md#adr-16-adopt-barrins-identity-as-the-rs256-jwks-authority), [ADR-17](../../../content/ops/architecture/decisions.md#adr-17-shared-code-lives-in-a-top-level-libs-directory) | / |
| **Dependency** | None inbound. **T9** (Karn Jupyter workbench proxy role gate) depends on this service existing. | / |

---

## Context

The full Barrin's Identity documentation set (platform / integration /
tests / Goblin Guide / deployment, ADR-16, ADR-17) landed on
`docs/barrins-identity-integration` (off `proj/v2.0.0-bump`) ahead of any
code. A working service already existed on two **stale** feature branches
whose merge-base with `staging` is a near-initial commit, so cherry-picking
would have dragged in or conflicted with tens of thousands of lines.

**Decision (user, 2026-08-29):** copy the file tree over (path checkout,
not `git cherry-pick`), reconcile it with current monorepo conventions,
and land it as one logical commit. `username` (`Q-03`) and
`libs/identity_client/` (`Q-01`) are **in scope**; the `barrins_api`
cutover, the `ops/my-server/barrins_identity.yml` playbook + Brevo/OVH
email execution, and the Goblin Guide frontend are **out of scope**.

## Design

- **Source of the copy:** `claude/barrins-identity-lifecycle-settings-4g2lyh`
  is a strict superset of `feat/barrins-identity` for the identity app
  (login/JWKS/service-accounts + signup, password reset, deletion,
  settings, per-app settings, email senders). `scripts/workflow_ci.py`
  taken verbatim from `apps/barrins_api` (byte-identical to the copy on
  `feat/barrins-identity`).
- **`username`:** `VARCHAR(64)` UNIQUE NOT NULL INDEX on `users`
  (migration `f6a7b8c9d0e1`, chained after `e5f6a7b8c9d0`). Input rule
  `^[A-Za-z0-9_-]{3,32}$` (`schemas.auth.USERNAME_PATTERN`, exposed via
  OpenAPI); the column is wider so a soft-deleted row can be anonymized to
  `deleted-<uuid>` alongside `email`. Required on `UserSignup` /
  `UserCreate`, echoed in `UserRead`, threaded through `/auth/signup`,
  `/auth/register`, and `create_admin.py --username`. A taken handle → a
  `409` with a message distinct from the email conflict. Login is
  unchanged — the OAuth2 form field named `username` still carries the
  email (`Q-05` deferred).
- **`libs/identity_client/`:** new shared package under `libs/` (ADR-17
  convention, mirroring `libs/dc_calendar/`). `JWKSCache` (fetch +
  monotonic-TTL cache + refresh-on-unknown-`kid`), framework-free
  `verify_token` → `VerifiedPrincipal`, and `make_verify_dependency` for
  FastAPI (`401` + `WWW-Authenticate: Bearer` on a bad token, `403` on a
  missing scope). Written from `integration.md` §2–§3 + the token shapes
  in `apps/barrins_identity/app/core/security.py`; nothing to copy (it
  existed nowhere). Not wired into any consumer.
- **CI:** the pre-existing `back` job is hard-pinned to
  `working-directory: apps/barrins_api` and never ran identity tests. A
  dedicated `identity` job was added (Postgres 17 service, its own
  `barrins_identity` / `_test` DBs, `workflow_ci.py --no-fix` for the app
  then `ruff`/`ty`/`pytest` for `libs/identity_client`).
  `apps/barrins_identity/**` + `libs/identity_client/**` moved to their own
  paths-filter entry; `identity` added to `ci-required`.

## Done statement

- `apps/barrins_identity/` present on `proj/v2.0.0-bump` — 313 tests,
  98.72% overall, 100% `app/models` + `app/schemas`; `ruff`/`ruff
  format`/`bandit`/`ty` clean; `uv.lock` regenerated.
- `libs/identity_client/` present — 26 tests, 100% coverage,
  `ruff`/`ty` clean, `uv.lock` present.
- `.github/workflows/CI.yml` runs both via a new `identity` job wired into
  `ci-required`.
- `apps/barrins_identity/.env.example` reconciled with the on-branch
  `ops/my-server/secrets/barrins_identity/*.env.example` (added the
  `PASSWORD_RESET_*` and `MAX_APP_SETTINGS_BYTES` sections).
- Docs updated: platform / integration / tests / README banners flipped
  🟨 → 🟩; `Q-01` and `Q-03` marked built; `Q-05` marked deferred; ADR-16
  Update note + ADR-17 consequence bullets; this tracker.
- One logical commit (constitution §18.3). **Not touched:**
  `apps/barrins_api/**`, `apps/goblin_guide/**`,
  `ops/my-server/barrins_identity.yml` (nonexistent).

## UAT (manual)

- [x] `cd apps/barrins_identity && uv run alembic upgrade head` applies all
      six migrations against a scratch Postgres; `alembic check` →
      "No new upgrade operations detected" (migration chain matches the
      ORM models). `\d users` confirms `username varchar(64) NOT NULL` +
      `ix_users_username UNIQUE`.
- [x] `uv run python scripts/workflow_ci.py --no-fix` — all green
      (ruff check, ruff format --check, bandit, ty, 313 pytest).
- [x] `scripts/create_admin.py --help` shows the required `--username`;
      an invalid handle is rejected before the password prompt. (Full
      interactive creation needs a TTY — not run in this session.)
- [x] `POST /api/v1/auth/token` / `/auth/refresh` / `/auth/logout`,
      `GET /.well-known/jwks.json`, service-token exchange — covered by
      `tests/test_routes_*` + `tests/test_jwks.py` (all green).
- [x] `cd libs/identity_client && uv run pytest` — 26 passed, 100%.
- [x] `markdownlint` + `cspell` on the edited `docs/content/**` pages and
      `uvx --with mkdocs-material mkdocs build --strict` — all clean.

## Non-regression tests

- `apps/barrins_identity/tests/` (313) — includes new `username` cases:
  model uniqueness, schema pattern accept/reject + required, route-level
  `409` username-taken (distinct message) on `/auth/signup` and
  `/auth/register`, `422` missing username, and username anonymization +
  reuse on account deletion.
- `libs/identity_client/tests/test_client.py` (26) — valid user/service
  tokens, expiry, wrong signing key, unknown-`kid` single refetch,
  `type`/`account_type` mismatch, insufficient scope, cache hit/expiry,
  injected `http_client` reuse, and the FastAPI dependency's 401/403/200.
- CI: the new `.github/workflows/CI.yml` `identity` job runs both on any
  change under `apps/barrins_identity/**` or `libs/identity_client/**`.
