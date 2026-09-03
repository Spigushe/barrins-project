# `scripts/dev`

Local, ad-hoc developer tooling. Not used by CI or any deployment.

## `start-local.ps1`

Starts the ecosystem's **web services** locally, each bound to `0.0.0.0`
so another device on the same Wi-Fi / LAN can open them. Each service runs
in its own PowerShell window with live logs; `Ctrl+C` in a window stops
just that one.

The cross-device URLs (frontend → API, and each backend's CORS
allow-list) are injected as environment variables at launch — the
committed `.env` files are left untouched.

| service | port | talks to |
| --- | --- | --- |
| `barrins_api` | 8000 | remote dev DB (`146.59.146.57`) |
| `barrins_identity` | 8001 | remote dev DB (`146.59.146.57`) |
| `tamiyo_scroll` | 5173 | `barrins_api` (LAN IP) + `barrins_identity` (auth, via `localhost` — see below) |
| `tolaria_news` | 5174 | `barrins_api` |
| `goblin_guide` | 5175 | `barrins_identity` (via `localhost` — see below) |

Because Tamiyo Scroll (and, once Q-02 lands, Tolaria News) authenticate
straight against `barrins_identity`, the identity service's injected
`ALLOWED_ORIGINS` covers **all three** frontend ports, not just Goblin
Guide's.

### Auth is `localhost`-only

Both browser SPAs are pointed at `barrins_identity` on
`http://localhost:8001`, **not** the LAN IP. Cookie mode (ADR-18) keeps
the refresh token in an `HttpOnly` cookie that identity always sets
`Secure` (`apps/barrins_identity/app/core/cookies.py`), and a browser only
stores a `Secure` cookie over plain `http://` for `localhost` /
`127.0.0.1`. Over `http://<lan-ip>:8001` the cookie is silently dropped —
a reload then never restores the session, and Tamiyo Scroll and Goblin
Guide never share one.

Consequence: **reload/auto-login and cross-app SSO work only in this
machine's own browser.** Logging in from a phone or another laptop on the
Wi-Fi does not work (its `localhost` is itself). The tracker proper
(`barrins_api`, Bearer token, no cookie) stays reachable cross-device;
only the identity handshake is local. Making LAN-IP login work needs
either local HTTPS or a dev-only non-`Secure` cookie in `barrins_identity`
— neither is done here.

### `barrins_api`'s identity service account

`barrins_api` shows real names in the Teams UI (rosters, "flag a deck",
deck owners) by calling `barrins_identity`'s
`POST /api/v1/users/lookup`, which needs a **service-account token**. With
no credentials the directory is disabled and every name renders as
`Unknown member`.

When `api` is in the run set the launcher runs
`apps/barrins_identity/scripts/create_service_account.py` to mint (or
rotate) a stable local account — `client_id = sa_local_dev_directory`,
scope `identity:users:read` — straight in identity's DB, then injects
`IDENTITY_SERVICE_URL` / `IDENTITY_SERVICE_CLIENT_ID` /
`IDENTITY_SERVICE_CLIENT_SECRET` into the api window. It talks to the DB
directly, so identity's *service* need not be in the run set; if the DB
is unreachable the api still starts, just with the directory disabled and
a warning.

To run `uvicorn` standalone (no launcher), mint the account yourself and
put the three vars in `apps/barrins_api/.env`:

```powershell
cd apps\barrins_identity
uv run python scripts/create_service_account.py --client-id sa_local_dev_directory
```

The launcher rotates the secret on each run, so re-run that command if a
launcher start has happened since you last set `.env`.

Batch jobs (`barrins_scripture`, `karn_tablets`) are not services and are
not started here. No local Postgres is needed — the backend `.env` files
point at the remote dev database, so this machine only needs network
access to `146.59.146.57:5432`.

### Usage

```powershell
# everything, installing deps first
.\scripts\dev\start-local.ps1 -Install

# just the Goblin Guide + identity pair (T12), exercising the real
# email-verification screen (the 6-digit code prints to the identity log)
.\scripts\dev\start-local.ps1 -Only identity,goblin -EmailVerification

# see the plan without starting anything
.\scripts\dev\start-local.ps1 -List

# override the detected LAN IP
.\scripts\dev\start-local.ps1 -Ip 192.168.1.50

# stop everything (frees ports 8000/8001/5173/5174/5175)
.\scripts\dev\start-local.ps1 -Stop
```

### First run

Windows Firewall prompts once to allow `python`/`node` — tick **Private
networks** or the LAN URLs stay unreachable from other devices.

Backend health check: `http://<ip>:8001/health` → `{"status":"ok"}`.
