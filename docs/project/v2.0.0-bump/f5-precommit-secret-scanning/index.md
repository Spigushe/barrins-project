# F5. Enforce pre-commit secret-scanning

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `.github/workflows/CI.yml` or a repo-side pre-receive check | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — pre-existing gap, worth reconsidering as contributor surface grows | / |
| **Source** | `docs/content/ops/roadmap.md`, `security/secrets.md` | / |
| **Dependency** | None | / |

---

## Context

`ops/my-server/scripts/check_no_secrets_committed.sh` exists but is
opt-in per developer (symlinked as a local pre-commit hook only) — no
CI or server-side gate enforces it today. This release adds new
contributors' worth of surface (new apps, potentially a migrated
external repo per T1) without changing that.

## Done statement

- The existing `check_no_secrets_committed.sh` (or GitHub's own
  secret-scanning feature, if adopted instead) runs automatically on
  every PR, not just for developers who symlinked the hook themselves.

## Tasks

- [ ] Decide: wire the existing script into a CI job vs. enable GitHub's
      built-in secret scanning vs. both.
- [ ] If CI-based: add a step (likely to the `ops` job, since the
      script lives under `ops/my-server/scripts/`) running the script
      against the diff.
- [ ] Update `security/secrets.md` to reflect the new enforced state
      once done (it currently explicitly says "Open item: this hook is
      not currently enforced automatically").

## UAT (manual)

- [ ] Open a test PR intentionally committing a fake secret-like value
      under `ops/my-server/secrets/`; confirm the new gate blocks it.

## Non-regression tests

- Confirm the new gate doesn't false-positive on the existing
  `*.example`/`README.md` allow-list already carved out by the script.
