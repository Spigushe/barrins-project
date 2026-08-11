<!-- cSpell:ignore mkdocs -->
# Barrin's Project

Technical documentation for the `barrins-project` monorepo.

## Sections

- **back end**
  - _`barrins_api`_: FastAPI / BFF API
  - _`barrins_identity`_: FastAPI / Single user profile entry point
- **front end**
  - _`tamiyo_scroll`_: ReactJS / Test result tracker
  - _`tolaria_news`_: ReactJS / Duel Commander data display & exploration !WIP!
- **service** — Standalone background services (no HTTP API of their own)
  - _`barrins_scripture`_: MTG tournament scraper (MTGO / MTGTop8)
- **ops** — Deployment, infrastructure (Ansible / myserver)

> This page and its associated `nav:` (in `mkdocs.yml`) are
> placeholders to be filled in as sub-projects are migrated.
