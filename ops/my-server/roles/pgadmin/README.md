# pgadmin

Deploys [pgAdmin4](https://www.pgadmin.org/) (web/server mode) in a Docker
container, reverse-proxied by nginx with TLS, wired up to reach the
PostgreSQL server that `setup_packages` already installs on the host — plus
automatic updates for both.

pgAdmin runs in Docker (rather than the OS package) because pgAdmin4's own
apt-based web installer requires an interactive/unreliable setup script and
pulls in Apache alongside the nginx this repo already standardizes on.
Docker keeps it self-contained and trivially updatable.

## What it does

1. Installs Docker (`docker.io`) if missing, enables the daemon.
2. Creates an isolated Docker network (`pgadmin_docker_network`, default
   `pgadmin_net`, subnet `pgadmin_docker_subnet`/`172.30.99.0/24`) so the
   container never shares a network namespace with the host (no service
   inside it is bound to a public interface — same "only nginx faces the
   internet" model as every other role in this repo).
3. Creates a named Docker volume (`pgadmin_volume_name`, default
   `pgadmin4_data`) mounted at `/var/lib/pgadmin` so pgAdmin's own users/
   saved-server list survive container recreation and image updates.
4. Finds the host's PostgreSQL config (`/etc/postgresql/<version>/main`) and:
   - reads the currently active `listen_addresses` first, and only adds the
     Docker network's gateway IP to it (alongside `localhost`) **if nothing
     already covers that gateway** — in particular, an existing `'*'` is
     left untouched rather than narrowed. This matters: the application
     itself may depend on Postgres already listening broadly (e.g. to be
     reachable over the host's public interface for its own `DATABASE_URL`)
     — unconditionally overwriting `listen_addresses` to a Docker-only
     value once broke that;
   - appends a `pg_hba.conf` line allowing password (`scram-sha-256`) auth
     from that Docker subnet only — **not** from the internet, since nothing
     opens the port on a public interface and the subnet is a private
     Docker-only range.
   - restarts `postgresql` (via a handler, flushed before pgAdmin starts) if
     either file changed.
5. Templates the admin credentials to `/etc/pgadmin4/pgadmin4.env` (mode
   `0600`, root-owned) and a systemd unit (`pgadmin4.service`) that runs
   `docker run --rm --name pgadmin4 ...` in the foreground, attached to
   the isolated network above (so it can already reach Postgres at
   `pgadmin_docker_gateway_ip` directly — no `--add-host` trick needed;
   `host.docker.internal` isn't wired to anything in this container on
   purpose, since on Linux it would resolve to the default bridge's
   gateway, not this network's, and silently "work" toward the wrong
   address), bound to `127.0.0.1:<pgadmin_port>` only, loading
   credentials via `--env-file` (kept out of the command line/unit file
   so it doesn't show up in `ps aux` or a world-readable systemd unit).
   `Restart=always` handles crashes/reboots.
6. Templates `pgadmin4-update.service` + `pgadmin4-update.timer`: every
   Sunday (± up to 30 min, `RandomizedDelaySec`), pulls the latest
   `dpage/pgadmin4` image and restarts the service — pgAdmin's automatic
   update mechanism (a few seconds of downtime, acceptable for an admin
   tool).
7. Templates an nginx HTTPS vhost for `pgadmin_server_name` that reverse-proxies
   to `127.0.0.1:<pgadmin_port>` (`X-Scheme`/`Host`/`X-Real-IP` headers per
   [pgAdmin's documented reverse-proxy setup](https://www.pgadmin.org/docs/pgadmin4/latest/container_deployment.html)).
   Requires `register_ssl` to have run for the same domain first (same
   convention as every other HTTPS-serving role here).
8. Installs and enables `unattended-upgrades` for the whole host, with
   `Debian-Security` *and* the regular `<codename>-updates` origin enabled
   (appended via `Unattended-Upgrade::Origins-Pattern::`, so it doesn't
   clobber Debian's own defaults) — this is what keeps the OS-level
   PostgreSQL package (installed by `setup_packages`) automatically patched,
   including point releases, not just CVEs.

## Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `pgadmin_server_name` | yes | — | Domain pgAdmin is served on, e.g. `pgadmin.barrins-codex.org`. |
| `pgadmin_admin_email` | yes | — | pgAdmin login email (first admin user, created on first boot of the container). |
| `pgadmin_admin_password` | yes | — | pgAdmin login password. Source it from a local, git-ignored file (Constitution §34 — see `postgresql_pgadmin.yml` and `secrets/README.md`), never hardcode or commit it. |
| `pgadmin_port` | no | `5050` | Local port the container's web UI is published on (`127.0.0.1` only). |
| `pgadmin_image_tag` | no | `latest` | `dpage/pgadmin4` tag to run/pull. |
| `pgadmin_volume_name` | no | `pgadmin4_data` | Docker volume name for persistent pgAdmin state. |
| `pgadmin_docker_network` | no | `pgadmin_net` | Docker network name. |
| `pgadmin_docker_subnet` | no | `172.30.99.0/24` | Subnet for that network; must not collide with an existing Docker network on the host. |
| `pgadmin_docker_gateway_ip` | no | `172.30.99.1` | First address of `pgadmin_docker_subnet` (Docker's default gateway for a network it creates) — keep in sync if you change the subnet. |

## Requirements

- `setup_packages` must have run first (installs `nginx`, `certbot`,
  `postgresql`).
- `register_ssl` must have run for `pgadmin_server_name` first (certificate
  files this role's nginx vhost references).

## Not automated

- **No PostgreSQL role/password is created.** `pg_hba.conf` now accepts
  password auth from the Docker network, but you still need a Postgres role
  with a password to log in with — e.g.:

  ```bash
  sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD '<strong password>';"
  ```

  Never reuse the pgAdmin login password for this — they're unrelated
  credentials.
- **The Postgres server connection inside pgAdmin** isn't pre-created — add
  it by hand after first login: Host `{{ pgadmin_docker_gateway_ip }}`
  (`172.30.99.1` by default), Port `5432`, Username/password from the step
  above. **Not** `localhost` (resolves inside the pgAdmin container's own
  network namespace, not the host's) and **not** `host.docker.internal`
  either — this container isn't given that hostname at all (deliberately:
  on Linux, Docker's `host-gateway` special value resolves to the
  *default* bridge's gateway, typically `172.17.0.1`, not this isolated
  network's — so wiring it up would silently point at an address
  Postgres never listens on).

## Example

```yaml
- role: register_ssl
  tags: [pgadmin, certs]
  register_ssl_server_name: pgadmin.barrins-codex.org
  register_ssl_contact_name: admin@example.com

- role: pgadmin
  tags: [pgadmin, deploy]
  pgadmin_server_name: pgadmin.barrins-codex.org
  pgadmin_admin_email: admin@example.com
  pgadmin_admin_password: "{{ lookup('file', playbook_dir + '/secrets/postgresql_pgadmin/admin_password.txt') }}"
```

See `postgresql_pgadmin.yml` for the full pattern, including the pre-flight
check that fails clearly if that local file doesn't exist yet.
