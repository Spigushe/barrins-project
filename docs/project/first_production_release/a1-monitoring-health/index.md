# A1. Monitoring and `/health`

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api` | + external uptime-checker account (HetrixTools) |
| **Initial date** | 2026-07-23 | / |
| **Status** | ✅ Implemented, UAT fully confirmed | / |
| **Source** | Constitution §31.2 (health route), §30 (certificate-expiry monitoring) | / |
| **Dependency** | none | / |

---

## Context

Closes the open item already flagged in
`docs/content/ops/operations/index.md` and required by Constitution
§31.2: `barrins_api` has no `/health` route, and no monitoring/alerting
exists for the production VPS.

## Design

- Add a real `GET /health` route to `barrins_api` (no auth) returning
  `{"status": "ok"}` on success; includes a lightweight DB check (e.g.
  `SELECT 1` with a short timeout) and returns `503` if the database is
  unreachable.
- **Monitoring/alerting — decided: external.** An external free uptime
  checker polls `https://api.barrins-codex.org/health` (prod + staging),
  plus certificate-expiry alerting (§30). Rationale: monitoring hosted
  *on the same VPS it's watching* can't detect a full server outage —
  it needs to run somewhere else. This is an external account, not a
  new code dependency, so it doesn't trigger the §22 dependency-approval
  process.
  **Scope note**: the chosen free tier caps trackers at 2, which barely
  covers `barrins_api` prod + staging — `tamiyo_scroll` is not
  separately monitored. Accepted because both frontends already share
  this backend (see `barrins_api.yml`'s deploy warning), so a
  `barrins_api` outage is caught either way; what's missed is a
  frontend-only failure (static site down, backend still healthy).
  *Selection criterion*: free tier, with the least data exposure —
  private status page by default (no forced public incident page
  broadcasting our downtime history) and minimal account PII required at
  signup.
  **Provider decided: [HetrixTools](https://hetrixtools.com/).**
  *Alternative rejected*: self-hosted Uptime Kuma (Docker, reusing the
  Docker install already present for pgAdmin) — keeps everything
  in-repo/on-VPS but can't alert on total VPS failure and adds another
  service to maintain.

## Tasks

- [x] Implement `GET /health` in `barrins_api` with the DB-connectivity
      check (`app/api/health.py`, `app/schemas/responses_health.py`).
- [x] Write `test_health_ok` / `test_health_db_down_returns_503`
      (`tests/test_health.py`) — both pass; full suite (225 tests)
      green, coverage 98.15%.
- [x] Update `docs/content/ops/operations/index.md`'s open-items table:
      `/health` → implemented.
- [x] Select an external uptime-checker provider against the criterion
      above — **HetrixTools**.
- [x] Sign up / configure a HetrixTools account and add monitors for
      `barrins_api`'s staging/production URLs plus certificate-expiry
      alerting. Free tier caps trackers at 2, so `tamiyo_scroll` isn't
      separately monitored — see scope note in Design above. Monitors
      are live and currently report `404` on `/health` for both staging
      and production — **expected**, since this branch (the `/health`
      route itself) hasn't been deployed yet. Should flip to `200` once
      B5 deploys this work.
- [x] Update the open-items table's monitoring row to reflect monitors
      configured (still pending a deploy to go green).
- [x] Fix `/health` to return `503` when the database is entirely
      unreachable (connection refused/rejected), not just when a query
      fails after connecting. The original `except SQLAlchemyError`
      only catches failures that occur *after* a connection is
      established — SQLAlchemy doesn't wrap connection-establishment
      failures that way, so they surfaced as raw driver exceptions and
      an unhandled `500`. Found via the UAT step below (staging DB
      access blocked via `pg_hba.conf`). Now `except Exception`; added
      `test_health_db_unreachable_returns_503` alongside the existing
      mocked-`SQLAlchemyError` test.

## Done statement

`GET /health` exists and returns `200`/`503` correctly; an external
uptime checker is actively polling `barrins_api` (prod + staging) plus
certificate expiry; `operations/index.md` reflects both as
implemented.

## UAT (manual, performed by the user)

- [X] Hit `/health` locally and on `staging`; confirm
      `200 {"status": "ok"}`.
- [X] Stop the local/staging DB and confirm `/health` returns `503`.
      (Staging: initially returned `500` — an unhandled connection-level
      exception, see Tasks above. Fixed, redeployed, and re-tested by
      blocking `barrins_api_staging` via `pg_hba.conf`: now returns a
      clean `503 {"error":{"code":"SERVICE_UNAVAILABLE",...}}`.)
- [X] Open the chosen uptime-checker's dashboard; confirm `barrins_api`
      prod and staging URLs are being polled and show "up," and a
      certificate-expiry check is configured. (`tamiyo_scroll` not
      separately monitored — free tier only allows 2 trackers, see
      scope note in Design.)

## Non-regression tests

- Automated: `test_health_ok`, `test_health_db_down_returns_503`,
  `test_health_db_unreachable_returns_503` (new).
- Manual smoke: `GET /` still returns `301` to `/docs` — confirms the new
  route didn't disturb the existing redirect.
