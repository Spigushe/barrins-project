# create-ssh-key

Generates a dedicated SSH keypair on the server (`~/.ssh/id_rsa` for
`username`). Run once during initial provisioning.

## What it does

1. Generates an SSH keypair at `~/.ssh/id_rsa` if one doesn't already
   exist (`openssh_keypair` is idempotent — a second run is a no-op).
2. Registers the result as the `public_key` fact, in case a caller wants
   to consume `public_key.public_key` in a later task (nothing in this
   repo currently does).

## Variables

None.

## Requirements/notes

- Currently generates a key that isn't consumed by any deploy role in
  this repo: `fastapi-backend` and `react-frontend` both authenticate
  their `git clone` over HTTPS with a GitHub Personal Access Token
  instead (see the root README's "GitHub Token" section and each role's
  own README).
- Kept around for the SSH-based alternative: if you'd rather clone over
  SSH than manage a token, register this key as a read-only GitHub
  **Deploy Key** on the target repo — see the root README's "GitHub
  Deploy Key" section for the exact steps (`ssh` in, `cat
  ~/.ssh/id_rsa.pub`, add it under Settings > Deploy Keys).

## Example

```yaml
# setup.yml
- hosts: all
  vars:
    username: spigushe
  roles:
    - role: create-ssh-key
```
