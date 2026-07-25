# T6. Karn Tablets — placeholder scaffold

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/karn_tablets` (new, placeholder only) | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — depends on §1.4 being confirmed | / |
| **Source** | Request item 1; `v2.0.0-bump/index.md` §1.4 | / |
| **Dependency** | I4 | Blocks T8 (its playbook) |

---

## Context

No prior planning for Karn Tablets exists anywhere in this repository or
its constitution. §1.4 recommends scoping it to a placeholder for
v2.0.0 (mirroring how `apps/tolaria_news` and `apps/barrins_identity`
exist today as README/CHANGELOG-only intents) rather than building a
real ML/DL service now — **recommendation, not yet confirmed**.

## Done statement (if §1.4's recommendation is confirmed)

- `apps/karn_tablets/README.md` describing intent only (what it will
  eventually do: compute/serve ML/DL data derived from the `dl_*`
  scraped-tournament domain), no application code.
- `apps/karn_tablets/CHANGELOG.md`, placeholder entry, matching the
  `apps/tolaria_news`/`apps/barrins_identity` precedent exactly.
- The `dl_*` schema (T2) is confirmed, during T2's own design pass, not
  to structurally prevent a future Karn Tablets from reading it (no
  schema change required later just to make it readable).

## Tasks

- [ ] Confirm §1.4 (placeholder-only) with the user before doing even
      this much — it's still an open recommendation, not a decision.
- [ ] Write the placeholder README/CHANGELOG.
- [ ] No other implementation work for v2.0.0.

## UAT (manual)

- [ ] N/A beyond confirming the placeholder files exist and are wired
      into the docs-sync hook (`docs/hooks/sync_readmes.py`) the same
      way every other app's README already is.

## Non-regression tests

- None — no code is added.
