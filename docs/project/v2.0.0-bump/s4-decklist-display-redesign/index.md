# S4. Better decklist display

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/tamiyo_scroll` (`CurrentDecklistSection.tsx`, `VersionHistorySection.tsx`) | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Design not started** — no target UI exists yet, "UI TBD" per the request | / |
| **Source** | Request item 2.3 | / |
| **Dependency** | None (no technical blocker — needs a design pass first) | / |

---

## Context

The request explicitly flags this as "UI TBD" — no target design exists.
Today's decklist display lives in
`src/pages/decklist/CurrentDecklistSection.tsx` and
`VersionHistorySection.tsx`, driven by the backend's already-computed
row-coloring (`GET .../decklist-view`, per
`bff/tamiyo_scroll.md`'s Option F: validated/rejected/in_test/neutral
per row, computed server-side). Whatever the redesign becomes, it must
keep consuming that pre-computed coloring rather than recomputing it
client-side (Constitution §4.1/§4.2) — the original build already got
this right, no regression risk on the calculation itself, only on
presentation.

## Done statement

Cannot be finalized without a design pass first. At minimum, whatever
ships must:

- Continue consuming `decklist-view`'s server-computed
  `{line, status}[]` shape as-is.
- Not reintroduce any client-side re-derivation of validated/rejected/
  in-test/neutral status.

## Tasks

- [ ] Design pass (mockup/wireframe) — the same "hifi design first"
      approach `docs/content/front/tamiyo_scroll/handoff.md` used for
      the original build (colors/typography/spacing/interactions final
      before implementation starts).
- [ ] Implement against the approved design.
- [ ] Confirm `decklist-view`'s response shape doesn't need to change to
      support the new design — if it does, that's backend work added to
      this item's scope, not assumed here.

## UAT (manual)

- [ ] Cannot be written meaningfully before a design exists.

## Non-regression tests

- Existing `decklist-view`-consuming component tests must still pass
  against whatever new component replaces today's display.
