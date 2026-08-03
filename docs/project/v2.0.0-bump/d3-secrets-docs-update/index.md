# D3. Document the new service-to-service credential

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `docs/content/ops/security/secrets.md`, `ops/my-server/secrets/README.md` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — unblocked, §1.2/I3 decided 2026-07-25 (Option 2: private ingestion route, needs a service credential) | / |
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

## Done statement

- The new credential follows the existing "never in git" pattern
  (`ops/my-server/secrets/**` git-ignored except `*.example`/
  `README.md`, per ADR-1).
- `security/secrets.md` gains a short section describing it: what it's
  for, its scope, and why it's handled the way it is (mirroring the
  existing "Why `github_token` is different" section's shape).

## Tasks

- [ ] Generate/document the credential's `.env.example` entry for
      whichever app(s) need it (`barrins_api`, and Barrin's Scripture
      once T1 lands).
- [ ] Write the `security/secrets.md` section.

## UAT (manual)

- [ ] `check_no_secrets_committed.sh` still passes with the new secret
      file in place (git-ignored, not staged).

## Non-regression tests

- N/A (documentation/ops item).
