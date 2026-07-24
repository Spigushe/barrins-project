# Docs Site Deployment

Operational guide for `ops/my-server/docs.yml`. Structured per
Constitution §37.2. Self-hosted on this repo's own VPS rather than
GitHub Pages — see B2 in the project tracking docs
(`docs/project/first_production_release/b2-docs-deploy/`, not part of
this built site — see that directory's own note on why) for the
decision record.

| | Detail |
| --- | --- |
| Playbook | `docs.yml` |
| Production domain | `docs.barrins-codex.org` |
| Staging domain | `docs-staging.barrins-codex.org` |
| Source | latest GitHub release tag (or `-e docs_site_release_tag=<tag>`) |
| Serves | `docs/`'s `mkdocs build --strict` output, as a plain static site |

All commands below run from `ops/my-server/`.

## Preparation

**Server requirements** — `initial.yml`/`setup.yml` must already have run.

**DNS** — an A record for the target domain pointing at the server (both
`docs.barrins-codex.org` and `docs-staging.barrins-codex.org` need one;
neither exists yet as of this writing).

**GitHub token** — a local, git-ignored `secrets/github/token.txt` (see
`secrets/README.md`) — the same shared token every other playbook that
clones a private repo uses.

**Release** (production only) — this monorepo needs at least one GitHub
Release published (ADR-2 in
[`../architecture/decisions.md`](../architecture/decisions.md)).

## Deployment

```bash
# Staging first
ansible-playbook docs.yml -e deploy_env=staging
# preview a specific branch instead of the staging default:
ansible-playbook docs.yml -e deploy_env=staging -e docs_site_git_branch=my-feature

# Production, once staging is verified — deploys the latest release tag
ansible-playbook docs.yml
```

This is a **snapshot deploy, not a live-updating site**: it builds and
serves whatever the resolved ref pointed to at deploy time. Later commits
on that branch/tag aren't reflected until the playbook runs again —
nothing here watches for changes (unlike `mkdocs serve`'s local dev
hot-reload, which isn't used in production).

## Validation

- Open the deployed domain in a browser; confirm the docs site loads and
  a deep link (e.g. a nested page) resolves directly, not just the home
  page — mkdocs' "pretty URL" pages are real `<page>/index.html` files on
  disk (`try_files $uri $uri/ =404;`), so this should just work with no
  SPA-style rewrite involved.
- Spot-check that the content matches the branch/tag actually requested
  (e.g. a page you know changed recently).

## Rollback

See [`rollback.md`](rollback.md) for the full procedure. Short version:

```bash
ansible-playbook docs.yml -e docs_site_release_tag=<previous-tag>
```

Simplest rollback in the whole deployment set: no database, no running
service — just a rebuild from the older tag.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Playbook fails before touching the server, "repo has no GitHub release yet" | Cut a release on GitHub, or pin one with `-e docs_site_release_tag=<tag>`. |
| Playbook fails before touching the server, "does not exist" (github token) | `secrets/github/token.txt` is missing — see `secrets/README.md`. |
| `register_ssl` fails on "certbot certonly" | DNS not propagated, or port 80 unreachable from the internet. |
| Site loads but shows stale content | Expected if nothing has re-deployed since the last change — re-run the playbook; this isn't a live-updating site (see "Deployment" above). |
| `mkdocs build --strict` fails during the playbook run | The same failure would show locally via `npm run build` in `docs/` — fix the underlying docs issue (broken nav entry, lint error) before retrying, not an infra problem. |

## See also

- [`rollback.md`](rollback.md) — full rollback procedure.
- B2 (`docs/project/first_production_release/b2-docs-deploy/`, not part
  of this built site) — the decision record for self-hosting instead of
  GitHub Pages.
