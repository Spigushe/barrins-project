# A3. Moxfield deck-import feature

[← Back to project index](../index.md)

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

## Design

Backend-only, per §4.1 ("backend owns business logic") and §41's
principle that external data sources must be abstracted.

- New infrastructure client:
  `apps/barrins_api/app/infrastructure/external_services/moxfield_client.py`
  — wraps HTTP calls to Moxfield, attaches the User-Agent from a new
  `MOXFIELD_USER_AGENT` env var, enforces the 1 req/sec limit with a
  stdlib-only async gate (`asyncio` + a monotonic-clock check — no new
  dependency; a library like `aiolimiter` would need §22 approval for
  something this simple).
  *Caveat*: this in-process limiter only coordinates within a single
  Uvicorn worker process — fine for the current single-worker systemd
  deployment; would need a shared limiter (Redis/Postgres-backed) if
  `barrins_api` ever runs multiple workers (not needed now, §39).
- New domain service
  (`app/domain/services/moxfield_import_service.py`) that fetches a deck
  via the client and maps it into the existing personal-deck/decklist
  schema.
- New BFF route:
  `POST /api/v1/tamiyo-scroll/personal-decks/import-moxfield` — request
  `{moxfield_url: str}`, response reuses `PersonalDeckResponse`. Auth
  required. Errors: `400` invalid/non-Moxfield URL, `404` deck not found
  upstream, `502`/`503` upstream failure, `429` if the local rate limiter
  is saturated.
- Secrets: add `MOXFIELD_USER_AGENT` to `apps/barrins_api/.env.example`
  (placeholder only) and to the vaulted
  `ops/my-server/secrets/barrins_api/{production,staging}.env(.example)`
  templates. **The real value goes directly into the local git-ignored
  `.env`/vault file at implementation time — never pasted into chat, a
  commit, or a PR description.**
- Frontend: a small "Import from Moxfield" URL field (placement decided
  alongside the A5 combobox rework) that calls the new BFF route only —
  the frontend never talks to Moxfield directly and never sees the
  secret.

## Tasks

- [ ] Implement `moxfield_client.py` with the rate limiter.
- [ ] Implement `moxfield_import_service.py` mapping logic.
- [ ] Add the BFF route with documented error cases.
- [ ] Add `MOXFIELD_USER_AGENT` to `.env.example` + vaulted secret
      templates (placeholders only).
- [ ] Add the frontend "Import from Moxfield" field.
- [ ] Provide the real credential locally at implementation time (never
      committed).

## Done statement

Import-by-URL endpoint implemented and rate-limited to ≤1 req/s;
`MOXFIELD_USER_AGENT` stored as a secret, never reaching the frontend; UI
field wired to the endpoint; documented error cases handled.

## UAT (manual)

- [ ] Paste a real public Moxfield deck URL into the new field on
      `staging`; confirm a personal deck is created with the correct
      cards.
- [ ] Paste an invalid/non-Moxfield URL; confirm a clear `400` surfaces
      in the UI instead of a silent failure.
- [ ] Trigger two imports back-to-back; confirm via server logs/timing
      they are spaced ≥1 second apart.
- [ ] Inspect the frontend network tab during an import; confirm no
      Moxfield User-Agent or credential ever appears in a request the
      browser makes (only the internal BFF call is visible).

## Non-regression tests

- Automated: new tests for `moxfield_client`'s rate limiter (mocked
  clock) and the import route (mocked upstream HTTP response) — net-new.
- Manual: confirm the existing "create an empty personal deck" flow
  (whichever form it takes after A5) still works unaffected by the new
  import path.
