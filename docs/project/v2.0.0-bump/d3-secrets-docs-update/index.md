# D3. Document the new service-to-service credential

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `docs/content/ops/security/secrets.md`, `ops/my-server/secrets/README.md` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — depends on §1.2's outcome | / |
| **Source** | Request item 4; `v2.0.0-bump/index.md` §1.2 | / |
| **Dependency** | I3 (§1.2) | / |

---

## Context

If §1.2 resolves to "Barrin's Scripture calls a private ingestion route
on `barrins_api`" (the recommended option), a new credential is needed
for that service-to-service call — same shape as the existing
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

- [ ] Wait on §1.2's outcome.
- [ ] Generate/document the credential's `.env.example` entry for
      whichever app(s) need it.
- [ ] Write the `security/secrets.md` section.

## UAT (manual)

- [ ] `check_no_secrets_committed.sh` still passes with the new secret
      file in place (git-ignored, not staged).

## Non-regression tests

- N/A (documentation/ops item).
