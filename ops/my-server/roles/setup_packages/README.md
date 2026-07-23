# setup_packages

Base OS package installation and baseline nginx state for a freshly
bootstrapped Debian server. Run once during initial provisioning, before
any app-specific playbook — every app role (`register_ssl`,
`fastapi_backend`, `react_frontend`, ...) assumes `nginx`/`certbot`/build
toolchain packages are already present.

## What it does

1. `apt update` + full upgrade of installed packages.
2. Installs baseline packages: `gcc`, `git`, `nginx`, `certbot`,
   `postgresql`, `postgresql-client`, `libpq-dev`, `python3-psycopg2`,
   `acl`, `python3-certbot-nginx`, `python3-venv`, `python3-dev`, `curl`,
   `make`, `rsync`.
3. Removes nginx's default `sites-enabled/default` site (so it doesn't
   catch requests meant for one of the app vhosts).
4. Reloads nginx.

## Variables

None required by this role directly, but it must run with `become: yes`
against the whole host (see `setup.yml`).

## Requirements

- A Debian host reachable over SSH as a user with sudo (normally
  `username` from `setup_base_user`, run right after it in `setup.yml`).
- Installs PostgreSQL unconditionally — if a future host never needs a
  local database, trim that from the package list rather than working
  around it per-app.

## Example

```yaml
# setup.yml
- hosts: all
  become: true
  vars:
    username: spigushe
  roles:
    - role: setup_packages
```
