# MTGJSON test fixtures

## mtgjson_sample.json

Real, live-fetched MTGJSON data, trimmed to a handful of card entries per
set — not hand-authored — matching `AllPrintings.json`'s own top-level
shape (`{"meta": ..., "data": {<set code>: <Set object with a `cards`
list>, ...}}`), so the importer under test (`app/services/mtgjson/`) sees
the same structure it will see against the real file.

- **P30A** ("30th Anniversary Play Promos"), fetched 2026-08-05 via
  `GET https://mtgjson.com/api/v5/P30A.json` — a small (30-card), real
  set, trimmed to one card (`Serra Angel`, a normal single-face card) for
  the single-face import/round-trip path.
- **ZNR** ("Zendikar Rising"), fetched 2026-08-05 via
  `GET https://mtgjson.com/api/v5/ZNR.json` — trimmed to the two real
  entries for `Emeria's Call // Emeria, Shattered Skyclave`, a modal
  double-faced card: face `a` (`Emeria's Call`, a `Sorcery`) and face `b`
  (`Emeria, Shattered Skyclave`, a `Land`), linked via `otherFaceIds`.
  Used for the per-face type-data round-trip test (S8's done statement:
  "multi-face cards store per-face type data... required by S4's
  'face A Land' rule").

Both sets' own metadata fields (`name`, `releaseDate`, `type`, `block`,
`baseSetSize`, `totalSetSize`, `keyruneCode`, `isOnlineOnly`, `languages`)
and every kept card object are copied verbatim from the real download —
only the `cards` array (and top-level unrelated keys like `decks`,
`booster`, `sealedProduct`) were trimmed down, no field values were
hand-edited.

## scryfall_*_example.json

Real, live-fetched Scryfall card payloads (`GET
https://api.scryfall.com/cards/<id>`), one per multi-face layout, used by
`test_mtgjson.py` to regression-test `GET /cards/by-name/{name}` and
`GET /cards/search-by-name/{name}` against every layout whose combined
name contains a literal " // " (MTGJSON and Scryfall agree on this
combined `name` string — verified against the real ZNR entry in
`mtgjson_sample.json` above). Each file is converted into a minimal
MTGJSON-shaped set+card pair at test time (`_mtgjson_payload_from_scryfall_card`)
rather than imported as Scryfall's own schema. Each filename names the
card's actual `layout` field, so the tests can key off either without
the two drifting apart.

- `scryfall_aventure_example.json` — `layout: adventure` (Bonecrusher
  Giant // Stomp, ELD).
- `scryfall_transform_example.json` — `layout: transform` (Delver of
  Secrets // Insectile Aberration, MID).
- `scryfall_mdfc_example.json` — `layout: modal_dfc` (King T'Challa //
  Black Panther, Hope Enduring, MSH).
- `scryfall_room_example.json` — `layout: split` (Roaring Furnace //
  Steaming Sauna, DSK).
- `scryfall_prepared_example.json` — `layout: prepare` (Emeritus of
  Ideation // Ancestral Recall, SOS).
