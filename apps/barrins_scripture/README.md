# Barrin's Scripture: MTG tournament scraper

Scrapes decklists and tournament results from MTGO and MTGTop8, archiving
every scrape as JSON before anything else — the same
scrape-first-archive-first behavior as the standalone `mtg_scraper`
project this app supersedes (see
`docs/project/v2.0.0-bump/t1-scripture-repo-migration/`).

## Tech stack

| Component | Technology |
| --------- | ----------- |
| Language | Python 3.14 |
| Scraping | `requests` + `beautifulsoup4` (MTGTop8), `selenium` (MTGO, client-rendered) |
| Validation | Pydantic v2 |
| Archive | JSON files, eventually committed to the `mtg_decklist_cache` git submodule (not wired up yet — see Archive below) |
| Logging | stdlib `logging`, configured once in `__main__.main()` |
| Tests | pytest + pytest-cov |

## Usage

```sh
uv run scrape --source mtgo --date-from 2026-06 --date-to 2026-06
uv run scrape --source mtgtop8 --span 200
uv run scrape --source mtgo --output-dir /path/to/archive
```

`--help` lists every option. `--source` defaults to `mtgo`; `--date-from`/
`--date-to` (mtgo only, format `YYYY-MM`) default to a 5-day trailing
window; `--span` (mtgtop8 only) defaults to 1000 tournament ids; `--force-
mtgo` re-scrapes already-archived MTGO tournaments instead of skipping
them.

## Archive

`--output-dir` (defaults to `apps/barrins_scripture/scraped/` if omitted)
controls where the JSON archive is written — `<output-dir>/mtgo.com/` and
`/mtgtop8.com/`, mirroring `mtg_decklist_cache`'s own
`<source>/<year>/<month>/<day>/<slug>.json` layout. That default path is
git-ignored: per T1's plan (§1.3), the archive belongs in its own git
repository, never inlined into this monorepo's history. Wiring
`apps/barrins_scripture/scraped/` up as an actual submodule pointing at
`mtg_decklist_cache` (or its durable successor) is still open — until
then, `--output-dir` is how a deployment points this at wherever it
actually manages that clone.

## Scope

- Sources: MTGO and MTGTop8 only. (`mtg_scraper`'s old `mtgprime`
  one-off scraper is not ported — confirmed unusable, dropped entirely.)
- No database access, no ingestion logic — this app only produces the
  JSON archive. Ingesting archived data into `barrins_api` is a separate
  concern (see T3, `docs/project/v2.0.0-bump/t3-scripture-ingestion-pipeline/`).
- Scheduling runs on the VPS (`ops/my-server/barrins_scripture.yml`), not
  via GitHub Actions cron.
