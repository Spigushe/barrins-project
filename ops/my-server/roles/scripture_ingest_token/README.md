# scripture_ingest_token

Reads the shared Barrin's Scripture ingestion secret from a local,
git-ignored file and exposes it as the `scripture_ingest_token` fact —
mirrors `github_token`'s pattern. `barrins_api.yml` and
`barrins_scripture.yml` both consume this one fact instead of requiring
the same value hand-copied into `secrets/barrins_api/*.env` **and**
`secrets/barrins_scripture/*.env` and kept in sync by hand (T8's original
2026-08-08 decision, superseded — see
`docs/project/v2.0.0-bump/t8-scripture-karn-playbooks/index.md`).

## What it does

1. Resolves `scripture_ingest_token_file` — the play's own value if set,
   else `<playbook_dir>/secrets/scripture/<deploy_env>_ingest_token.txt`
   (both consuming playbooks already define `deploy_env`) — keyed by
   environment so staging and production keep separate values, the same
   isolation `secrets/<app>/{staging,production}.env` already has. Only
   the *per-app* duplication (`barrins_api` vs. `barrins_scripture`) goes
   away, not the *per-environment* split.
2. Fails fast with a clear message if that file doesn't exist locally
   (Constitution §34 — never generated or committed silently).
3. Reads it and sets the `scripture_ingest_token` fact (`no_log: true`,
   never logged).

## Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `scripture_ingest_token_file` | no | `<playbook_dir>/secrets/scripture/<deploy_env>_ingest_token.txt` | Path to the local, git-ignored file holding the raw token. Requires `deploy_env` to be defined by the play unless overridden explicitly. |

## Requirements

None beyond the local file itself existing (see `secrets/README.md`) —
this role must run **before** whichever role deploys the consuming app's
`.env` (`fastapi_backend` for `barrins_api.yml`, `scripture_scraper` for
`barrins_scripture.yml`), since both playbooks inject
`scripture_ingest_token` into the already-deployed `.env` via a
`post_tasks` `ansible.builtin.lineinfile` step, not via the role's own
env-file templating.

## Example

```yaml
roles:
  - role: scripture_ingest_token

  - role: fastapi_backend
    tags: [backend]
    fastapi_backend_env_file: "{{ backend_env_file }}"
    # ...

post_tasks:
  - name: Inject the shared SCRIPTURE_INGEST_TOKEN into the deployed .env
    become: false
    no_log: true
    ansible.builtin.lineinfile:
      path: "{{ fastapi_backend_config.work_dir }}/.env"
      regexp: "^SCRIPTURE_INGEST_TOKEN="
      line: "SCRIPTURE_INGEST_TOKEN={{ scripture_ingest_token }}"
      owner: "{{ username }}"
      mode: "0600"
```
