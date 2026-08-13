# mtgjson_import_scheduler

Daily systemd timer that calls `barrins_api`'s own
`POST /api/v1/mtgjson/import` route (S8) at 04:00 UTC. Companion to
`fastapi_backend`, not a standalone service — it does no git clone or
dependency install of its own, only a systemd `.service`/`.timer` pair
that curls the backend `fastapi_backend` already deployed, into the same
`barrins_api.yml` play.

## Step 0 answers (`docs/content/ops/deployment/new-service-checklist.md`)

1. **Trigger**: a systemd timer calling an **existing on-demand admin
   route** (`POST /mtgjson/import`, admin-gated since S8) — the checklist
   explicitly calls out combining both, and S8 already built the
   on-demand half.
2. **HTTP surface**: none of its own. It calls the already-provisioned
   `fastapi_backend`/`backend_website` surface over `127.0.0.1` directly
   (bypassing nginx/TLS entirely — this is host-local traffic, not a
   public request) — so this role has no `register_ssl`/DNS/nginx steps.
3. **Validation**: `systemctl status <app_name>.service` /
   `journalctl -u <app_name>.service -n 50` for the timer-driven run
   itself, plus the pre-existing `GET /api/v1/mtgjson/status` route's
   `last_imported_at` as an independent, application-level signal.
4. **Rollback**: no artifact of its own. It writes into `barrins_api`'s
   own `mj_sets`/`mj_cards` tables via the same idempotent upsert
   `POST /mtgjson/import` already uses manually — that data's rollback
   story belongs to `barrins_api`/`rollback.md`, not to this role.
5. **Data ownership**: none. No new database, no new backup/retention
   story — reuses `barrins_api`'s own tables and its existing
   `postgres_backup` coverage.
6. **Release-tagged?** N/A — this role deploys no code of its own. It
   always calls whichever version of `barrins_api` is currently running
   (production release tag or staging branch, whatever `fastapi_backend`
   most recently deployed), so it has nothing to pin or roll back
   independently.

## What it does

1. Templates a oneshot systemd service
   (`/etc/systemd/system/<mtgjson_import_scheduler_app_name>.service`)
   that runs, as whichever user systemd services run as by default
   (root — this unit makes no filesystem changes of its own):

   ```bash
   curl --fail-with-body -sS -X POST \
     http://127.0.0.1:<mtgjson_import_scheduler_backend_port>/api/v1/mtgjson/import \
     -H "X-MTGJSON-Import-Token: ${MTGJSON_IMPORT_TOKEN}"
   ```

   `MTGJSON_IMPORT_TOKEN` is loaded via `EnvironmentFile=`, pointed at
   `barrins_api`'s own already-deployed `.env`
   (`mtgjson_import_scheduler_env_file`) — **not** a second, separately
   injected secret file. Unlike `SCRIPTURE_INGEST_TOKEN` (shared between
   two different playbooks via the `scripture_ingest_token` role), only
   `barrins_api.yml` ever needs this value, so reading it back out of the
   one `.env` file that already has it avoids an unneeded cross-playbook
   abstraction.
2. Templates a daily timer
   (`/etc/systemd/system/<mtgjson_import_scheduler_app_name>.timer`),
   default `04:00:00 UTC` ± up to 30 min `RandomizedDelaySec`,
   `Persistent=true` so a missed run (host was off) catches up on next
   boot. `OnCalendar` carries an explicit `UTC` suffix rather than
   assuming the host's system clock is itself set to UTC, unlike
   `postgres_backup`/`scripture_scraper`'s bare local-time spec.
3. Enables and starts the timer (`daemon_reload: true`).

## Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `mtgjson_import_scheduler_app_name` | yes | — | systemd unit name (both `.service` and `.timer`), e.g. `api-mtgjson-import`. |
| `mtgjson_import_scheduler_backend_service_name` | yes | — | The `fastapi_backend` systemd unit name to order after/require (e.g. `api`) — ensures the API is up before this unit curls it. |
| `mtgjson_import_scheduler_backend_port` | yes | — | Local port the backend's `uvicorn` binds to — same value passed to `fastapi_backend_port`. |
| `mtgjson_import_scheduler_env_file` | yes | — | Path to the backend's already-deployed `.env` (e.g. `<fastapi_backend work_dir>/.env`) — read via `EnvironmentFile=` for `MTGJSON_IMPORT_TOKEN`. |
| `mtgjson_import_scheduler_hour` | no | `4` | Hour (0-23, UTC) the daily timer fires. |

## Requirements

- `fastapi_backend` must already have deployed `barrins_api` with
  `MTGJSON_IMPORT_TOKEN` set in its `.env` (see
  `secrets/barrins_api/production.env.example`) — this role's first task
  greps the deployed `.env` for that key and fails the play immediately,
  with a clear message, if it's missing (never silently enables a timer
  that would just 401 forever).
- Must run **after** `fastapi_backend` in the play (needs
  `mtgjson_import_scheduler_env_file` to already exist on the server).

## Example

```yaml
- role: fastapi_backend
  tags: [backend]
  # ...

- role: mtgjson_import_scheduler
  tags: [backend]
  when: deploy_env == 'production'
  mtgjson_import_scheduler_app_name: "api-mtgjson-import"
  mtgjson_import_scheduler_backend_service_name: "api"
  mtgjson_import_scheduler_backend_port: "{{ backend_port }}"
  mtgjson_import_scheduler_env_file: "{{ backend_work_dir }}/.env"
  mtgjson_import_scheduler_hour: 4
```

See `barrins_api.yml` for how it's actually wired in (production only —
staging is a side-by-side preview instance that doesn't need its own
independent daily refresh).
