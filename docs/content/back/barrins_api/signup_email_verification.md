# Implementation Plan — Self-Registration & Email Verification

> **Target**: barrins-project/barrins_api
> **Initial date**: 2026-07-15
> **Status**: ✅ Implemented — 2026-07-15 (backend only, verification screen on
  the
> Tamiyo Scroll side still to do — see "Open point" section at the end of this
  document)
> **Trigger**: shared identity prerequisite for the "Competitive MTG Tracking"
  tracker
> (Tamiyo Scroll), but cross-cutting scope — reusable by any future Barrin's
  application
> (constitution §13, §40).

---

## Objective

At the end of this implementation, the API must:

1. Allow an anonymous visitor to create an account (`POST /api/v1/auth/signup`)
   with `email` + `password` + `display_name?` — without ever being able to
   self-assign a role or a verified status (the existing `UserSignup` schema
   already forbids this via `extra="forbid"`).
2. Generate a 6-digit verification code, send it by email, and associate it with
   the newly created account (`is_verified=False`, Level 1 — constitution
   §13.4).
3. Allow code validation (`POST /api/v1/auth/signup/verify`): on success → the
   account moves to `is_verified=True` (Level 2) and the user directly receives
   a pair of JWT tokens (automatic login after verification).
4. Allow resending a new code (`POST /api/v1/auth/signup/resend`) with an
   anti-abuse throttle (cooldown + maximum number of attempts before a mandatory
   renewal).
5. Never log or expose a verification code in clear text beyond the email sent.
6. Cover error cases: email already taken (409, consistent with the existing
   `/auth/register`), invalid/expired code (400), too many attempts (429),
   account already verified (409 on `/verify` and silent no-op on `/resend`).
7. Include a confirmation link in the email that points to a frontend page which
   pre-fills the code — without ever triggering an automatic `POST /verify` when
   the page loads (see Option D).

> **Product decision**: a dedicated Gmail account (`barrins-identity@gmail.com`)
  as the
> sender — see the Gmail subsection of option A below for the configuration
> implications.

---

## Options analysis

### A. Email sending

| Option | Mechanism | Advantages | Drawbacks |
| ------ | --------- | --------- | ------------- |
| **A1 (selected)** | `smtplib` + `email.mime` (stdlib) | Zero new pip dependency; configured via env vars (`SMTP_HOST`, etc.) already in the spirit of `BaseAppSettings` | Requires an operational SMTP relay in prod (Agent 3 decision — out of scope for this plan) |
| B | Provider SDK (Resend, SendGrid, Postmark…) | Simple HTTP API, deliverability managed | New pip dependency + paid account + API key to provision — product/infra decision not settled, to be justified separately (§4.7/§22) |
| C | Provider via `httpx` (already present) without a dedicated SDK | No new dependency | Provider choice = business decision, not yet made; unnecessary complexity while A1 suffices |

**Choice: option A1** — no new dependency to justify, and dev/test behavior (no
SMTP relay available locally) is covered by an `EmailSender` with two
implementations: `SMTPEmailSender` (production/staging) and `ConsoleEmailSender`
(development/tests — logs the code instead of sending it). Automatic selection:
if `smtp_host` is empty, the `development`/`test` environment falls back to
`ConsoleEmailSender`; in `production`, an empty `smtp_host` raises a
configuration error at startup (same pattern as
`secret_key_must_not_be_placeholder`).

#### Gmail specifics (chosen relay)

The chosen SMTP relay is a Gmail account created for the occasion
(`barrins-identity@gmail.com`), not a dedicated transactional provider.
Consequences to document (deployment — Agent 3):

- **Mandatory app password**: Gmail refuses classic-password SMTP authentication
  as soon as 2-step verification is active (required to generate an app
  password). The secret stored in `smtp_password` is this 16-character app
  password, never the Google account password.
- **`From`/authenticated account consistency**: Gmail requires the `From` header
  to match the authenticated SMTP account (unless a "Send as" alias is
  configured separately in Gmail). `smtp_from_address` must therefore be
  identical to `smtp_username`.
- **Quota**: ~500 emails/day on a free Gmail account. Largely sufficient for a
  launch; to monitor if the volume of created accounts increases significantly
  (not blocking for this plan, to revisit with Agent 3 if needed).
- **Send failure = no orphan account**: if the SMTP send raises an exception
  during `POST /signup`, the DB transaction (creation of `User` +
  `EmailVerification`) is rolled back and the API returns `502 Bad Gateway`
  rather than leaving an `is_verified=False` account with no way to receive a
  code (a `resend` on an account that doesn't exist yet would fail).

### B. Verification code storage

| Option | Mechanism | Advantages | Drawbacks |
| ------ | --------- | --------- | ------------- |
| A | Columns on `users` (`verification_code_hash`, `verification_expires_at`, …) | No new table | Pollutes the `User` model with transient state; no history |
| **B (selected)** | Dedicated `auth_email_verifications` table (1 active row per user, upsert on resend) | Isolates transient state from the central identity model; consistent with the earlier `decklist_imported_files` (dedicated tracking table, see `docs/decklist_integration/`) | One more table |

**Choice: option B**, with a `UNIQUE(user_id)` constraint — resending a code
**replaces** the existing row (no multi-code history to manage).

### C. Anti-abuse limiting (resend throttle + attempts)

| Option | Mechanism | Advantages | Drawbacks |
| ------ | --------- | --------- | ------------- |
| A | Redis (already listed in `pyproject.toml` `dependencies`) | Fast, native TTL | **Redis is neither configured (`app/config/base.py` has no `redis_url`) nor deployed (constitution §26.2: "no service is running")** — the pip dependency is present but vestigial, no client is instantiated anywhere in `app/`. Using it would introduce an infrastructure dependency not planned by Agent 3 for a simple counter. |
| **B (selected)** | Columns on `auth_email_verifications` (`attempts`, `last_sent_at`) | No new infrastructure, SQL transaction already in place | No sharing across multiple API instances without a common store — not blocking, PostgreSQL is already the shared source of truth |

**Choice: option B** — consistent with "minimize dependencies" (constitution
§22). If Redis is ever deployed for other needs (BFF Tolaria cache, see §2.2.2
of `docs/tolaria_news/00_plan_general.md`), this throttle can migrate without an
API contract change.

### D. Confirmation link in the email

The code shown in clear text in the email can also be encoded as a clickable
link (`{frontend_base_url}/verify-email?email=...&code=...`) to avoid manual
entry.

**Risk analysis**:

- **Main risk — accidental consumption, not confidentiality.** Many enterprise
  security gateways (Microsoft Safe Links, Proofpoint, Mimecast…) and some mail
  clients **automatically pre-click** links in an email to scan them before the
  user opens it. If the link directly triggered verification via `GET`, the code
  would be consumed by the scanner before the user even clicks — a frequent
  failure mode of "magic link" flows with side effects on `GET`.
- **Leak via logs/history/`Referer`**: a code in a URL ends up in browser
  history, access logs, and could leak via the `Referer` header if the target
  page loads third-party resources. Impact bounded by the already-planned
  15-minute TTL + single use.
- **No need for a separate secret**: the email body contains the code in clear
  text anyway for manual entry — exposing it in a link too does not
  significantly worsen the risk, as long as the throttle (5 attempts, single
  use) protects against brute-force.

**Decision**:

- The link points to a **frontend page** for confirmation, never directly to an
  API route.
- The page pre-fills the code from the URL parameters but only calls `POST
  /api/v1/auth/signup/verify` after an **explicit click** by the user ("Confirm
  my account") — never on page load. This is a constraint for the frontend phase
  (Tamiyo Scroll), documented here so it isn't lost.
- The `POST /verify` endpoint remains `POST` only — no `GET` route with a side
  effect is introduced for "click to validate".
- New config field `frontend_base_url` (see Target configuration) to build the
  link.

Rules adopted:

- Code: 6 digits, expires after **15 minutes**.
- Stored hash: `sha256(code + user_id_bytes)` — a low-entropy OTP doesn't need
  Argon2 (unnecessary CPU cost on verification), protection comes from the
  throttle, not the hash.
- Max **5 verification attempts** per code; beyond that, the code is invalidated
  and a resend is required.
- Resend: **60-second** cooldown between two sends (`last_sent_at`).
- `POST /verify` and `POST /resend` respond indistinguishably whether the email
  exists or not **only for `/resend`** (generic 202); `/verify` must distinguish
  "invalid code" from "account already verified" to remain usable on the UI side
  — accepted as in the existing `/register`, which already reveals account
  existence via 409.

---

## Target architecture

```text
POST /api/v1/auth/signup
        |
        v
UserSignup (existing, extra=forbid) --> User(is_verified=False) --+
                                                                    |
                                          EmailVerification(code_hash, expires_at)
                                                                    |
                                                    EmailSender.send_verification_code()
                                                                    |
                                              SMTPEmailSender  |  ConsoleEmailSender
                                            (prod/staging)        (dev/test)

POST /api/v1/auth/signup/verify {email, code}
        |
        v
  checks hash + expiration + attempts
        |
   success --> User.is_verified=True, EmailVerification deleted, TokenPair
   failure --> 400 (invalid/expired) | 429 (too many attempts)

POST /api/v1/auth/signup/resend {email}
        |
        v
  if account exists, unverified, cooldown elapsed --> new code, upsert, send
  otherwise --> generic 202 (no information leak)
```

---

## Target configuration

New fields in `app/config/base.py` (`BaseAppSettings`):

| Variable | Type | Default | Description |
| -------- | ---- | ------ | ----------- |
| `smtp_host` | `str \| None` | `None` | SMTP relay host. Empty in dev/test → `ConsoleEmailSender`. |
| `smtp_port` | `int` | `587` | SMTP port (STARTTLS). |
| `smtp_username` | `str \| None` | `None` | SMTP identifier (optional depending on the relay). |
| `smtp_password` | `SecretStr \| None` | `None` | SMTP password — never logged (`SecretStr`). |
| `smtp_use_tls` | `bool` | `True` | STARTTLS. |
| `smtp_from_address` | `str` | `"barrins-identity@gmail.com"` | Sending address — must match `smtp_username` (Gmail constraint). |
| `verification_code_ttl_minutes` | `int` | `15` | Code validity duration. |
| `verification_max_attempts` | `int` | `5` | Attempts before forced invalidation. |
| `verification_resend_cooldown_seconds` | `int` | `60` | Minimum delay between two resends. |
| `frontend_base_url` | `str` | `"http://localhost:5173"` | Base to build the confirmation link in the email (`{frontend_base_url}/verify-email`). |

Added validation (same pattern as `secret_key_must_not_be_placeholder`):
`environment == "production"` and empty `smtp_host` → configuration error at
startup. Same for `frontend_base_url == "http://localhost:5173"` in production —
avoids sending confirmation links pointing to a development environment.

---

## Overview of changes

| Dimension | Current state | After implementation | Work required |
| --------- | ----------- | -------------------- | -------------- |
| Config | No SMTP fields | +10 fields on `BaseAppSettings` (including `frontend_base_url`) | `app/config/base.py` |
| ORM models | `User.is_verified` already exists, unused in practice | + `EmailVerification` (`auth_email_verifications`) | `app/models/email_verification.py` |
| Migration | 10 existing migrations | +1 migration (`auth_email_verifications`) | `alembic/versions/` |
| Schemas | `UserSignup` exists, not exposed | + `VerifyEmailRequest`, `ResendVerificationRequest` | `app/schemas/auth.py` |
| Services | No email sending in the project | `app/services/email/` (`EmailSender`, `SMTPEmailSender`, `ConsoleEmailSender`) | New service |
| Routes | `/auth/signup` not registered | `/auth/signup`, `/auth/signup/verify`, `/auth/signup/resend` | `app/api/v1/routers/auth.py` |
| Tests | `tests/test_auth.py` (158 cases, 90.70% coverage) | + signup/verify/resend cases, `EmailSender` mocks | Extension of the same file or new `test_signup.py` |

---

## Phase breakdown

| Phase | Title | Main files | Prerequisite |
| ----- | ----- | ------------------- | --------- |
| 1 | Configuration | `app/config/base.py` | — |
| 2 | `EmailVerification` ORM model | `app/models/email_verification.py` | Phase 1 |
| 3 | Alembic migration | `alembic/versions/` | Phase 2 |
| 4 | Pydantic schemas | `app/schemas/auth.py` | Phase 2 |
| 5 | Email service (Gmail SMTP + template with confirmation link) | `app/services/email/` | Phase 1 |
| 6 | Code utilities (hash, generation, throttle) | `app/core/security.py` | Phase 2 |
| 7 | signup/verify/resend routes | `app/api/v1/routers/auth.py` | Phases 3–6 |
| 8 | Tests | `tests/test_auth.py` or `tests/test_signup.py` | All |

---

## Open point to flag (out of backend scope) — confirmed

The high-fidelity design prototype (`Suivi Compétitif MTG.dc.html` / README
provided by the client) shows a login screen with a "Log in" / "Create account"
toggle but **contains no field for entering the verification code**. The
two-step flow described by the constitution (§13.3) assumes an intermediate
screen absent from the provided design.

→ Confirmed by the client: a **second screen** ("Verify your email") is required
on the Tamiyo Scroll side, in addition to the existing login/signup screen. This
screen must:

- allow manual entry of the 6-digit code (`POST /verify`);
- handle the `/verify-email?email=...&code=...` route for the link sent by
  email, pre-filling the code but requiring an explicit click before calling
  `POST /verify` (see Option D — never submit automatically on page load);
- offer a "Resend code" button (`POST /resend`), with 60s cooldown handling on
  the UI side.

This backend plan provides the complete API contract; the screen itself is a
separate frontend project, not to be forgotten when scoping Tamiyo Scroll (Agent
2).

---

## Implementation notes (2026-07-15)

- Files delivered: `app/models/email_verification.py`, `app/schemas/auth.py`
  (`SignupResponse`, `VerifyEmailRequest`, `ResendVerificationRequest`,
  `ResendVerificationResponse`), `app/services/email/` (`EmailSender`,
  `SMTPEmailSender`, `ConsoleEmailSender`, `get_email_sender`/`EmailSenderDep`),
  utilities `generate_verification_code`/`hash_verification_code`/
  `verify_verification_code` in `app/core/security.py`, routes `/auth/signup`,
  `/auth/signup/verify`, `/auth/signup/resend` in `app/api/v1/routers/auth.py`,
  migration `bc1059a4da27`.
- `get_email_sender` is exposed as an injectable FastAPI dependency
  (`EmailSenderDep`) rather than called directly — allows substitution in tests
  via `app.dependency_overrides`, consistent with `DatabaseSession`.
- Two pre-existing bugs unrelated to this feature were fixed along the way
  because they prevented any test execution (`except X, Y:` syntax inherited
  from Python 2, invalid in Python 3): `app/core/security.py`,
  `app/services/mtgjson/sets.py`, `app/api/v1/tolaria_routers/decklists.py`,
  `app/services/tolaria/db.py`, `app/services/tolaria/helpers.py` — separate
  commit `fix: parenthesize multi-exception except clauses`.
- Tests: 137 tests covering signup/verify/resend, production config, and the
  email service (see `tests/test_signup.py`, `tests/test_config.py`,
  `tests/test_email_service.py`). `mypy` and `ruff` pass without error on all
  modified/created files.
- **Known limitation of the validation environment**: this project targets
  Python 3.14 (not installable in the sandbox used for this implementation — the
  `python-build-standalone` repo is blocked by the network proxy). Tests were
  run under Python 3.13 with **local, uncommitted** `from __future__ import
  annotations` patches on files that rely on deferred annotation evaluation (PEP
  649, default in 3.14) — reverted before each commit, none appear in the final
  diff. Under this configuration, the `coverage` tool reproducibly under-counts
  FastAPI routes (`app/api/v1/routers/auth.py`, `app/dependencies/auth.py`),
  including on pre-existing code already documented at ~90% coverage — tests
  nonetheless all pass in direct execution (`pytest -q --no-cov`). To be re-run
  with `--cov` on a real Python 3.14 environment (CI) for a reliable coverage
  figure; do not trust the `coverage` percentage measured in this sandbox.

## Temporary workaround — single-step signup (2026-07-16)

The time available to configure an SMTP relay (dedicated Gmail account + app
password, see Gmail section above) before Tamiyo Scroll went live was
insufficient on the client side. Added a `REQUIRE_EMAIL_VERIFICATION` setting
(`app/config/base.py`, default `true`):

- `true` (behavior documented above, unchanged): `POST /auth/signup` creates an
  unverified account, sends a code, `SignupResponse.tokens` is `None` — the
  client must go through `POST /auth/signup/verify`.
- `false`: `POST /auth/signup` directly creates a **verified** account
  (`is_verified=True`), no `EmailVerification` row created, no email sent, and
  returns `SignupResponse.tokens` (access/refresh pair) — the user is logged in
  right at signup. The production constraint requiring
  `SMTP_HOST`/`FRONTEND_BASE_URL`
  (`_production_requires_real_smtp_and_frontend_url`) is itself disabled in this
  case: neither is ever read if no verification email is sent.

`SignupResponse` now carries `verification_required: bool` and
`tokens: TokenPair | None` — a stable contract on the client side regardless
of the server setting (the frontend doesn't need to know the value of
`REQUIRE_EMAIL_VERIFICATION` in advance; it branches on `verification_required`
in the response). `POST /auth/signup/verify` and `POST /auth/signup/resend` are
unchanged — an account already verified through this workaround can no longer
match `is_verified=False` anyway.

**To do once SMTP is configured**: switch `REQUIRE_EMAIL_VERIFICATION` back to
`true` (or remove it from `.env`, `true` is the default value) — no code change
required, only an environment variable.

Tests: `tests/test_signup.py::TestSignupWithVerificationDisabled` (3 cases),
`tests/test_config.py::TestBaseAppSettingsValidators::test_production_with_verification_disabled_does_not_require_smtp`.
