# T7. Docs for the new applications

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `docs/content/back/barrins_scripture/`, `docs/content/back/karn_tablets/`, `docs/content/front/tolaria_news/_links.md` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — depends on T1, T4, T5, T6 having real content to document | / |
| **Source** | Request item 1 | / |
| **Dependency** | T1, T4, T5, T6 | Blocks nothing further |

---

## Context

Every existing app's docs page follows the same generated pattern:
`docs/hooks/sync_readmes.py` copies `apps/<app>/README.md` into
`docs/content/**/<app>/index.md` at build time, with a sibling
`_links.md` sidecar preserving curated nav links (e.g. `bff/`,
`bootstrap.md`, `incidents/`) that would otherwise be lost. New apps
just need real README content (produced by their own work items) plus
whatever curated links make sense once those exist.

## Done statement

- `docs/content/back/barrins_scripture/_links.md` and
  `docs/content/back/karn_tablets/_links.md` created (mirroring
  `barrins_identity/_links.md`'s pattern), linking to whatever
  design/BFF docs those items produce (e.g. a future
  `bff/tolaria_news.md` for T4, analogous to `bff/tamiyo_scroll.md`).
- `docs/content/front/tolaria_news/_links.md` (currently empty)
  populated once T5 produces a bootstrap/handoff doc worth linking, the
  same way `tamiyo_scroll/_links.md` links `bootstrap.md`/`handoff.md`/
  `incidents/`.
- `docs/content/back/index.md` (currently listing only the apps that
  exist today) updated with entries for Barrin's Scripture and Karn
  Tablets. `docs/content/front/index.md` needs no change here — it
  already lists Tolaria News.

## Tasks

- [ ] Write `bff/tolaria_news.md` alongside T4 (implementation-plan
      style doc, matching `bff/tamiyo_scroll.md`'s format).
- [ ] Create the `_links.md` sidecars listed above.
- [ ] Update `docs/content/back/index.md` with Barrin's Scripture and
      Karn Tablets entries (`front/index.md` already lists Tolaria
      News, no change needed there).

## UAT (manual)

- [ ] `npm run build` (docs site) succeeds with the new pages present,
      no broken internal links (mkdocs' link checker, if configured, or
      a manual click-through).

## Non-regression tests

- N/A (documentation-only item) — covered by the existing docs CI job
  (`.github/workflows/CI.yml`'s `docs` job: markdownlint, spellcheck,
  build).
