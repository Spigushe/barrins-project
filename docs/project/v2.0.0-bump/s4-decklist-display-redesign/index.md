# S4. Better decklist display

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/tamiyo_scroll` (`CurrentDecklistSection.tsx`, `VersionHistorySection.tsx`), plus `apps/barrins_api` for sortable card metadata | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — needs S8 (card/set data) in addition to a design pass | / |
| **Source** | Request item 2.3 | / |
| **Dependency** | S8 (card images + sortable metadata — added 2026-07-26) | / |

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

**New, 2026-07-26**: the redesign is linked to real MTG card data —
card images and sort-by-{type, mana value, color identity, mana cost}
all need cards to exist somewhere in the database. **Verified this
doesn't exist yet** (F8): `auth_roles.md` describes an MTGJSON pipeline
as already built; it isn't. S8 is the new item that builds it from
scratch. This item is blocked on S8, not just on a design pass —
"implementation investigation," per the user, is needed once S8's
ingestion and scheduling land, since the exact shape of card data
available (and how images are sourced — MTGJSON has no images) isn't
settled yet.

## Decided sorting spec (2026-07-26)

- **Two sort criteria, primary + secondary**, both selectable, not just
  one fixed order.
- **Default**: primary = Card Type, secondary = Mana Value.
- **Important rule**: for a multi-face card, if **face A** (the front
  face) has "Land" among its types, the **whole card** is treated as a
  Land for sorting/grouping purposes — regardless of face B's types.
  This requires per-face type data from S8 (a single flattened type
  line isn't enough to evaluate this rule).

## Done statement

Cannot be fully finalized without both a design pass and S8 landing. At
minimum, whatever ships must:

- Continue consuming `decklist-view`'s server-computed
  `{line, status}[]` shape as-is.
- Not reintroduce any client-side re-derivation of validated/rejected/
  in-test/neutral status.
- Implement the two-criteria sort (default Card Type → Mana Value) and
  the face-A-Land rule above, computed server-side (Constitution
  §4.1/§4.2 — sorting by card metadata is business logic, not
  presentation).
- Render card images once S8 defines an image source.

## Tasks

- [ ] Wait for S8 to land (card/set data, per-face type data, image
      source decision) — implementation investigation needed at that
      point, per the user, before this item's backend work is scoped in
      detail.
- [ ] Design pass (mockup/wireframe) — the same "hifi design first"
      approach `docs/content/front/tamiyo_scroll/handoff.md` used for
      the original build (colors/typography/spacing/interactions final
      before implementation starts). Can proceed in parallel with S8.
- [ ] Backend: implement the primary/secondary sort (default Card Type →
      Mana Value) and the face-A-Land rule, server-side.
- [ ] Implement against the approved design, consuming S8's card data +
      the new sort output.
- [ ] Confirm `decklist-view`'s response shape doesn't need to change to
      support the new design — if it does, that's backend work added to
      this item's scope, not assumed here.

## UAT (manual)

- [ ] Cannot be written meaningfully before a design exists and S8 lands.
- [ ] Once both land: confirm a deck containing a multi-face land
      (face A = Land) sorts as a Land, not by face B's type.

## Non-regression tests

- Existing `decklist-view`-consuming component tests must still pass
  against whatever new component replaces today's display.
- New backend test for the sort function: default ordering, secondary-
  criteria tiebreak, and the face-A-Land rule against a fixture
  multi-face card.
