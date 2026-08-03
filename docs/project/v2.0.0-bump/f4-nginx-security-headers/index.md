# F4. nginx security headers (HSTS, etc.)

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `ops/my-server/roles/backend_website/`, `roles/register_ssl/` templates | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — pre-existing gap, unrelated to v2.0.0 specifically | / |
| **Source** | `docs/content/ops/roadmap.md`, Constitution §29.1 | / |
| **Dependency** | None | / |

---

## Context

Constitution §29.1 expects nginx security headers; none are implemented
today across any vhost template. This gap predates v2.0.0 and applies
equally to every existing and new domain (`api`, `tamiyo`, `tolaria`,
`pgadmin`, ...).

## Done statement

- HSTS (and any other headers §29.1 requires — re-read its exact text
  before implementing, not assumed here) added to the shared vhost
  template(s) so every current and future domain inherits them
  automatically, rather than per-app opt-in.

## Tasks

- [ ] Re-read Constitution §29.1's exact requirement.
- [ ] Add the headers to `roles/backend_website/templates/https.conf.j2`
      and `roles/register_ssl/templates/http.conf.j2` (the two template
      locations `operations/index.md` already references for
      access/error logging — the natural place for shared vhost
      concerns).
- [ ] Re-run every affected playbook on staging to confirm no existing
      functionality breaks (some strict headers, e.g. HSTS with
      `includeSubDomains`, can have real consequences if misconfigured).

## UAT (manual)

- [ ] `curl -I` against a staging domain; confirm the new headers are
      present with correct values.

## Non-regression tests

- `ansible-lint ops/my-server` stays clean.
- Manual check that existing frontend/backend functionality (CORS,
  asset loading) is unaffected by the new headers.
