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
| `tamiyo_scroll` | 5173 | `barrins_api` |
| `tolaria_news` | 5174 | `barrins_api` |
| `goblin_guide` | 5175 | `barrins_identity` |

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
