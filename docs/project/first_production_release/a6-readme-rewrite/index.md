# A6. Root README rewrite

[← Back to project index](../index.md)

## Context

Current `README.md` is a single line ("Full stack project for
collecting/rendering Magic: the Gathering data").

## Design

Rewrite into a clear, presentation-first README: what the project is and
does, for whom, a short feature overview, links to the live apps and to
the docs site (`docs.barrins-codex.org`) — light on technical/
architecture detail, which already has a proper home in `docs/content/`.
The root README is a different, top-level file and isn't synced by
`sync_readmes.py`, so it can be freely rewritten without affecting the
docs build.

## Tasks

- [ ] Draft the new README content (pitch, feature overview, links).
- [ ] Verify every link resolves.

## Done statement

Root `README.md` rewritten, presentation-first, all links verified live.

## UAT (manual)

- [ ] Read the rendered README on GitHub as if unfamiliar with the
      codebase; confirm it's clear, and every link (docs site, live
      apps) resolves correctly.

## Non-regression tests

Manual only, no automated code path — confirm `docs/hooks/sync_readmes.py`
still behaves identically for app READMEs (the root README isn't synced,
so this change can't affect app doc pages; verified by running the docs
build once).
