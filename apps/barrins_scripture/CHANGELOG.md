# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [2.0.0] "Morningtide" - 2026-09-06

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
- `scripts.top8_check_gaps` / `scripts.mtgo_empty_decks`: the biweekly
  gap-check maintenance jobs, ported from `mtg_scraper`'s scripts of the
  same purpose (renamed from `mtgo_empy_decks`, a typo in the original).
  Invoked directly (`python -m barrins_scripture.scripts.<name>`), same
  as the originals were.
- `scripts.top8_check_gaps`: `--output-dir` (same meaning as `scrape
  --output-dir`, for when the archive is checked out outside this
  monorepo) and `--progress` (a `sweep --progress`-style live stderr
  bar, off by default). Also fixes two producer/consumer wiring bugs
  that made every real (non-mocked) `scrape_gaps()` run silently do
  nothing: the 3rd `producer` arg was the batch's `Lock` instead of the
  scraped-ids set `we_should_scrape_it()` checks, and `consumer` was
  missing its required `producers_done` argument entirely.
- CI: a `scripture` path filter + job in `.github/workflows/CI.yml`
  (mirrors `back`'s shape, no Postgres service — this app has no DB
  access), backed by a new local CI runner
  (`apps/barrins_scripture/scripts/workflow_ci.py`, mirroring
  `apps/barrins_api`'s).
- Ops: `ops/my-server/barrins_scripture.yml` + a new
  `ops/my-server/roles/scripture_scraper/` role — a `systemd`
  `.service`/`.timer` pair (patterned on `roles/postgres_backup/`)
  running the daily scrape and the Sunday biweekly gap-check on the VPS,
  replacing `mtg_scraper`'s GitHub Actions cron per T1's scheduling
  decision. `ansible-lint` clean (via WSL); not yet deployed to the
  real VPS.

### Changed

- `services.mtgo.scrape_mtgo`: reworked from "detect every month in the
  date span, then scrape everything found" to detect-then-scrape one
  month at a time (`detect_month` / `scrape_links`, replacing the old
  `producer`/`consumer`-thread split for the detection side). A large
  backfill now starts saving tournaments after the first month is
  detected instead of only after the whole span has been crawled, and
  one month's retries never mix with another month's queue. Selenium
  drivers are now reused across every month's batch instead of being
  re-launched per run — `consumer()` no longer quits its own driver
  (driver lifecycle moved to the caller: `scrape_mtgo` and
  `scripts.mtgo_empty_decks.scrape_tournaments_without_decks`, the two
  places that create drivers for it).

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
- `mtgtop8_utils.we_should_scrape_it` re-walked the entire archive tree
  (`rglob`) on every call — O(n^2) in archive size, since it's called once
  per candidate tournament id. `get_scraped_ids()` now walks the archive
  once per `scrape_mtgtop8()` run and the resulting set is reused across
  every producer's dedup check.
