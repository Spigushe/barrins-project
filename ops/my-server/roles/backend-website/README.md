# backend-website

nginx HTTPS vhost that serves a static build from `dist/` and
reverse-proxies everything else to a backend process listening on
`127.0.0.1:<port>`. Pairs with `fastapi-backend` (or any process bound to
localhost) to expose it publicly over HTTPS. If the domain has no static
frontend of its own (pure API), that's fine — `dist/` can simply not
exist, and every request falls through to the proxy.

## What it does

1. Templates the HTTPS vhost to
   `/etc/nginx/sites-enabled/<bw_server_name>.https.conf`:
   - optional redirect vhost for `bw_alternate_server_name` (e.g. a `www.`
     domain) straight to the primary domain,
   - `root <site_root>/dist` with `try_files $uri @backend`,
   - `@backend` proxies to `http://127.0.0.1:<bw_port>` with the usual
     `X-Forwarded-*`/`X-Real-IP` headers.
2. Reloads nginx.

## Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `bw_server_name` | yes | — | Public domain for this vhost. Certificate must already exist (run `register-ssl` first). |
| `bw_port` | yes | — | Local port the backend process listens on (`127.0.0.1:<port>`). |
| `bw_alternate_server_name` | no | `False` | Extra domain (e.g. `www.<domain>`) that 301-redirects to `bw_server_name`. Needs its own `register-ssl` call/certificate. |
| `bw_is_websocket` | no | `False` | Accepted for forward-compatibility but **not yet wired into the nginx template** — the `@backend` location has no `Upgrade`/`Connection` headers today. Add them to `templates/https.conf.j2` before relying on this flag for a websocket backend. |

Internally, `site_root` resolves to `/home/{{username}}/projects/{{bw_server_name}}` — the same convention every other role uses, so it lines up with `fastapi-backend`'s `app_root` when both target the same `fb_server_name`/`bw_server_name`.

## Requirements

- `register-ssl` must have run for `bw_server_name` (and
  `bw_alternate_server_name`, if set).
- A backend process actually listening on `127.0.0.1:<bw_port>` — e.g.
  `fastapi-backend` configured with the same `fb_port`.

## Example

Paired with `fastapi-backend` on the same domain/port:

```yaml
- role: fastapi-backend
  tags: [backend]
  fb_repo: my-org/my-api
  fb_server_name: my-api.barrins-codex.org
  fb_port: 8012
  fb_entrypoint: "my_api.main:app"

- role: backend-website
  tags: [backend]
  bw_server_name: my-api.barrins-codex.org
  bw_port: 8012
```
