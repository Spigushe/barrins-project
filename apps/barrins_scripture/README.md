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
| Archive | JSON files, committed to the `mtg_decklist_cache` git submodule |
| Tests | pytest + pytest-cov |

## Scope

- Sources: MTGO and MTGTop8 only. (`mtg_scraper`'s old `mtgprime`
  one-off scraper is not ported — confirmed unusable, dropped entirely.)
- No database access, no ingestion logic — this app only produces the
  JSON archive. Ingesting archived data into `barrins_api` is a separate
  concern (see T3, `docs/project/v2.0.0-bump/t3-scripture-ingestion-pipeline/`).
- Scheduling runs on the VPS (`ops/my-server/barrins_scripture.yml`), not
  via GitHub Actions cron.
