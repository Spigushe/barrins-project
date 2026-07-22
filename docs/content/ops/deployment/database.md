# Database Administration — PostgreSQL & pgAdmin

Operational guide for `ops/my-server/postgresql_pgadmin.yml`. Unlike
`backend.md`/`frontend.md`, this isn't an application deploy — it's an
infrastructure/admin tool, so it's not release-tagged and has no
staging/production split. Structured per Constitution §37 where it applies.

| | Detail |
| --- | --- |
| Playbook | `postgresql_pgadmin.yml` |
| URL | `https://pgadmin.barrins-codex.org` |
| PostgreSQL | Already installed natively by `setup-packages` (host bootstrap) — this playbook doesn't reinstall it, only makes it reachable from pgAdmin. |
| pgAdmin | Runs in a Docker container (`dpage/pgadmin4`), on `127.0.0.1:5050`, behind nginx/TLS. |
| Auto-updates | pgAdmin: weekly systemd timer that `docker pull`s + restarts. PostgreSQL (OS package): `unattended-upgrades`, enabled by this same playbook. |

## Why Docker for pgAdmin, not the apt package?

The official `pgadmin4-web` apt package pulls in Apache and an interactive
setup script whose non-interactive mode is known to be unreliable. The
official Docker image configures entirely through environment variables
(`PGADMIN_DEFAULT_EMAIL`/`PGADMIN_DEFAULT_PASSWORD`), needs no Apache, and
updates with a plain `docker pull` — hence the choice here.

## Preparation

**Server requirements** — `initial.yml` and `setup.yml` must already have
run (installs PostgreSQL, nginx, certbot).

**DNS** — an A record for `pgadmin.barrins-codex.org` pointing at the
server.

**pgAdmin admin password** — a local, git-ignored file (Constitution §34):

```bash
echo -n '<strong password>' > secrets/postgresql_pgadmin/admin_password.txt
chmod 600 secrets/postgresql_pgadmin/admin_password.txt
```

Unlike the "if available" backend `.env` files, this one is a hard
requirement — the playbook fails clearly if it's missing rather than
silently deploying without it, since pgAdmin cannot function without
admin credentials.

## Deployment

```bash
ansible-playbook postgresql_pgadmin.yml
```

The `pgadmin` role (see `ops/my-server/roles/pgadmin/README.md` for full
technical detail):

- installs Docker if absent;
- creates an isolated Docker network (`172.30.99.0/24` by default) so the
  pgAdmin container never shares the host's network namespace;
- updates `postgresql.conf`/`pg_hba.conf` so PostgreSQL accepts password
  auth from that Docker network only — never from the internet, since
  nothing binds Postgres to a public interface;
- deploys pgAdmin (`pgadmin4.service`) on `127.0.0.1:5050`;
- deploys its weekly auto-update timer;
- deploys the nginx vhost + TLS;
- enables `unattended-upgrades` for automatic OS/PostgreSQL patching.

## Mandatory manual step — create a PostgreSQL role

This playbook **deliberately does not** create a PostgreSQL user/password
(same "no secret generated silently" principle as backend `.env` files).
After the playbook runs:

```bash
ssh spigushe.org
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD '<strong password>';"
```

Use a password different from the pgAdmin login password above — these
are two unrelated credentials (one to log into the pgAdmin UI, the other
for pgAdmin to connect to PostgreSQL).

## Validation

1. Open `https://pgadmin.barrins-codex.org`, log in with
   `pgadmin_admin_email`/the password from `admin_password.txt`.
2. *Add New Server*:
   - **Host**: `host.docker.internal` — **not** `localhost` (which, from
     inside the container, means the container itself, not the host).
   - **Port**: `5432`
   - **Username**: `postgres` (or the role created above)
   - **Password**: the one set with `ALTER USER` above
3. Confirm the connection succeeds and databases are visible.

## Rollback

No release tag applies here (this isn't an application deploy). To roll
back a bad change, re-run the playbook after reverting whatever changed
(a role/template edit) — every task here is idempotent. There is no data
to roll back for pgAdmin itself (its own state lives in a Docker volume,
untouched by playbook re-runs); PostgreSQL data rollback is a separate
concern, see [`rollback.md`](rollback.md)'s database caveat.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `register-ssl` fails on "certbot certonly" | DNS not propagated, or port 80 unreachable. |
| pgAdmin shows "Unable to connect to server" when adding the Postgres server | `Host` set to `localhost` instead of `host.docker.internal`; or the manual `ALTER USER ... PASSWORD` step wasn't done; or PostgreSQL wasn't reloaded (`systemctl status postgresql`). |
| `docker network create` fails on a re-run | Another Docker network already occupies `172.30.99.0/24` — change `pga_docker_subnet`/`pga_docker_gateway_ip` in `postgresql_pgadmin.yml`. |
| pgAdmin container won't start | `journalctl -u pgadmin4 -n 50`; confirm Docker is running (`systemctl status docker`) and port `5050` is free. |
| Playbook fails before touching the server, "does not exist" | `secrets/postgresql_pgadmin/admin_password.txt` is missing — see "Preparation" above. |

## See also

- `ops/my-server/roles/pgadmin/README.md` — full role technical detail.
- [`../security/secrets.md`](../security/secrets.md) — the secrets policy
  this playbook follows.
