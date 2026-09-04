---
name: release
description: "Drive a Barrin's-project release through its documented sequence (merge to staging, promote to main, tag/cut the release, deploy production, write ADRs) or an alpha/beta pre-release variant — including the ordering traps this project has already been burned by (ADRs before the staging merge, 'done' confirmations backported to staging not just main, squash-merge never advancing the merge-base between long-lived branches). Use when asked to cut/ship/promote/deploy a release, merge proj/staging/main, or 'what's left before this release'."
---

# Release workflow — Barrin's ecosystem

Release cutting in this repository is still a **manual, documented
process** (F2, `docs/project/v2.0.0-bump/f2-release-automation/index.md`,
is proposed but not built) — this skill is the checklist that process
runs against, not an automation you invoke.

## Before doing anything: which release, which step?

1. Find the active release's plan: `docs/project/<version>-bump/index.md`
   (currently `docs/project/v2.0.0-bump/index.md`). Its "Group R" (or
   `RA`/`RB` for an alpha/beta pre-release) lists the exact steps and
   their current status.
2. Read each numbered step's own `index.md`
   (`docs/project/<version>-bump/r1-merge-staging/index.md`, etc.) before
   acting — it carries the authoritative "Done statement," "Tasks," and
   any project-specific gotcha for that exact release. **This skill
   describes the shape; the step's own doc is the source of truth for
   this release's specifics.**
3. Never guess which step comes next from git state alone — check the
   plan's dependency graph. Steps are gated (e.g. R1 depends on every
   in-scope feature item **and** R5; R4 depends on R3 and the new
   services' playbooks existing).

## Canonical order (Group R) and what each step actually is

1. **R1 — merge to `staging`.** Every in-scope item is green on the
   integration branch (`proj/<version>-bump`), **and every ADR from R5
   is already merged into that same branch** — R5 is a hard
   *prerequisite* of R1 in this project, not trailing cleanup (see R5
   below; this ordering was added after v1.0.0 got it backwards).
2. **R2 — promote `staging` → `main`.** A fast-forward or merge so
   `main` reflects `staging` exactly at this point.
3. **R3 — tag and cut the release.** Manual today (ADR-2, F2 not yet
   built): create the `vX.Y.Z` tag on `main`, publish a GitHub Release
   with notes aggregated from the per-app `CHANGELOG.md`s.
4. **R4 — deploy from tag (production).** Constitution §25/§27.1:
   deploy only a tagged release, never a branch or local build. Each
   application deploys via its own playbook (§26.1 — one application,
   one playbook). A new service needs its playbook **and** monitoring
   live before or immediately after its first deploy (the same
   `postgres_backup`-before-`B1` gating precedent ADR-4 set).
5. **R5 — write the ADRs this release's decisions require.** Every
   resolved open decision (recorded in the release plan's own
   Context/Alternatives/Trade-offs shape, per §16.3) becomes a permanent
   entry in `docs/content/ops/architecture/decisions.md` — use the
   `decision-record` skill for the actual scaffolding. **This step
   precedes R1**, not the reverse.

Alpha/beta pre-releases (this project's `RA*`/`RB*` groups) follow the
same shape — confirm scope, decide the version-bump convention, merge
toward the integration/staging target — just against an earlier branch
pair and a narrower feature set. Read that specific group's own `index.md`
files; don't assume RA/RB map step-for-step onto R1-R5's numbering.

## Traps this project has already hit — don't repeat them

- **Confirmations written only on `main` never reach `staging`.**
  v1.0.0 wrote several "done" checkmarks directly on `main` after the
  squash-merge; they never existed on `staging` and cost two dedicated
  reconciliation PRs to fix. Whenever you mark an R2/R3/R4-style step
  done, **immediately backport that same confirmation to `staging`** in
  a small follow-up commit — don't let it accumulate.
- **Squash-merge never advances the merge-base between two long-lived
  branches** (Constitution Amendment Proposal 7,
  `docs/project/v2.0.0-bump/consitution-amendment.md` — 🔲 accepted-not-
  yet-applied as of this skill's writing, but the mechanism it documents
  is real and already bit this project twice, PRs #47/#48). If you're
  reconciling `proj/*` with `staging` (or any two integration branches)
  and a conflict keeps reappearing after you "fixed" it: build the
  reconciliation branch **from the target branch**, merging the *source*
  branch into it — not the reverse. A sync PR that squash-merges into
  the *source* branch does not clear the conflict in the opposite
  direction; these are two independent reconciliations under this
  repo's squash-only/linear-history branch protection, not one.
- **Never tag from a branch or local modification** — §25/§27.1 is
  absolute: production only ever deploys a release tag.
- **Never destination a new service's first production deploy ahead of
  its own playbook and monitoring** — same gating principle as ADR-4
  (`postgres_backup` before `B1`), reapplied per new service in R4.

## When you're not sure something is release-blocking

Per constitution §5/§16.2: if a decision inside the release process is
subjective (does this failing check block the release, is a feature
in-scope or should it slip to the next release), do not decide silently.
State the alternatives and their consequences, and ask — the same
posture the release plan documents already model for their own open
decisions (§1.x entries resolved via the same Context/Alternatives/
Trade-offs/Decision structure the `decision-record` skill scaffolds).
