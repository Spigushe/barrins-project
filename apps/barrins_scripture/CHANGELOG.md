# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [Unreleased]

### Added

- Initial project scaffold (`pyproject.toml`, package layout, tooling).
- `schemas`: pydantic models ported from `mtg_scraper` (`Deck`, `CardEntry`,
  `Tournament`, `Round`, `Match`, `Standing`, `MTGScrape`, `Formats`).
  `CircuitPlayer`/`player.py` not ported — it was `mtgprime`-only, and
  `mtgprime` itself isn't ported (confirmed unusable).
- `parsers.mtgo` / `parsers.mtgtop8`: HTML-in, schema-out parsers, verified
  against real archived Duel Commander tournaments (one MTGO, one
  MTGTop8) from `mtg_decklist_cache`.
- `utils.{mtgo,mtgtop8,selenium_driver,date_parsing,swiss_tournament}`:
  the scraping orchestration layer — Selenium driving, tournament-list
  discovery, dedup-by-already-scraped checks, and JSON-archive writes.
- `services.{mtgo,mtgtop8}` + a working CLI (`uv run scrape`): the
  producer/consumer thread orchestration and entry point tying
  everything above together into an actual runnable scraper.
- `--output-dir`: overrides the default archive location
  (`apps/barrins_scripture/scraped/`), so a deployment can point the
  JSON archive wherever it manages that clone instead of assuming a git
  submodule at a fixed path.

### Fixed

(Bugs inherited from `mtg_scraper`, found and fixed during this rewrite
— see individual commits for detail.)

- `parse_date` checked `isinstance(x, date)` before `isinstance(x,
  datetime)`; since `datetime` subclasses `date`, the `datetime` branch
  was dead code.
- `mtgtop8` parser's `get_tournament_soup` passed its headers dict
  positionally to `requests.get`, which treats it as `params=`, not
  `headers=` — the custom `User-Agent` was never actually sent.
- `mtgtop8_utils.we_should_scrape_it` used a non-recursive `glob` to look
  for already-archived files that always live nested 3 directories deep
  — this dedup check was a permanent no-op.
- `mtgtop8`'s consumer re-queued a bare URL string on retry into a queue
  typed `(url, soup)`, which would crash the next dequeue.
- `scrape_mtgtop8`'s id-range loop was off by one, silently skipping the
  very next unscraped tournament id on every run.
