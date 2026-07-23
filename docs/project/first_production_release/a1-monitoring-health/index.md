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
  signup. Final vendor pick (e.g. UptimeRobot, Freshping) happens at
  implementation time by checking current privacy terms against this
  criterion.
  *Alternative rejected*: self-hosted Uptime Kuma (Docker, reusing the
  Docker install already present for pgAdmin) — keeps everything
  in-repo/on-VPS but can't alert on total VPS failure and adds another
  service to maintain.

## Tasks

- [ ] Implement `GET /health` in `barrins_api` with the DB-connectivity
      check.
- [ ] Write `test_health_ok` / `test_health_db_down_returns_503`.
- [ ] Select an external uptime-checker provider against the criterion
      above.
- [ ] Configure monitors for both apps' staging/production URLs plus
      certificate-expiry alerting.
- [ ] Update `docs/content/ops/operations/index.md`'s open-items table:
      `/health` → implemented; monitoring → implemented (external
      checker).

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
