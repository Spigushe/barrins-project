# A6. Root README rewrite

[← Back to project index](../index.md)

## Context

Current `README.md` was a single line ("Full stack project for
collecting/rendering Magic: the Gathering data").

## Design

Rewrite into a clear, presentation-first README: what the project is and
does, for whom, a short feature overview — light on technical/
architecture detail, which already has a proper home in `docs/content/`
and each app's own `apps/*/README.md`. The root README is a different,
top-level file and isn't synced by `sync_readmes.py`, so it can be
freely rewritten without affecting the docs build.

**Confirmed with the user before finalizing**: `deployment_strategy.md`
documents production domains (`tamiyo.barrins-codex.org`,
`api.barrins-codex.org`, `docs.barrins-codex.org`), but as of writing
this, **nothing is live in production yet** — only `api`/`tamiyo` on
staging. A public-facing README asserting working "try it here" links
would have been actively misleading pre-launch (and staging URLs aren't
meant to be advertised publicly either). Final version has **no live
links** — just an honest "nothing public yet" status note, to be added
back once B5 (production deploy) actually ships.

## Tasks

- [x] Draft the new README content (pitch, feature overview, status).
- [x] Confirm production domain status with the user before including
      any links — none are live, so none are included.

## Done statement

Root `README.md` rewritten, presentation-first, no misleading/broken
links.

## UAT (manual)

- [ ] Read the rendered README on GitHub as if unfamiliar with the
      codebase; confirm it's clear and accurate.
- [ ] Once B5 ships, add real links back (docs site + production apps)
      — tracked as a small follow-up, not part of this item.

## Non-regression tests

Manual only, no automated code path — confirm `docs/hooks/sync_readmes.py`
still behaves identically for app READMEs (the root README isn't synced,
so this change can't affect app doc pages; verified by running the docs
build once — see A4/A5's build verification, unaffected by this change).
