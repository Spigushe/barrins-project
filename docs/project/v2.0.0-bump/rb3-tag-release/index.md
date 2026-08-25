# RB3. Tag and cut the `v2.0.0-alpha.2` release

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `v2.0.0-alpha.2` tag, GitHub Release (marked pre-release) | / |
| **Initial date** | 2026-08-25 | Done same day |
| **Status** | ✅ **Done (2026-08-25)** — tag pushed, GitHub Release published | / |
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

- [x] Cut the tag/release manually (per ADR-2's documented gap, F2).
      `v2.0.0-alpha.2` created as an annotated tag on `main`'s new head
      (`10c556b`, RB2's merge commit) and pushed.
- [x] Check "This is a pre-release" on the GitHub Release. Confirmed via
      `gh release view v2.0.0-alpha.2 --json isPrerelease,isDraft` —
      `isPrerelease: true`, `isDraft: false`.
- [x] Write the release description's scope note so anyone reading it —
      including future contributors to this project — understands why
      Group T and S18 aren't in it. Notes aggregated from all three
      `[2.0.0-alpha.2]` `CHANGELOG.md` sections (root, `barrins_api`,
      `tamiyo_scroll`), breaking changes (S16, S17, F10) called out up
      top, scope note first. Published:
      <https://github.com/Spigushe/barrins-project/releases/tag/v2.0.0-alpha.2>
- [ ] Immediately backport this item's "done" confirmation to `staging`
      once written on `main` (§3.1), same as RA4/R3's equivalent task —
      same one-directional Proposal 7 limitation RB2 hit, so this is a
      small follow-up PR into `staging`, not a direct push.

## UAT (manual)

- [x] GitHub Release page shows correct, complete, correctly-scoped
      notes; tag matches `main`'s HEAD from RB2 (`10c556b`); pre-release
      flag is set.

## Non-regression tests

- N/A (release-process step).
