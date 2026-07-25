# A3. Moxfield deck-import feature

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` | backend only, frontend field delivered separately |
| **Initial date** | 2026-07-23 | / |
| **Status** | ✅ Implemented, UAT fully confirmed | includes 1 bug found/fixed during manual testing |
| **Source** | User-supplied requirement | confirmed against a real Postman collection (endpoint/auth) |
| **Dependency** | none | frontend wiring delivered by A5 (deferred here, already built there) |

---

## Context

**Scope**: import a personal deck into Tamiyo Scroll from a public
Moxfield deck URL (not commander/card-data enrichment).

**Constraints** (from credentials the user holds — never pasted into any
repo file, doc, commit, or chat message; handled exactly like
`SECRET_KEY`/`SMTP_PASSWORD` today, Constitution §34):

- Moxfield requires a specific **User-Agent** header value, treated as a
  secret credential — must never reach the frontend client and must never
  appear in a public repo.
- Hard rate limit: **no more than 1 request/second** to Moxfield.

**Discovered while starting this item**: a placeholder route already
existed — `POST .../personal-decks/{deck_id}/versions/import-moxfield`
in `app/api/tamiyo_scroll/personal_decks.py` (`import_moxfield_placeholder`),
which just stored a fixed string mentioning the URL. The real work was
replacing that placeholder body, not adding a new route. The user also
supplied a Postman collection confirming the exact endpoint/auth: `GET
https://api2.moxfield.com/v2/decks/all/{publicId}` needs only a
Moxfield-assigned `User-Agent` header, no bearer token, for public decks.

## Design

Backend-only, per §4.1 ("backend owns business logic") and §41's
principle that external data sources must be abstracted. Structure
follows this repo's actual conventions (`app/services/<name>/` with a
Protocol + concrete implementations + factory, mirroring
`app/services/email/`) rather than the `app/domain/`/`app/infrastructure/`
layout an earlier draft of this plan assumed — that layout doesn't exist
in this codebase.

- `app/services/moxfield/base.py` — `MoxfieldClient` Protocol
  (`async def fetch_decklist(deck_url: str) -> str`).
- `app/services/moxfield/http_client.py` — `HttpxMoxfieldClient`: parses
  the deck's public id out of the URL, enforces the 1 req/s cap via a
  **module-level** `asyncio.Lock` + last-call timestamp (module-level,
  not per-instance, so the cap holds regardless of how many client
  instances get created per request), calls the endpoint above, and
  formats the response's `commanders`/`companions`/`mainboard` boards
  into the same free-text, one-card-per-line format
  `TSPersonalDecklistVersion.content` already uses for manual decklists
  (there's no structured per-card entry model in this codebase — content
  is a text blob).
  *Verified live* against a real deck URL supplied by the user, with
  their real credential — the response shape matched on the first try.
  *Caveat*: the rate limiter only coordinates within a single process —
  fine for the current single-worker deployment; would need a shared
  limiter (Redis/Postgres-backed) if `barrins_api` ever runs multiple
  workers (not needed now, §39).
- `app/services/moxfield/console_client.py` — `ConsoleMoxfieldClient`,
  a dev/test stub returning a fixed sample deck, mirroring
  `ConsoleEmailSender`. **Difference from the email pattern**: this stub
  must never be reachable in production — returning a fake deck instead
  of failing would be a silent correctness bug (the user would think
  their real deck imported), unlike logging-instead-of-emailing which is
  a safe production-off-switch. `get_moxfield_client()` raises
  `ServiceUnavailableError` (503) in production when unconfigured,
  rather than falling back to the stub.
- `app/services/moxfield/__init__.py` — `get_moxfield_client()` factory +
  `MoxfieldClientDep`, selecting `HttpxMoxfieldClient` when
  `MOXFIELD_USER_AGENT` is set, else `ConsoleMoxfieldClient` (dev/test
  only) or a 503 (production).
- `app/config/base.py` — new `moxfield_user_agent: SecretStr | None`
  setting.
- Existing route `personal_decks.py`'s `import_moxfield_placeholder`
  renamed to `import_moxfield`, now calls `moxfield.fetch_decklist(...)`
  via the injected `MoxfieldClientDep` instead of building a placeholder
  string. No new route, no new request/response schema needed
  (`MoxfieldImportRequest`/`ResponseDecklistVersion` already existed).
- Secrets: `MOXFIELD_USER_AGENT` added to `apps/barrins_api/.env.example`
  and to `ops/my-server/secrets/barrins_api/{production,staging}.env.example`
  (placeholders only — the real value went directly into the user's
  local git-ignored `.env`, never pasted into chat/commit).
- Frontend: **not yet done** — the "Import from Moxfield" UI field is
  deferred to A5, since both touch the same personal-deck area of
  `AppShell.tsx`/its successor and the plan already scoped their layout
  to be decided together.

## Tasks

- [x] Add `moxfield_user_agent` setting (`app/config/base.py`).
- [x] Implement `app/services/moxfield/` (base, http_client,
      console_client, `__init__` factory).
- [x] Replace the placeholder body in `personal_decks.py`'s
      `import_moxfield` route with a real `moxfield.fetch_decklist(...)`
      call.
- [x] Add `MOXFIELD_USER_AGENT` to `.env.example` + vaulted secret
      templates (placeholders only).
- [x] Update `tests/tamiyo_scroll/test_personal_decks.py`'s placeholder
      test to override `get_moxfield_client` with a fake and assert on
      real content.
- [x] New `tests/test_moxfield_client.py`: URL parsing, board formatting,
      404/upstream-error/network-error mapping, rate limiter (via
      module-reference substitution, not in-place patching of the shared
      `time`/`asyncio` modules — see the comment in that test for why),
      factory selection (real/stub/production-503).
- [x] Full backend suite green: 237/237 tests, 98.21% coverage,
      `ruff`/`ty` clean.
- [x] Live-verified against a real Moxfield deck URL with the user's real
      credential — worked on the first try, including correct UTF-8
      handling of accented card names.
- [x] Frontend "Import from Moxfield" field — deferred to A5, delivered
      and UAT-confirmed there.

## Done statement

Import-by-URL endpoint implemented and rate-limited to ≤1 req/s;
`MOXFIELD_USER_AGENT` stored as a secret, never reaching the frontend;
documented error cases handled; verified against the real API. Frontend
wiring is intentionally out of scope here (→ A5).

## UAT (manual)

- [x] Paste a real public Moxfield deck URL directly against the
      endpoint; confirm the created version's content lists the correct
      cards. *(Done during implementation, via a direct script call —
      not yet through the Tamiyo Scroll UI, since that field doesn't
      exist until A5.)*
- [X] Once A5 adds the UI field: paste a real Moxfield URL there on
      `staging`; confirm a personal deck version is created with the
      correct cards.
- [X] Paste an invalid/non-Moxfield URL; confirm a clear `400` surfaces
      instead of a silent failure. *(Backend already returns a clear
      `400`. Bug found on retest: `PersonalDecklistImportSection.tsx`'s
      `handleImport`/`handleSaveRaw` never caught the mutation's
      rejection, so the error silently vanished in the browser instead
      of reaching the user — same missing-try/catch pattern as
      `LoginPage`/`VerifyEmailPage` already guard against. Fixed: both
      handlers now catch `ApiError` and render the message inline,
      mirroring the login form. Confirmed on retest — staging now shows
      "Not a Moxfield deck URL: 'a'" inline under the field.)*
- [X] Trigger two imports back-to-back; confirm via server logs/timing
      they are spaced ≥1 second apart.
- [X] Once the UI field exists: inspect the frontend network tab during
      an import; confirm no Moxfield User-Agent or credential ever
      appears in a request the browser makes (only the internal BFF call
      is visible).

## Non-regression tests

- Automated: `tests/test_moxfield_client.py` (net-new, 12 tests) — URL
  parsing, formatting, error mapping, rate limiter, factory selection.
- Automated: updated `test_moxfield_import_creates_version_from_client`
  in `test_personal_decks.py` (was
  `test_moxfield_import_creates_placeholder_content`) — same test slot,
  now asserting real behavior instead of the old placeholder string.
- Manual: confirm the existing "create an empty personal deck" flow
  still works unaffected by the new import path (unchanged code path).
