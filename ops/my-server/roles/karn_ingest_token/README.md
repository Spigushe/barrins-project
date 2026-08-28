# karn_ingest_token

Reads the shared Karn Tablets ingestion secret from a local, git-ignored
file and exposes it as the `karn_ingest_token` fact — mirrors
`scripture_ingest_token`'s pattern. `barrins_api.yml` (which validates
the `X-Karn-Token` header on `POST /internal/karn/ingest`) and
`karn_tablets.yml` (which sends it) both consume this one fact instead of
requiring the same value hand-copied into `secrets/barrins_api/*.env`
**and** `secrets/karn_tablets/*.env` and kept in sync by hand.

## What it does

1. Resolves `karn_ingest_token_file` — the play's own value if set, else
   `<playbook_dir>/secrets/karn/<deploy_env>_ingest_token.txt` (both
   consuming playbooks already define `deploy_env`) — keyed by
   environment so staging and production keep separate values, the same
   isolation `secrets/<app>/{staging,production}.env` already has. Only
   the *per-app* duplication (`barrins_api` vs. `karn_tablets`) goes
   away, not the *per-environment* split.
2. Fails fast with a clear message if that file doesn't exist locally
   (Constitution §34 — never generated or committed silently).
3. Reads it and sets the `karn_ingest_token` fact (`no_log: true`, never
   logged).

## Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `karn_ingest_token_file` | no | `<playbook_dir>/secrets/karn/<deploy_env>_ingest_token.txt` | Path to the local, git-ignored file holding the raw token. Requires `deploy_env` to be defined by the play unless overridden explicitly. |

## Requirements

None beyond the local file itself existing (see `secrets/README.md`) —
this role must run **before** whichever role deploys the consuming app's
`.env` (`fastapi_backend` for `barrins_api.yml`, `karn_tablets` for
`karn_tablets.yml`), since both playbooks inject `karn_ingest_token` into
the already-deployed `.env` via a `post_tasks`
`ansible.builtin.lineinfile` step, not via the role's own env-file
templating.

## Example

```yaml
roles:
  - role: karn_ingest_token

  - role: fastapi_backend
    tags: [backend]
    fastapi_backend_env_file: "{{ backend_env_file }}"
    # ...

post_tasks:
  - name: Inject the shared KARN_INGEST_TOKEN into the deployed .env
    become: false
    no_log: true
    ansible.builtin.lineinfile:
      path: "{{ fastapi_backend_config.work_dir }}/.env"
      regexp: "^KARN_INGEST_TOKEN="
      line: "KARN_INGEST_TOKEN={{ karn_ingest_token }}"
      owner: "{{ username }}"
      mode: "0600"
```
