# R3. Tag and cut the release

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `v2.0.0` tag, GitHub Release | / |
| **Initial date** | 2026-09-06 | / |
| **Status** | 🟡 Tag done, release drafted — publish deferred to R4 | / |
| **Source** | Mirrors v1.0.0's B5 | / |
| **Dependency** | R2 | Blocks R4 |

---

## Done statement

`v2.0.0` tagged on `main`, GitHub Release published with real notes
(aggregated from the per-app `CHANGELOG.md`s, per the existing
changelog-split convention — and per F3, hopefully with the heading bug
already fixed by this point).

**Note (2026-09-06):** in practice, every past release (`v1.0.0`,
`v2.0.0-alpha`, `v2.0.0-alpha.2`) shipped a hand-written, user-facing
announcement post instead of a raw CHANGELOG aggregation — this release
follows that precedent (user decision), not the aggregation this
statement originally described.

## Tasks

- [X] Cut the annotated tag `v2.0.0` on `main` at `116573c2` (`main`'s
      exact tip from R2) — manually, per ADR-2's documented gap (F2 not
      built).
- [X] Draft the GitHub Release: title `v2.0.0 "Morningtide"`, ecosystem-
      wide announcement (English, same style as `v2.0.0-alpha.2`'s post)
      covering the identity/account unification, Tolaria News's public
      launch, and the Tamiyo Scroll feature set, with a "coming soon"
      mention for Karn Tablets (still feature-flagged off). Created as a
      **draft**, not published — it links `tolaria.barrins-codex.org`
      and the one-account flow, neither of which is live in production
      until R4 deploys them.
- [ ] Publish the draft release for real once R4 completes and those
      URLs resolve.
- [X] Immediately backport this item's "done" confirmation to `staging`
      once written on `main` (§3.1) — same reasoning as R2's equivalent
      task, don't let it accumulate.

## UAT (manual)

- [X] Tag matches `main`'s HEAD from R2 (`116573c25c26ab273fbf3c6b22c2b83d71bd806f`).
- [ ] GitHub Release page shows correct, complete notes and is public —
      checked once published (post-R4).

## Non-regression tests

- N/A (release-process step).
