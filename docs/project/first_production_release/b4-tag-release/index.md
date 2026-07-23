# B4. Tag and cut the release

[← Back to project index](../index.md)

## Tasks

- [ ] On `main`, after merge: annotated tag `v1.0.0`, pushed to `origin`.
- [ ] Create the GitHub Release from that tag (title `v1.0.0`, notes
      drawn from each sub-repo's `CHANGELOG.md` `[1.0.0]` section — the
      same content `sync_changelogs.py` picks up as "Latest changes" once
      this tag exists).

This satisfies ADR-2's precondition. Manual this time; automating it is
a separate tracked item, not part of this release.

## Done statement

`v1.0.0` tag pushed; GitHub Release published with accurate notes.

## UAT (manual)

- [ ] Open the GitHub Releases page; confirm the release is visible and
      its notes match the aggregated changelog content.

## Non-regression tests

None (no code change) — confirm ADR-2's precondition check now passes
(the deploy playbook no longer fails with "no release exists yet").
