# F3. Changelog aggregation heading-level bug

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `docs/hooks/sync_changelogs.py` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 Not started — cosmetic, should fix before more apps hit it | / |
| **Source** | `docs/content/ops/roadmap.md` (found during v1.0.0's changelog-split UAT) | / |
| **Dependency** | None | / |

---

## Context

Found during v1.0.0's changelog-split UAT: sub-repo and category
headings render at the same level in `changelog/index.md`'s "Latest
changes" section. Every app added to the aggregation this release
(Tolaria News, Barrin's Scripture, Karn Tablets if it ever ships real
changelog entries) repeats the same cosmetic issue.

## Done statement

- `sync_changelogs.py` emits distinct heading levels for "which app" vs.
  "which change category," so the aggregated page reads as a proper
  nested hierarchy.

## Tasks

- [ ] Reproduce the current output with today's two apps
      (`barrins_api`, `tamiyo_scroll`) to confirm the exact bug.
- [ ] Fix the heading-level generation in the hook.
- [ ] Re-run the docs build; visually confirm the aggregated page nests
      correctly with at least three apps' changelogs feeding it
      (simulate with dummy entries for the new apps if their real
      changelogs don't exist yet at the time this is fixed).

## UAT (manual)

- [ ] `npm run build` (docs) then inspect `changelog/index.md`'s
      rendered "Latest changes" section — headings nest correctly.

## Non-regression tests

- Existing docs CI job (`markdownlint`, `build`) stays green; add a
  focused unit test for the hook itself if none exists yet.
