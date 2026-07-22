# pgadmin

Deploys [pgAdmin4](https://www.pgadmin.org/) (web/server mode) in a Docker
container, reverse-proxied by nginx with TLS, wired up to reach the
PostgreSQL server that `setup-packages` already installs on the host — plus
automatic updates for both.

pgAdmin runs in Docker (rather than the OS package) because pgAdmin4's own
apt-based web installer requires an interactive/unreliable setup script and
pulls in Apache alongside the nginx this repo already standardizes on.
Docker keeps it self-contained and trivially updatable.

## What it does

1. Installs Docker (`docker.io`) if missing, enables the daemon.
2. Creates an isolated Docker network (`pga_docker_network`, default
   `pgadmin_net`, subnet `pga_docker_subnet`/`172.30.99.0/24`) so the
   container never shares a network namespace with the host (no service
   inside it is bound to a public interface — same "only nginx faces the
   internet" model as every other role in this repo).
3. Creates a named Docker volume (`pga_volume_name`, default
   `pgadmin4_data`) mounted at `/var/lib/pgadmin` so pgAdmin's own users/
   saved-server list survive container recreation and image updates.
4. Finds the host's PostgreSQL config (`/etc/postgresql/<version>/main`) and:
   - adds the Docker network's gateway IP to `listen_addresses` (alongside
     `localhost`, which is left untouched);
   - appends a `pg_hba.conf` line allowing password (`scram-sha-256`) auth
     from that Docker subnet only — **not** from the internet, since nothing
     opens the port on a public interface and the subnet is a private
     Docker-only range.
   - restarts `postgresql` (via a handler, flushed before pgAdmin starts) if
     either file changed.
5. Templates the admin credentials to `/etc/pgadmin4/pgadmin4.env` (mode
   `0600`, root-owned) and a systemd unit (`pgadmin4.service`) that runs
   `docker run --rm --name pgadmin4 ...` in the foreground, bound to
   `127.0.0.1:<pga_port>` only, loading that file via `--env-file` (kept out
   of the command line/unit file so it doesn't show up in `ps aux` or a
   world-readable systemd unit) plus
   `--add-host=host.docker.internal:host-gateway` so the container can
   reach the host's Postgres. `Restart=always` handles crashes/reboots.
6. Templates `pgadmin4-update.service` + `pgadmin4-update.timer`: every
   Sunday (± up to 30 min, `RandomizedDelaySec`), pulls the latest
   `dpage/pgadmin4` image and restarts the service — pgAdmin's automatic
   update mechanism (a few seconds of downtime, acceptable for an admin
   tool).
7. Templates an nginx HTTPS vhost for `pga_server_name` that reverse-proxies
   to `127.0.0.1:<pga_port>` (`X-Scheme`/`Host`/`X-Real-IP` headers per
   [pgAdmin's documented reverse-proxy setup](https://www.pgadmin.org/docs/pgadmin4/latest/container_deployment.html)).
   Requires `register-ssl` to have run for the same domain first (same
   convention as every other HTTPS-serving role here).
8. Installs and enables `unattended-upgrades` for the whole host, with
   `Debian-Security` *and* the regular `<codename>-updates` origin enabled
   (appended via `Unattended-Upgrade::Origins-Pattern::`, so it doesn't
   clobber Debian's own defaults) — this is what keeps the OS-level
   PostgreSQL package (installed by `setup-packages`) automatically patched,
   including point releases, not just CVEs.

## Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `pga_server_name` | yes | — | Domain pgAdmin is served on, e.g. `pgadmin.barrins-codex.org`. |
| `pga_admin_email` | yes | — | pgAdmin login email (first admin user, created on first boot of the container). |
| `pga_admin_password` | yes | — | pgAdmin login password. Source it from a local, git-ignored file (Constitution §34 — see `postgresql_pgadmin.yml` and `secrets/README.md`), never hardcode or commit it. |
| `pga_port` | no | `5050` | Local port the container's web UI is published on (`127.0.0.1` only). |
| `pga_image_tag` | no | `latest` | `dpage/pgadmin4` tag to run/pull. |
| `pga_volume_name` | no | `pgadmin4_data` | Docker volume name for persistent pgAdmin state. |
| `pga_docker_network` | no | `pgadmin_net` | Docker network name. |
| `pga_docker_subnet` | no | `172.30.99.0/24` | Subnet for that network; must not collide with an existing Docker network on the host. |
| `pga_docker_gateway_ip` | no | `172.30.99.1` | First address of `pga_docker_subnet` (Docker's default gateway for a network it creates) — keep in sync if you change the subnet. |

## Requirements

- `setup-packages` must have run first (installs `nginx`, `certbot`,
  `postgresql`).
- `register-ssl` must have run for `pga_server_name` first (certificate
  files this role's nginx vhost references).
- Docker Engine ≥ 20.10 for `--add-host=host.docker.internal:host-gateway`
  support (true of `docker.io` on any current Debian release).

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
  it by hand after first login: Host `host.docker.internal`, Port `5432`,
  Username/password from the step above. (Not `localhost` — that resolves
  inside the pgAdmin container's own network namespace, not the host's.)

## Example

```yaml
- role: register-ssl
  tags: [pgadmin, certs]
  rs_server_name: pgadmin.barrins-codex.org

- role: pgadmin
  tags: [pgadmin, deploy]
  pga_server_name: pgadmin.barrins-codex.org
  pga_admin_email: admin@example.com
  pga_admin_password: "{{ lookup('file', playbook_dir + '/secrets/postgresql_pgadmin/admin_password.txt') }}"
```

See `postgresql_pgadmin.yml` for the full pattern, including the pre-flight
check that fails clearly if that local file doesn't exist yet.
