# Parser test fixtures

Real, live-fetched data — not hand-authored — paired with the same
tournament's already-archived JSON from `mtg_decklist_cache` as the
known-correct expected output. Per T1's plan, at least one Duel Commander
event from each source is included (MTGO doesn't natively support
Commander-family formats in its official queues, but does run a
community "Duel Commander League").

## mtgo/duel_commander_league_2026-06-27.html

- Source: `https://www.mtgo.com/decklist/duel-commander-league-2026-06-2710716`
- Fetched 2026-07-29 via headless Chrome (Selenium), waiting for
  `p.decklist-posted-on` to appear before capturing `page_source`.
- **A plain HTTP fetch of this URL is not usable as a fixture**: the
  server response only contains the page's Underscore.js template
  (`<section class="decklist" id="<%- data.playerAnchor %>">` etc.),
  not the rendered deck data — confirming mtgo.com decklist pages are
  genuinely client-rendered, as T1's context notes already said. The
  parser itself only ever touches a `BeautifulSoup`-parsed string, so a
  captured `page_source` is a faithful, sufficient input regardless of
  how it was produced.
- **Why this specific league and not the most recent one**: the first
  attempt used the then-most-recent league (2026-07-27). MTGO leagues
  stay open for ~5 days accepting new 5-0 decklists, so re-fetching it
  live returned *more* decks than the archived JSON had captured days
  earlier — not a parsing bug, just a moving target. This one
  (2026-06-27) is a month old and fully closed, so re-fetching it live
  reproduces the archive exactly: same 4 players, same mainboards/
  sideboards/results.
- **One known, accepted discrepancy**: every deck's *own* `date` field
  (not the tournament date) comes back one day earlier than the archive
  (`6/26/2026` vs the archived `2026-06-27`) — reproduces consistently
  across all 4 decks, most likely a timezone-rendering difference
  between the original scrape's environment (a UTC CI runner) and
  wherever this was re-fetched from, not a parsing bug. `test_parsers.py`
  asserts this field against what the page itself says rather than the
  archive, with a comment explaining why.
- Expected output: `duel_commander_league_2026-06-27.expected.json`,
  copied verbatim from `mtg_decklist_cache`'s
  `mtgo.com/2026/06/27/duel-commander-league-2026-06-2710716.json`.

## mtgtop8/event_88803_duel_commander.html + decklist_874003.html

- Source: `https://mtgtop8.com/event?e=88803` (event/standings page) and
  `https://mtgtop8.com/mtgo?d=874003` (rank-1 deck's plain-text
  decklist), both fetched 2026-07-28 via a plain `requests`-equivalent
  GET (`curl`, same `User-Agent` the parser's own `HEADERS` use) — no
  browser rendering needed, this source is server-rendered.
- The event page's deck links use **unquoted HTML attributes**
  (`href=?e=88803&d=874003&f=EDH`, no quotes) — easy to miss when
  grepping for `href="..."` but BeautifulSoup parses them correctly.
- Only one deck's decklist page is included (rank 1, "Sylvain Courtois",
  `d=874003`) even though the tournament has 29 registered players — the
  event only published full decklists for the top 8, which is exactly
  what `decks()` finds (verified: `len(decks(soup)) == 8`, matching the
  archive). The other 7 top-8 decks are exercised structurally in tests
  (decks() must still find all of them) with `get_decklist`/`get_notes`
  mocked out to avoid live calls for entries with no fetched fixture.
- `get_notes()` (the AI-generated deck-explanation endpoint,
  `event?e=1&d=<id>&explain_deck=Y` — note the upstream code hardcodes
  `e=1` rather than the real event id, preserved as-is since I can't
  verify a fix without more real examples) was **not** fetched — it's a
  nullable, secondary field, not core to decklist scraping. Mocked in
  tests via `unittest.mock.patch`, with its own small unit tests against
  a synthetic response instead.
- Expected output: `event_88803_duel_commander.expected.json`, copied
  verbatim from `mtg_decklist_cache`'s
  `mtgtop8.com/2026/07/26/88803_duel-commander_championnat-dc-974-juillet.json`.

## Known gap: the mtgtop8 "out of top8" (radio-selector) path

`parsers/mtgtop8.py`'s `get_deck_out_top8` (for large events that list
every deck via `<input type="radio">` elements instead of individual
`<a href>` links) has **no real fixture** — neither Duel Commander event
used it. Worse, its ported logic reads `deck_tag.contents[0]`, and
`<input>` is a void HTML element: BeautifulSoup's `html.parser` backend
(the same one `get_tournament_soup` uses) always gives it `contents == []`,
so this path raises `IndexError` for any standard-conforming markup.
`tests/test_parsers_units.py::test_get_deck_out_top8_raises_without_a_parent`
and the sibling test documenting the void-element issue capture this
honestly rather than hiding it behind a synthetic fixture built to make
it pass. **Before this ships, find a real large mtgtop8 event that uses
this path and fixture it properly** — either the real markup differs
from what the original `mtg_scraper` code assumed (and this needs a real
fix), or this path has simply never worked in production either.
