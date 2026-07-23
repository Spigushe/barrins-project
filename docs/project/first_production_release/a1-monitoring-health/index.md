# A1. Monitoring and `/health`

[← Back to project index](../index.md)

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
  checker polls `https://api.barrins-codex.org/health` and the frontend
  URLs, plus certificate-expiry alerting (§30). Rationale: monitoring
  hosted *on the same VPS it's watching* can't detect a full server
  outage — it needs to run somewhere else. This is an external account,
  not a new code dependency, so it doesn't trigger the §22
  dependency-approval process.
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
- [x] Sign up / configure a HetrixTools account and add monitors for both
      apps' staging/production URLs plus certificate-expiry alerting.
      Monitors are live and currently report `404` on `/health` for both
      staging and production — **expected**, since this branch (the
      `/health` route itself) hasn't been deployed yet. Should flip to
      `200` once B5 deploys this work.
- [x] Update the open-items table's monitoring row to reflect monitors
      configured (still pending a deploy to go green).

## Done statement

`GET /health` exists and returns `200`/`503` correctly; an external
uptime checker is actively polling both apps plus certificate expiry;
`operations/index.md` reflects both as implemented.

## UAT (manual, performed by the user)

- [ ] Hit `/health` locally and on `staging`; confirm
      `200 {"status": "ok"}`.
- [ ] Stop the local/staging DB and confirm `/health` returns `503`.
- [ ] Open the chosen uptime-checker's dashboard; confirm both
      `barrins_api` and `tamiyo_scroll` staging URLs are being polled and
      show "up," and a certificate-expiry check is configured.

## Non-regression tests

- Automated: `test_health_ok`, `test_health_db_down_returns_503` (new).
- Manual smoke: `GET /` still returns `301` to `/docs` — confirms the new
  route didn't disturb the existing redirect.
