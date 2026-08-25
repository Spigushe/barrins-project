# RB3. Tag and cut the `v2.0.0-alpha.2` release

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `v2.0.0-alpha.2` tag, GitHub Release (marked pre-release) | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started | / |
| **Source** | Mirrors RA4/R3/v1.0.0's B5, scoped to the alpha.2 cut (§1.12) | / |
| **Dependency** | RB2 | Blocks RB4 |

---

## Context

Second pre-release tag this project has cut. `v2.0.0-alpha` used the
un-numbered `-alpha` suffix; this one uses `-alpha.2` (§1.12's decision)
— SemVer's dot-separated pre-release numbering, the correct form once a
second pre-release of the same name exists. Same "mark as a pre-release"
GitHub checkbox as RA4, for the same reason: keeps this tag out of the
"Latest release" slot so the eventual `v2.0.0` final tag still reads as
the canonical release once it ships.

## Done statement

- `v2.0.0-alpha.2` tagged on `main`.
- GitHub Release published, **marked as a pre-release**, with real notes
  aggregated from the per-app `CHANGELOG.md`s' `[2.0.0-alpha.2]`
  sections (RB1), explicitly scoped in the release description: "Tamiyo
  Scroll deck-management changes only (S4, S8, S13–S17) — Tolaria News /
  Barrin's Scripture / Karn Tablets / S18 land later."

## Tasks

- [ ] Cut the tag/release manually (per ADR-2's documented gap, F2).
- [ ] Check "This is a pre-release" on the GitHub Release.
- [ ] Write the release description's scope note (above) so anyone
      reading it — including future contributors to this project —
      understands why Group T and S18 aren't in it.
- [ ] Immediately backport this item's "done" confirmation to `staging`
      once written on `main` (§3.1), same as RA4/R3's equivalent task.

## UAT (manual)

- [ ] GitHub Release page shows correct, complete, correctly-scoped
      notes; tag matches `main`'s HEAD from RB2; pre-release flag is set.

## Non-regression tests

- N/A (release-process step).
