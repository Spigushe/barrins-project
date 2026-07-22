# setup-base-user

Creates the operational Linux user that every other playbook/role runs as
(via `become_user`/`ansible_ssh_user`), with passwordless sudo, and
authorizes the control machine's SSH key for it. Part of first-time server
bootstrap only — not something you re-run per app.

## What it does

1. Creates the user `username` (`/bin/bash` shell) if it doesn't exist.
2. Adds a `NOPASSWD: ALL` sudoers entry for that user (validated with
   `visudo -cf` before writing).
3. Authorizes the **control machine's** local `~/.ssh/id_rsa.pub` as an
   `authorized_key` for that user, so subsequent Ansible runs can connect
   as `username` over key-based SSH instead of the initial
   password/provided-user login.

## Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `username` | yes | — | The operational Linux user to create (`spigushe` in every current playbook). |

## Requirements

- Run as/with a user that already has root (`become: yes`), typically the
  server's initial provisioning account (see `initial.yml`).
- Expects `~/.ssh/id_rsa.pub` to exist **on the control machine running
  Ansible**, not on the target host.

## Example

```yaml
# initial.yml
- hosts: all
  become: "yes"
  vars:
    username: spigushe
  roles:
    - role: setup-base-user
```
