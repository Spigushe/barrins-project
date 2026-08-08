# D3. Document the new service-to-service credential

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `docs/content/ops/security/secrets.md`, `ops/my-server/secrets/README.md` | / |
| **Initial date** | / | Not started |
| **Status** | 🟡 **Half done, as a byproduct of T8 (2026-08-08)** — while scheduling the T3 sweep, T8 documented `SCRIPTURE_INGEST_TOKEN` in `ops/my-server/secrets/README.md` and added `secrets/barrins_api/{production,staging}.env.example` / `secrets/barrins_scripture/{production,staging}.env.example`. This item's own remaining scope narrows to the `docs/content/ops/security/secrets.md` write-up — see Context | / |
| **Source** | Request item 4; `v2.0.0-bump/index.md` §1.2 | / |
| **Dependency** | I3 (§1.2) | / |

---

## Context

§1.2/I3 resolved (2026-07-25, Option 2, see ADR-5): Barrin's Scripture
calls a private ingestion route (`POST /internal/scripture/ingest`) on
`barrins_api` rather than holding its own `DATABASE_URL`. That route
needs a new service-to-service credential — same shape as the existing
`github_token`/Moxfield-credential precedent: narrow-scope, backend-
only, never reaching a browser. `security/secrets.md` needs updating to
describe it, the same way ADR-1 already documents the reasoning for
every other secret's handling.

**Overlap found 2026-08-08**: T8, while wiring the T3 sweep onto its own
systemd timer, already needed to document `SCRIPTURE_INGEST_TOKEN`
operationally (`ops/my-server/secrets/README.md`, plus
`secrets/barrins_api/*.env.example` and the new
`secrets/barrins_scripture/*.env.example`) so the sweep's deploy
(`deploy_env`-gated staging validation before production) made sense on
its own. That covers this item's `.env.example`/`ops/my-server/secrets/
README.md` half. What's still genuinely this item's own scope is the
narrative write-up in `docs/content/ops/security/secrets.md` — the
`security/secrets.md` file this page's Target/Done statement actually
names — which T8 had no reason to touch.

## Done statement

- The new credential follows the existing "never in git" pattern
  (`ops/my-server/secrets/**` git-ignored except `*.example`/
  `README.md`, per ADR-1).
- `security/secrets.md` gains a short section describing it: what it's
  for, its scope, and why it's handled the way it is (mirroring the
  existing "Why `github_token` is different" section's shape).

## Tasks

- [x] Generate/document the credential's `.env.example` entry for
      whichever app(s) need it (`barrins_api`, and Barrin's Scripture
      once T1 lands). **Done, via T8 (2026-08-08)**: see Context.
- [ ] Write the `security/secrets.md` section. **Still open** — the only
      remaining task on this item.

## UAT (manual)

- [ ] `check_no_secrets_committed.sh` still passes with the new secret
      file in place (git-ignored, not staged).

## Non-regression tests

- N/A (documentation/ops item).
