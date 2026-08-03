# R3. Tag and cut the release

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `v2.0.0` tag, GitHub Release | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started | / |
| **Source** | Mirrors v1.0.0's B5 | / |
| **Dependency** | R2 | Blocks R4 |

---

## Done statement

`v2.0.0` tagged on `main`, GitHub Release published with real notes
(aggregated from the per-app `CHANGELOG.md`s, per the existing
changelog-split convention — and per F3, hopefully with the heading bug
already fixed by this point).

## Tasks

- [ ] Cut the tag/release — manually, per ADR-2's documented gap, unless
      F2 lands in time to automate this for real.
- [ ] Immediately backport this item's "done" confirmation to `staging`
      once written on `main` (§3.1) — same reasoning as R2's equivalent
      task, don't let it accumulate.

## UAT (manual)

- [ ] GitHub Release page shows correct, complete notes; tag matches
      `main`'s HEAD from R2.

## Non-regression tests

- N/A (release-process step).
