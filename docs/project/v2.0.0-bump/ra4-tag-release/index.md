# RA4. Tag and cut the `v2.0.0-alpha` release

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `v2.0.0-alpha` tag, GitHub Release (marked pre-release) | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started | / |
| **Source** | Mirrors R3/v1.0.0's B5, scoped to the alpha cut (§1.11) | / |
| **Dependency** | RA3 | Blocks RA5 |

---

## Context

First time this project has cut a pre-release (`-alpha` suffix) tag —
v1.0.0 went straight to a final tag, and no prior release used a
semver pre-release identifier. GitHub's "mark as a pre-release" checkbox
exists for exactly this case: it keeps `v2.0.0-alpha` out of the "Latest
release" slot so the eventual `v2.0.0` final tag still reads as the
canonical release once it ships.

## Done statement

- `v2.0.0-alpha` tagged on `main`.
- GitHub Release published, **marked as a pre-release**, with real notes
  aggregated from the per-app `CHANGELOG.md`s' `[2.0.0-alpha]` sections
  (RA1), explicitly scoped in the release description: "Tamiyo Scroll
  deck-management changes only — Tolaria News / Barrin's Scripture /
  Karn Tablets land in the full v2.0.0."

## Tasks

- [ ] Cut the tag/release manually (per ADR-2's documented gap, F2).
- [ ] Check "This is a pre-release" on the GitHub Release.
- [ ] Write the release description's scope note (above) so anyone
      reading it — including future contributors to this project —
      understands why Group T isn't in it.
- [ ] Immediately backport this item's "done" confirmation to `staging`
      once written on `main` (§3.1), same as R3's equivalent task.

## UAT (manual)

- [ ] GitHub Release page shows correct, complete, correctly-scoped
      notes; tag matches `main`'s HEAD from RA3; pre-release flag is set.

## Non-regression tests

- N/A (release-process step).
