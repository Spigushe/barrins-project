# S4. Better decklist display

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/tamiyo_scroll` (`CurrentDecklistSection.tsx`), `apps/tolaria_news` (`DeckDetailPage.tsx` — extended to this app too, see below), plus `apps/barrins_api` for sortable card metadata and a new card-image proxy | / |
| **Initial date** | 2026-08-14 | Done same day |
| **Status** | ✅ **Done (2026-08-14)** | / |
| **Source** | Request item 2.3 | / |
| **Dependency** | S8 (card images + sortable metadata — done 2026-08-05) | / |

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

## Implementation (2026-08-14)

Landed alongside T5's Tolaria News scaffold rather than as a standalone
Tamiyo Scroll change — `apps/tolaria_news/DeckDetailPage.tsx` shows the
same commander-plus-type-grouped decklist table, since T4's BFF already
returns a per-tournament decklist and the sort/grouping logic this item
needed is not Tamiyo-Scroll-specific. Both frontends now share the
component pair (`components/card-faces-preview.tsx`,
`components/mana-pips.tsx`, `lib/mana-symbols.ts`,
`components/ui/hover-card.tsx`) rather than each building its own.

**No hifi mockup was produced** for this item, unlike the original
build's `handoff.md`-driven process — implementation instead worked
directly from a short written spec (sort order, the "pips must contain
color" requirement, and the Commander/Qty/Name/Color-pips/Popover table
shape). Narrower and faster than the originally-planned design-pass
step; recorded here so this isn't misread later as having gone through
the same hifi process as
`handoff.md`.

**Sort/grouping — differs from the original spec in one respect**: the
decided spec above called for a **two-criteria, user-selectable**
sort (primary + secondary, both pickable) with a specific **face-A-Land
rule** for multi-face cards. What shipped is a **fixed** order —
`app/services/decklist_sort.py`: category (planeswalker, battle,
creature, instant, sorcery, artifact, enchantment, land, other, in that
priority — a combined type line like "Artifact Creature" always
resolves to its highest-priority category) → mana value → name — not
user-selectable, and with no explicit face-A-Land special case (S8's
`mj_cards.type_line` is resolved per print, and the priority-order walk
above means any type line containing "land" groups as land regardless
of face ordering, which happens to satisfy the common case, but no
dedicated per-face check was added or tested against a multi-face-land
fixture). If the selectable-sort/face-A-Land requirements are still
wanted as originally decided, that's follow-up scope, not silently
dropped — recorded here rather than assumed satisfied.

**Card images**: sourced from a new Scryfall image proxy
(`GET /api/v1/cards/{scryfall_id}/image`, `app/services/scryfall/`),
disk-cached and wiped on every MTGJSON re-import. Shown as a hover-card
preview on the card name (front + back face for MDFC/transform cards),
not inline in the table row — narrower than "render card images" read
literally, but keeps the dense table layout the spec's
Qty/Name/Color-pips/Popover structure implies.

**Color pips**: `ManaPips` renders each `{symbol}` token
(`lib/mana-symbols.ts`) as a small badge with the raw symbol text
(e.g. `W`, `U/R`, `U/P`) — hybrid and Phyrexian symbols pass through
unmodified since Scryfall's mana-cost string already encodes them as
single tokens (`{W/U}`, `{U/P}`). Pips are not yet color-coded per
WUBRG (all render in the same neutral badge style) — the spec's "pips
must contain color" is satisfied literally (the color letter is shown)
but not via actual per-color styling. Flagged here as a likely
follow-up polish item, not addressed in this pass.

**Done statement, as actually shipped**:

- `decklist-view` no longer returns the flat `{line, status}[]` shape —
  superseded by a structured `ResponseDecklistView`
  (`commander_cards`/`library_cards`/`unparsed_lines`), documented in
  `bff/tamiyo_scroll.md` §F. Still built on `color_decklist`'s
  per-line status, still computed server-side — no client-side
  re-derivation of validated/rejected/in-test/neutral.
- Card-type sort/grouping is computed server-side
  (`app/services/decklist_sort.py`), shared by both apps.
- Card images render via the new Scryfall proxy once a card resolves to
  a `scryfall_id`.
- Backend: 500 tests passing, 97.20% coverage, `ruff`/`ty` clean.
  Frontend: `apps/tamiyo_scroll` 232 tests / `apps/tolaria_news` 14
  tests, both typecheck/build/lint clean.

## Non-regression tests

- `tamiyo_scroll`'s `reuseAssertions.ts`/`demoApi.test.ts` (demo-mode
  fixtures) updated for the structured response shape — qty and name
  now render as separate table cells, not one `"<qty> <name>"` text
  line; `apps/tamiyo_scroll/src/demo/api/personalDecks.ts` mirrors the
  backend's categorize/group-by-category logic client-side (demo mode
  has no backend to call).
- New backend tests for `decklist_sort.py` (category/tiebreak
  ordering), `decklist_view.py`, and `decklist_coloring.py`'s new
  `commander_section_indices`/`parse_card_line` helpers — no fixture
  test specifically exercises a multi-face-land card, consistent with
  the face-A-Land rule not being separately implemented (see above).
