# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [Unreleased]

### Added

- Karn Tablets clustering ingest + read surface (T6 backend half,
  ADR-13). `POST /internal/karn/ingest` (`X-Karn-Token` /
  `KARN_INGEST_TOKEN`, same shape as scripture ingest) persists a pushed
  clustering run into new `kt_*` tables (`kt_clustering_runs`,
  `kt_archetypes`, `kt_run_archetypes`). The ingester
  (`app/services/karn/ingester.py`) gives each cluster a **stable**
  archetype identity by matching its representative decklist against the
  registry (Jaccard ≥ 0.6), auto-naming new archetypes from their top
  non-basic-land cards. Read layer (`app/services/karn/read.py`, isolated
  per §45.1) is shared by the public Tolaria News BFF routes
  `GET /bff/tolaria-news/{metagame,archetypes,trends}` (no auth, ADR-10)
  and the S6 admin route
  `GET /bff/tamiyo-scroll/admin/metrics/karn-tablets` (`AdminUser`), so
  the two surfaces can't drift. All read routes take `window`
  (`rolling_30d` | `banlist_period`) and an optional `format` query param
  (default `"Duel Commander"` — see ADR-13's 2026-08-27 amendment).
  Migration `a1f4c7e9b230`. Deployment playbook (T8) still separate.
- Karn Tablets read contract additions (T6 frontend wiring). Additive —
  no migration.
  - **Window stepper.** `/metagame` and `/archetypes` responses gained
    `previous_window` / `next_window` (`WindowOut | null`, the adjacent
    windows of the same kind by period start), and both take an `at`
    query param — a `window.label` — to step to a past window (`404` if
    no run carries that label). `/archetypes` `data` changed from a bare
    list to `{format, window, previous_window, next_window, archetypes}`
    (the `page` envelope still carries the cursor).
  - **Momentum** (`"rising" | "falling" | "stable" | "new"`) +
    `deck_share_delta` on every archetype row now compare it to the run
    of the **preceding window of the same kind** (not "the second-most-
    recent run"), so momentum is meaningful at any point in the stepper;
    at the oldest window everything is `"stable"`/`null`. The
    ±10%-of-previous-share band is a backend-owned rule (§4.1/§4.2).
  - Every archetype row (all three routes) gained
    `commanders: [{name, scryfall_id}]` for card-image hovers.
  - `/archetypes` `representative_mainboard` rows gained `scryfall_id`,
    `is_land`, and `is_signature` — the last is `false` for a **basic**
    land always and for any other land in ≥33% of the run's archetypes
    (a metagame-wide staple), `true` otherwise; the frontend just
    filters on it.
  - `/archetypes` is cursor-paginated (`limit` 1–100, default 20; opaque
    `cursor`; malformed cursor → `400`). `/trends` returns the top 10
    archetypes.
- Structured Commander/Library decklist view (S4):
  `GET .../personal-decks/{id}/decklist-view` now returns a
  `ResponseDecklistView` (`commander_cards`/`library_cards`/
  `unparsed_lines`) instead of a flat colored-line list — each resolved
  card carries `mana_cost`/`type_line`/`text`/`keywords`/`scryfall_id`
  from `mj_cards`, grouped by type and sorted by mana value then name.
  `GET /bff/tolaria-news/decks/{id}`'s `mainboard` gets the same
  type-grouping/sort, via a new shared `app/services/decklist_sort.py`
  module used by both apps. A `"Commander"` header line (new
  `commander_section_indices` in `decklist_coloring.py`) splits a
  decklist into its commander(s) vs. library; Moxfield-imported decks
  now get this header for free (`_format_board`).
- Disk-cached Scryfall card-image proxy: `GET
  /api/v1/cards/{scryfall_id}/image?face=front|back`
  (`app/services/scryfall/`), rate-limited to Scryfall's ~10 req/s
  courtesy limit, wiped on every `POST /mtgjson/import` (`scryfall_id`
  can shift/disappear on refresh). New `SCRYFALL_USER_AGENT`/
  `CARD_IMAGE_CACHE_DIR` settings; a placeholder-image console client is
  used when unset outside production.
- `app/services/identity_directory.py` — batched, TTL-cached
  `{user_id: {username, display_name}}` lookups against
  `barrins_identity`'s `POST /api/v1/users/lookup` (service token, scope
  `identity:users:read`), for team-roster / sharing display labels. New
  `IDENTITY_SERVICE_CLIENT_ID` / `IDENTITY_SERVICE_CLIENT_SECRET`
  settings; empty ⇒ the directory is disabled and labels fall back to a
  generic placeholder.
- `apps/barrins_api/scripts/migrate_users_to_identity.py` — one-shot,
  UUID-preserving copy of `users` into `barrins_identity`'s database
  (`--source-url` / `--target-url` / `--dry-run` / `--report`). Email
  dedup raises `role` to the higher of the two; `username` is synthesised
  from the email local part and every synthesised / suffixed handle goes
  to the report. Each URL resolves as flag → `$SOURCE_DATABASE_URL` /
  `$TARGET_DATABASE_URL` → the same key in `apps/barrins_api/.env`
  (matching `sync_mj_bs_tables.py`). CI-tested against two throwaway DBs.

### Changed

- **Authentication cut over to `barrins_identity` JWKS (ADR-20, rollout
  Phase 7+8).** `barrins_api` no longer issues or decodes its own JWTs:
  `app/dependencies/auth.py` + `app/dependencies/service_auth.py` verify
  `barrins_identity` RS256 access tokens locally against its JWKS via
  `libs/identity_client`. `AuthenticatedUser {id, role, email}` replaces
  the ORM `User`; role ordering moved to `app/core/roles.py` (the
  `placeholder` role is renamed `moderator` to match the identity claim).
  New required `IDENTITY_SERVICE_URL` setting; `SECRET_KEY`, `ALGORITHM`,
  `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` removed.
- `resolve_owner` (sharing) no longer reasons about user existence — an
  `owner_id` with no `ts_user_settings` row is `403` "does not share",
  never `404`.
- Team rosters expose `username` instead of `email`
  (`ResponseTeamMember.email` → `username`); deck-owner / sharer labels
  come from the identity directory (`display_name` or `username`, never
  the email address).
- `pyproject.toml`: dropped `python-jose` + `argon2-cffi`; added `pyjwt`,
  `respx` (test), and the `identity-client` path dep.

### Removed

- Local auth surface, now owned by `barrins_identity`:
  `app/api/general/auth.py` (login / signup / email verification),
  `app/core/security.py`, `app/schemas/auth.py`, `app/models/user.py`,
  `app/models/email_verification.py`, `scripts/create_admin.py`.
- The email surface: `app/services/email/` (SMTP + console senders), all
  `SMTP_*` / `REQUIRE_EMAIL_VERIFICATION` / `VERIFICATION_*` /
  `FRONTEND_BASE_URL` settings and the production SMTP validator in
  `app/config/base.py`, and the `python-multipart` + `pydantic[email]`
  dependencies. `barrins_api` sends no email — signup / verification /
  password reset are entirely `barrins_identity`'s.
- The `users` table, `auth_email_verifications` table, the `userrole`
  enum, and the 12 `ForeignKey("users.id")` constraints on the Tamiyo
  Scroll tables — Alembic `d9e1a2c3b4f5`. `owner_id` / `user_id` columns
  stay as plain FK-less `UUID`s holding identity user ids.
- Admin "total accounts" metric (`PlatformMetrics.total_accounts`, the
  timeseries `accounts` series) — its data source is gone. Decks /
  matches / sessions metrics are unchanged; restore later via a
  `barrins_identity` admin count endpoint.

## [2.0.0-alpha] - 2026-08-03

### Added

- Team sharing (`/bff/tamiyo-scroll/teams*`): team CRUD (create/join/leave/
  delete) with 8-character invite codes, redemption rate-limited to 1 per
  5 seconds and 5 per minute; member listing with per-member
  cross-flagged-deck activity counts; name-based deck sharing
  (`ts_team_deck_flags`) — flagging one member's deck *name* auto-includes
  every other current or future member's same-named deck, computed at
  read time rather than a per-deck link; per-team-deck-name discussion
  threads (`ts_team_deck_threads`); a cumulative team-deck PDF report per
  flagged name (`GET .../teams/{id}/decks/{name_key}/report.pdf`,
  aggregating every contributing member's data); and reuses the new
  `PATCH /personal-decks/{id}` route (below, S10/S11) to rename a deck —
  renaming into/out of a flagged name joins/leaves a team-deck's
  rotation.
- Server-rendered PDF training reports (WeasyPrint, pinned `>=69.0`, see
  ADR I8): `GET .../sessions/{id}/report.pdf` for one training/tournament
  session (decklist version used, matches logged against it, win rate vs.
  the session's baseline, card-test feedback) and
  `GET .../personal-decks/{deck_id}/report.pdf` for a session-less,
  rolling last-30-days report that also folds in a viewer's merged shared
  data. Both share one calculation path (`stats.compute_period_stats`)
  and one renderer, no duplicated winrate/matchup logic.
- Tournament/training session grouping: new `ts_sessions` table (`name`,
  `tournament`/`training` type, `notes`, soft-delete via `archived_at`)
  with full CRUD and `GET .../sessions/{id}/comparison`, which diffs a
  session's matches against the same deck's prior history (everything
  logged before the session started, including other sessions), reusing
  the existing archetype/matchup stats functions. `ts_matches` gains an
  optional `session_id`, validated against the same owner and personal
  deck.
- Automatic read-only sharing merge (`app/services/tamiyo_scroll/
  sharing_merge.py`): once a sharer has `data_shared` on and a viewer has
  `receive_shared_data` on, the sharer's personal decks merge directly
  into the viewer's own Journal (matches) and Metagame (roster +
  archetype/matchup stats), matched by exact deck name — a name match
  keeps the viewer's own tier/category. Replaces the "View: {user}"
  selector concept entirely; the `GET /shared-users` route and its
  supporting per-sharer opt-in table are removed along with it.
- `PATCH /api/v1/auth/me` for self-service `display_name` updates.
- Match-to-decklist-version auto-stamping: `ts_matches` gains a nullable
  `decklist_version_id` FK to `ts_personal_decklist_versions`, auto-filled
  with the personal deck's current latest version at match creation, and
  editable afterward on the match itself.
- Moxfield re-import staleness flag: `TSPersonalDecklistVersion` gains a
  nullable `moxfield_data` JSONB column storing the full raw Moxfield API
  response for Moxfield-imported versions (`NULL` for manual entries).
  `POST .../versions/import-moxfield` now returns
  `moxfield_deck_changed_since_last_import` by comparing the fresh
  `lastUpdatedAtUtc` (read from the response root only, never a recursive
  search) against the deck's prior Moxfield-sourced version.
  `MoxfieldClient.fetch_decklist` returns this alongside the formatted
  decklist text.
- Barrin's Scripture scraped-tournament schema (`app/models/scripture.py`):
  six `bs_`-prefixed tables — `bs_tournaments`, `bs_decks`,
  `bs_deck_cards`, `bs_rounds`, `bs_round_matches`, `bs_standings` —
  mirroring the existing `ts_*` modeling convention, each with a unique
  constraint on its natural key so replaying the scrape archive through a
  future ingestion route is an idempotent upsert. Not yet wired to any
  route.
- `GET /internal/scripture/db-metrics`: on-disk size
  (`pg_total_relation_size` — heap + indexes + TOAST) and live row count
  of every `bs_*` table (`app/services/scripture/db_metrics.py`). Callable
  by either the same `X-Scripture-Token` service credential as `/ingest`
  or an admin user's JWT (`verify_scripture_or_admin`,
  `app/dependencies/service_auth.py`) — the first combined
  service-secret-or-admin gate in the codebase, scoped to `bs_*` only so
  the service credential never sees other apps' table sizes.
- Admin usage/metrics dashboard (`app/api/tamiyo_scroll/admin.py`, gated
  by `AdminUser`): flat totals (accounts, personal decks, matches
  recorded) via `app/services/metrics/`, plus day (last 30)/week (last
  12)/month (last 12) time-bucketed breakdowns of the same three counts
  (`app/services/metrics/timeseries.py`, `GET
  /admin/metrics/timeseries`), computed server-side via `GROUP BY
  date_trunc(...)`.
- `CardGame` field on `TSPersonalDeck` (S10) and a reused
  `ArchetypeCategory` `category` field (S11, same enum/Postgres type as
  the meta-deck roster): both nullable, no default/backfill, **required**
  on new-deck creation, and gating `_validate_match_refs` — logging or
  editing a match on a deck with `game`/`category IS NULL` is rejected
  with `422 personal_deck_game_required`/`422
  personal_deck_macrotype_required`. New `PATCH /personal-decks/{id}`
  route (first-ever PATCH on this resource) sets either field, and an
  optional `name`, to unblock historical decks and allow renames (a
  rename is also how a member joins/leaves a team-deck's name-based
  sharing rotation, S2). `CardGame`: `magic`, `yu_gi_oh`, `pokemon`,
  `flesh_and_blood`, `one_piece`, `lorcana`.
- Meta-deck `game` inheritance: a newly-created opponent/meta deck
  inherits its creating personal deck's `game`, and cascades to that
  meta deck's own opponent entries, so a non-Magic personal deck doesn't
  silently produce `NULL`-game meta decks (2026-08-03 follow-up to S10).
- Live MTGJSON import progress: `GET /mtgjson/import/status` (admin-gated)
  returns the most recent `POST /mtgjson/import` run's status
  (`running`/`succeeded`/`failed`), counts so far, and `error_message` on
  failure. A new `mj_import_runs` table is written independently of the
  main import transaction (`_ImportRunTracker`, its own short-lived
  session committed at the same granularity as the existing upsert
  chunking), since the importer only commits `mj_sets`/`mj_cards` once at
  the end and Postgres's default isolation would otherwise hide all
  progress from any poll until the whole import finished. A leftover
  `running` row from a hard crash (e.g. the 2026-08-09 OOM incident) is
  self-healed to `failed` the next time an import starts, rather than
  staying stuck forever. The existing `sets`/`cards` tables are also
  renamed to `mj_sets`/`mj_cards` in the same migration, matching this
  codebase's `bs_*`/`ts_*` domain-prefix convention (DB-internal only —
  API paths and ORM class names are unaffected).

### Changed

- Global sharing re-enabled: the `SHARING_ENABLED` gate is removed
  entirely. Receiving now also requires an explicit opt-in
  (`receive_shared_data` on `ts_user_settings`) in addition to the
  sharer's existing `data_shared`; new accounts default to
  `data_shared=true` (opt-out) while `receive_shared_data` still defaults
  `false` (opt-in), asymmetric on purpose.
- `PATCH /me/settings` (`update_my_settings`) now rejects
  `receive_shared_data: true` together with `data_shared: false` with
  `422 receive_requires_share` — an account can share without receiving,
  but can no longer receive without also sharing.
- Merged/roster response schemas (`ResponseMetaDeck`,
  `ResponseDeckWinrate`, `ResponseMatchupRow`) gain `has_shared_data`
  (an owned deck that also received at least one merged shared match,
  distinct from a fully-foreign `is_readonly` entry) and
  `is_multi_share` (two or more sharers' same-named decks consolidated
  into one read-only roster line, highest tier wins, instead of one line
  per sharer).
- PDF reports and the S9 session-comparison endpoint now exclude matches
  against an archived opponent deck instead of surfacing them as an
  unresolvable "?" row.

### Fixed

- Sharing merge no longer falls back to a sharer's raw email as the
  `shared_by` label when `display_name` is unset (privacy/GDPR); falls
  back to a generic "a kind user" label instead.
- Archiving a name-matched roster entry no longer strands a merged match
  pointing at the archived id with no read-only fallback line — only
  non-archived owner roster entries count as a name match now; an
  archived match falls back to the sharer's own entry as a new read-only
  line, same as no match at all.
- `GET /meta-decks` no longer 422s for any account with sharing enabled:
  `EffectiveMetaDeck` (`sharing_merge.py`) wasn't updated when S10 added
  `game` to `TSPersonalDeck`/meta decks, so `ResponseMetaDeck.
  model_validate()` failed Pydantic validation on the merged roster,
  breaking the whole list rather than just the new decks.
- `POST /mtgjson/import` no longer OOM-kills the backend worker on a real,
  full `AllPrintings.json` run: `HttpxMTGJSONClient` buffered the whole
  response body and parsed JSON tree, and `import_all_printings` built
  full `set_rows`/`card_rows` lists on top of that, all before writing a
  single row (2026-08-09 incident: ~5.5GB RSS, worker killed mid-import,
  zero rows committed). Both now stream via `ijson` (new dependency,
  `stream_sets()` + `_ImportBuffer`), bounding peak memory to
  `_UPSERT_CHUNK_SIZE` rows instead of file size; still one commit at the
  end, same idempotent-upsert contract.
- `GET /mtgjson/status`'s `last_imported_at` no longer freezes at each
  row's original insert time: the chunked upsert's raw
  `INSERT ... ON CONFLICT DO UPDATE` bypassed the ORM unit-of-work path,
  so `MTGSet`/`Card`'s `onupdate=func.now()` never fired on a re-import's
  conflict branch. Found while UAT-ing the streaming fix above against
  the real full file on staging (2026-08-09): two successful runs,
  `last_imported_at` still showed the first run's timestamp. `updated_at`
  is now set explicitly in `_upsert_sets`/`_upsert_cards`'s `update_cols`.

## [1.0.0] "WorldWake" - 2026-07-24

### Added

- Initial scaffold of the Barrin's API backend (FastAPI, Python 3.14,
  PostgreSQL via async SQLAlchemy 2 + asyncpg, Alembic migrations,
  Pydantic v2 settings).
- Authentication (`/api/v1/auth`): JWT (HS256) login/refresh/logout,
  self-registration with email verification (`/auth/signup`,
  `/auth/signup/verify`, `/auth/signup/resend`), admin-only direct
  account creation, Argon2id password hashing, and a 5-level
  hierarchical role system (`anonymous` → `user` → `role_c` →
  `ml_developer` → `admin`) enforced via a `require_role(min_role)`
  dependency.
- Tamiyo Scroll BFF (`/bff/tamiyo-scroll`), a competitive MTG tracking
  API: user settings (read-only sharing), personal decks and
  versioned decklists (with Moxfield import), a metagame/opponent
  deck roster, a BO3 match log, card-test feedback, decklist coloring
  by test feedback, and aggregated archetype/matchup statistics.
- Email delivery service with a console sender for local development
  and an SMTP sender for production.
- `scripts/create_admin.py` to bootstrap the first admin account, and
  `scripts/workflow_ci.py` to run the full local CI pipeline (ruff,
  ty, pytest) outside of GitHub Actions.
- Alembic migrations: users/roles/tokens, auth email verifications,
  and the Tamiyo Scroll tracker tables.
- Test suite (pytest + pytest-asyncio + httpx) with a 90% global / 100%
  `app/models/` coverage floor.
- `docs/content/back/barrins_api/auth_roles.md`: documents the JWT
  authentication and hierarchical role-based access control system
  (role hierarchy, endpoint security matrix), replacing the ad hoc
  `X-Admin-Key` header.
- `docs/content/back/barrins_api/signup_email_verification.md`:
  documents the self-registration and email verification flow
  (`/auth/signup`, `/auth/signup/verify`, `/auth/signup/resend`).
- Nav entries (`docs/mkdocs.yml`) and `_links.md` sidecar links for the
  two pages above.
- `GET /health`: reports database connectivity (`200`/`503`), for
  external uptime monitoring — `503` covers both a failed query and a
  fully unreachable database (e.g. connection refused/rejected).
  Registered after `GET /` in `general/router.py` so `/docs` lists
  routes in that order.
- External uptime monitoring (HetrixTools) is live against `barrins_api`
  prod + staging `/health`, plus certificate-expiry alerting — see
  `docs/content/ops/operations/index.md`.
- Real Moxfield deck import (`app/services/moxfield/`): fetches a public
  deck from Moxfield's API, rate-limited to 1 request/second, replacing
  the earlier placeholder that only stored the given URL as text.
- API routes reorganized into one `app/api/<domain>/` package per domain
  (`general/`, `tamiyo_scroll/`), each owning its own router aggregator —
  replaced the previous `ts_router.py`/`bff/ts_router/` and
  `v1_router.py`/`v1/` split, which had a file and a differently-scoped
  directory sharing the same name.

### Changed

- Translated `README.md` from French to English.
