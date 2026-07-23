# Security

- [Secrets Management](secrets.md) — what's never in git, how that's
  enforced, and the deliberate `github_token` exception.
- [TLS](#tls) and [CORS](secrets.md#cors-and-network-boundaries) below.

## TLS

Constitution §30: every public service must be HTTPS, with automatic
certificate renewal and no application-level changes required. The
`register_ssl` role (Let's Encrypt via `certbot`) issues certificates;
renewal is handled by certbot's own systemd timer/cron job installed with
the Debian package, not by Ansible — see
`ops/my-server/roles/register_ssl/README.md`.

## Reverse proxy

nginx terminates TLS and reverse-proxies to each backend's local port
(`127.0.0.1:<port>`) — see the `backend_website` role. Security headers
(HSTS, `X-Content-Type-Options`, `X-Frame-Options`) recommended by
Constitution §29.1 are **not yet templated** into the nginx vhosts this
project generates — open item, not currently implemented.

## Authentication and authorization

Owned by the application (`barrins_api`), not this infrastructure layer —
see the Constitution §§13, 23.2 and the application's own documentation
under `docs/content/back/barrins_api/`.
