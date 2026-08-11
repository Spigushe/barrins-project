# T6 — Karn Tablets: metagame clustering & deck-type aggregation

## Context

T6 (`docs/project/v2.0.0-bump/t6-karn-tablets-scaffold/index.md`) is now
unblocked: its dependencies I4 (scope resolved), T2 (`bs_*` schema), and T3
(ingestion pipeline) are all done. T6's own page flagged three open
sub-decisions as blockers before implementation ("not yet narrowed (flagged,
not guessed)"), each requiring the user's call per Constitution §16.2. All
three are now resolved by the user, this session:

1. **Windowing strategy** → both modes ship (rolling 30-day *and*
   banlist-period).
2. **Consumption surface** → folded into S6's existing admin metrics
   dashboard (`AdminMetricsPage`), not a new page.
3. **Clustering approach** → scikit-learn (new dependency, §4.7/§22 —
   Agglomerative/DBSCAN avoid having to pre-pick a cluster count, which fits
   "unknown number of archetypes"; the alternative of a hand-rolled
   Jaccard-similarity clusterer was rejected as unnecessary algorithmic risk
   for a solved problem).

This plan implements T6 itself: the `apps/karn_tablets` pipeline package, the
two `barrins_api` internal routes it talks to, the `kt_*` persistence layer,
and the S6 dashboard integration (explicitly gated on the consumption-surface
decision per T6's own page: "needs confirmation before the frontend/exposure
side of this item is designed"). It does **not** cover T7 (per-app docs
pages under `docs/content/`) or T8 (the ops deployment playbook) — those stay
separate tracked items, though this plan's design decisions (a pure scheduled
job, no HTTP surface of its own) directly unblock T8's "shape TBD by T6" note.

## Architecture decision: how Karn Tablets reaches `bs_*` data

Mirroring the precedent already set by Barrin's Scripture (§1.2, Constitution
§4.1/§26.1 — `barrins_api` is the sole schema owner, no second app gets its
own `DATABASE_URL`) and confirmed by `docs/content/ops/deployment/
new-service-checklist.md` ("most new services should NOT get their own DB,
call an existing app's ingestion route instead"):

- Karn Tablets gets **no Postgres credential**. It's a scheduled job with no
  HTTP surface of its own — same shape as `apps/barrins_scripture`.
- **Reads** `bs_*` data via a new internal-only route,
  `GET /internal/karn-tablets/decks`, gated the same way as scripture
  ingestion (static shared secret, `X-Karn-Tablets-Token` header). T4
  (Tolaria News BFF, the only other consumer of `bs_*` data) is confirmed
  **not started** (`t4-tolaria-news-bff/index.md` still shows 🔲 Blocked) —
  there's no existing public route to reuse, and a public/rate-limited BFF
  route wouldn't be the right shape for a bulk historical export anyway.
- **Writes** clustering results back via a second internal route,
  `POST /internal/karn-tablets/ingest`, following the exact same
  request/response/auth shape as `POST /internal/scripture/ingest`.
- `barrins_api` owns the new `kt_*` tables and their Alembic migration,
  consistent with owning every other domain table.

## Backend: `apps/barrins_api`

**New models** (`app/models/karn_tablets.py`, mirrors `models/scripture.py`'s
style — `KTSource = Literal`-style enum not needed, plain strings/enums as
appropriate):

- `KTClusteringRun` — `id`, `window_type` (`Enum`: `rolling_30d` |
  `banlist_period`), `window_start`, `window_end`, `pipeline_version` (str),
  `algorithm` (str, e.g. `"agglomerative"`), `algorithm_params` (JSON),
  `created_at`. This is the §45.2-required metadata record (source data
  range, pipeline version, algorithm info) — one row per pipeline run.
- `KTDeckTypeCluster` — `id`, `run_id` (FK → `KTClusteringRun`,
  `ondelete="CASCADE"`), `cluster_label` (str, e.g. `"cluster-3"` — no
  human-readable archetype naming in v2.0.0, out of scope), `deck_count`
  (int), `share_pct` (float). One row per cluster within a run.

New Alembic migration adding both tables (`uq` constraint on
`(window_type, window_start, window_end)` on `KTClusteringRun` so a rerun
for the same window is a controlled decision, not silent duplication).

**New internal routes** (`app/api/general/karn_tablets.py`, registered in
`app/api/general/router.py` under `prefix="/internal/karn-tablets"`, mirrors
`app/api/general/scripture.py` exactly):

- `GET /internal/karn-tablets/decks?since=&until=` — returns every
  `BSDeck` in range with its `BSDeckCard` rows (card_name/count/board) and
  parent `BSTournament.source`/`format`. Paginated (cursor or
  offset/limit) since this can be a large bulk export; existing pagination
  helper (check `app/api/tamiyo_scroll/` for a precedent) reused if one
  exists.
- `POST /internal/karn-tablets/ingest` — body: window metadata + list of
  `{cluster_label, deck_count, share_pct}`. Persists one `KTClusteringRun`
  - its `KTDeckTypeCluster` rows in one transaction. Idempotent on rerun
  via the unique constraint above (409 on duplicate window, not a silent
  overwrite — clustering isn't naturally idempotent per-row the way
  scripture ingestion is).

**New auth dependency** (`app/dependencies/service_auth.py`): add
`verify_karn_tablets_token`/`KarnTabletsToken`, copy of
`verify_scripture_token`/`ScriptureToken`, new setting
`settings.base.karn_tablets_token` (`app/config/base.py`, same
`SecretStr | None` pattern as `scripture_ingest_token`), documented in
`.env.example` and `ops/my-server/secrets/` (T8's job to wire into
deployment, this plan just adds the app-level setting + docs).

**S6 dashboard integration** (new, isolated per §45.1 — not folded into
`app/services/metrics/`, which stays Tamiyo-Scroll-only per its own
docstring):

- `app/services/karn_tablets/dashboard.py` — `get_latest_deck_type_
  distribution(session, window_type) -> KTDeckTypeDistribution | None`,
  reads the most recent `KTClusteringRun` for the requested window type and
  its clusters. Pure read, no clustering logic here (that lives in
  `apps/karn_tablets` itself).
- New route on the existing `app/api/tamiyo_scroll/admin.py`:
  `GET /admin/metrics/karn-tablets?window=rolling_30d|banlist_period`,
  same `AdminUser` gate as the existing two admin routes, same
  dataclass→Pydantic response-schema mapping pattern
  (`app/schemas/responses_tamiyo_scroll.py`).

## New app: `apps/karn_tablets`

Scaffolded exactly like `apps/barrins_scripture` (uv-managed,
`requires-python = ">=3.14"`, `setuptools`/`setuptools_scm`, pytest +
pytest-cov with the same `fail_under` bar, `scripts/workflow_ci.py` mirrored
from either sibling app):

```
apps/karn_tablets/
├── pyproject.toml          # deps: scikit-learn, httpx (call barrins_api)
├── README.md / CHANGELOG.md
├── karn_tablets/
│   ├── __main__.py         # CLI: `cluster --window rolling|banlist_period`
│   ├── windowing.py        # rolling_window()/banlist_period_window()
│   ├── client.py           # httpx calls to the two internal routes
│   ├── vectorize.py        # BSDeckCard rows -> card-count feature vectors
│   ├── clustering.py       # scikit-learn Agglomerative/DBSCAN wrapper
│   └── pipeline.py         # orchestrates: fetch -> vectorize -> cluster
│                           #                   -> aggregate -> POST
└── tests/
```

`pyproject.toml [project.scripts]`: `cluster = "karn_tablets.__main__:main"`.

**`windowing.py`** is the task T6's own page flags as highest bug-risk
(month/year rollover): `banlist_period_window(as_of: date) -> DateRange`
computes "last Tuesday of the current-or-previous odd month → last Monday of
the following odd month" — needs explicit unit tests for December→January
rollover and every odd-month boundary, per T6's non-regression-test
requirement.

**`clustering.py`**: card-count vectors (mainboard only — sideboard
composition varies too much run-to-run to cluster on, matching how
archetype identity is conventionally defined) run through scikit-learn
`AgglomerativeClustering` (no fixed `n_clusters`, distance-threshold mode) —
avoids having to guess how many archetypes exist in a given window.

## Frontend: `apps/tamiyo_scroll`

- `src/api/admin.ts` — add `getKarnTablesDistribution(window)` alongside the
  existing two functions, validated against a new Zod schema in
  `src/schemas/tamiyoScroll.ts`.
- `src/hooks/useAdmin.ts` — add `useKarnTabletsDistribution(window)`,
  TanStack Query, same `enabled: currentUser?.role === 'admin'` guard as
  the existing hooks.
- `src/pages/AdminMetricsPage.tsx` — new section below the existing
  time-bucketed charts: a `recharts` `PieChart` (or stacked `BarChart`) of
  deck-type share, with a mode switch (rolling 30-day / banlist-period)
  using the same `Tabs` component already used for day/week/month
  granularity. No new charting dependency — `recharts` is already in
  `package.json` (added for S6).

## Verification

- Backend: `uv run pytest` in `apps/barrins_api` (new tests for the two
  internal routes — 401/503 on bad/missing token mirroring
  `tests/scripture/test_ingest.py`, and the new admin route — 403
  non-admin/200 admin mirroring `test_admin_metrics.py`) and in
  `apps/karn_tablets` (windowing boundary tests, a fixture-based clustering
  test asserting a known expected grouping, a metadata-presence test per
  T6's non-regression-test list). `uv run ty check` in both.
- Frontend: existing `AdminMetricsPage` test file extended for the new
  section; `npm run typecheck`/lint in `apps/tamiyo_scroll`.
- Manual UAT (per T6's page): run `karn_tablets cluster --window rolling_30d`
  against staging `bs_*` data (real, since T3 has landed real data),
  confirm `GET /admin/metrics/karn-tablets` reflects it and the
  `AdminMetricsPage` chart matches a manual sanity check against known meta
  decks for that window; repeat for `banlist_period` and confirm switching
  modes changes the included matches.
