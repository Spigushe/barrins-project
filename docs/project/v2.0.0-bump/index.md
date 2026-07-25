# v2.0.0 — Tolaria News, Tamiyo Scroll Expansion & Ecosystem Hardening

**Project orientation for the upcoming weeks/months.** This document is
the foundation for every work item below — read it before picking up any
individual item.

Internal project tracking, not part of the public docs site
(`docs.barrins-codex.org`): like `docs/project/first_production_release/`,
this directory lives outside `docs/content/` (mkdocs' `docs_dir`), so it
isn't built or published, only version-controlled and reviewed via PR.

**Status of this document**: planning draft. Several items below are
**open architectural questions, not decisions** — per Constitution §16.2
("never guess requirements... changing deployment architecture,
introducing a dependency, handling secrets"), each is written in the
Context/Alternatives/Trade-offs shape used by `architecture/decisions.md`
so it can be turned into an ADR once the user picks an option. Nothing in
this document should be read as "already decided" unless explicitly
marked so.

---

## 0. What's verified before writing this plan

Everything below was confirmed directly against the repositories on
2026-07-25, not assumed:

- `Spigushe/barrins-project` (`staging` branch): `apps/barrins_api`
  (FastAPI) + `apps/tamiyo_scroll` (React/Vite) are the only apps with
  real code. `apps/tolaria_news` contains only a one-line `README.md` and
  a placeholder `CHANGELOG.md` — confirmed via the repo, matching what
  `docs/content/ops/roadmap.md` already states. `apps/barrins_identity`
  likewise has only a `README.md`/`CHANGELOG.md`, no application code.
- `ops/my-server/tolaria_news.yml` already exists and explicitly notes
  in its own comments that `apps/tolaria_news` "currently has no
  application code (README.md only)". It deploys `apps/tolaria_news`
  **from this same monorepo** (`react_frontend_repo_subdir:
  apps/tolaria_news`), not from a separate repository — this matters for
  §1 below, since it means Tolaria News is expected to live in-repo, not
  as an external service.
- `docs/content/back/barrins_api/bff/tamiyo_scroll.md` (the Tamiyo Scroll
  BFF implementation plan) explicitly describes the scraped-tournament
  domain as a **separate, pre-existing thing** ("mirroring the `dl_`
  prefix used by `docs/decklist_integration/` for the scraped tournament
  domain", "Same router/service separation as `tolaria_news`
  (`docs/tolaria_news/00_plan_general.md`)"). Neither
  `docs/decklist_integration/` nor `docs/tolaria_news/00_plan_general.md`
  exist anywhere in the repository (checked by full-repo search). Nor do
  `dl_decks`/`dl_tournaments` ORM models — `apps/barrins_api/app/models/`
  only contains `tamiyo_scroll.py`, `user.py`, `email_verification.py`,
  `base.py`, `_types.py`. **The scraped-tournament data domain does not
  exist in code today.** It's referenced as if it already existed, but it
  doesn't — see item **F7** below.
- `mtg_scraper` (public, `barrins-project/mtg_scraper`) is a real,
  working Python 3.13 scraper (MTGO + MTGTop8 sources), run daily via
  GitHub Actions (`.github/workflows/daily_scraping.yml` +
  `biweekly_check_gaps.yml`). It writes JSON output into a `scraped/`
  git submodule pointing at `mtg_decklist_cache`, and pushes commits to
  that submodule directly from CI (`secrets.PAT_TOKEN`) — **there is no
  database in this pipeline today.**
- `mtg_decklist_cache` (public, `barrins-project/mtg_decklist_cache`) is
  a pure JSON-file archive, organized `<source_domain>/<year>/<month>/
  <day>/<slug>.json` (e.g. `mtgo.com/2026/03/23/legacy-league-2026-03-
  2310381.json`). This **already is** the "save scrapes as JSON so they
  can be replayed" mechanism the user asked about in §1 — it's not a new
  idea, it's the current system of record, just not queryable by an API
  yet.
- `barrins-project/tolaria_news` (the third connected repo listed in the
  request) returns **HTTP 404** — it does not exist, or is private with
  no public landing page. It could not be cloned or read. Nothing below
  is based on its contents; if it exists privately, its content is
  unknown to this plan.
- "Karn Tablets" and "Barrin's Scripture" appear nowhere in the
  `barrins-project` repository, its docs, or its constitution
  (`docs/content/CLAUDE.md`, 2270 lines, checked). These are new names
  introduced in this conversation, not carried over from prior planning.
  The same is true of **"Goblin Guide"** (the future frontend for
  Barrin's Identity) — not found anywhere in the repo either. Barrin's
  Identity itself *is* already named in
  `docs/content/back/barrins_identity/platform.md`, but only as a
  "Future consideration," with no committed timeline before now.
- `apps/tamiyo_scroll/src/components/layout/SharingControls.tsx`
  **already exists**, fully built and tested
  (`SharingControls.test.tsx`), but is gated off by a
  `const SHARING_ENABLED = false` constant
  (see `docs/project/first_production_release/a2-sharing-extraction/`).
  The backend enforcement (`ownership.resolve_owner`,
  `ts_user_settings.data_shared`) is live and has its own test suite
  (127 tests total for the Tamiyo Scroll BFF). This is highly relevant
  to item **2.5** below — re-enabling read-only sharing is mostly
  already done.
- Every app is currently at `1.0.0`, released 2026-07-24
  (`docs/CHANGELOG.md`, `apps/*/CHANGELOG.md`), one version number shared
  across the monorepo.

---

## 1. Scope decisions requiring the user's input before work starts

These follow the same escalate-don't-guess pattern as
`architecture/decisions.md`'s ADRs. None are answered definitively here.

### 1.1 Where does Barrin's Scripture's code live, relative to `mtg_scraper`?

**Context.** The request describes "Backend service: `barrins_scripture`
under `apps/barrins_scripture`" — i.e. inside the `barrins-project`
monorepo, the same pattern `tolaria_news` already follows. But the
scraping code that actually exists today is a **separate, standalone
public repository** (`barrins-project/mtg_scraper`), with its own CI,
its own submodule (`mtg_decklist_cache`), its own versioning
(`CHANGELOG.md` at `0.2.0`).

**Alternatives.**

1. Merge `mtg_scraper`'s code into the monorepo at `apps/barrins_scripture`
   (via `git subtree`/`filter-repo` to preserve history), retire the
   standalone repo (archive it, redirect its README), and either keep
   `mtg_decklist_cache` as an external submodule or fold its role into
   the new service.
2. Keep `mtg_scraper` as its own repository (rename it
   `barrins-project/barrins_scripture` on GitHub), and have the monorepo
   reference it the way `ops/my-server/` references any external
   dependency — no `apps/barrins_scripture` folder in the monorepo at
   all, just a deployment playbook that clones the external repo.
3. Treat `apps/barrins_scripture` in the monorepo as a **new**
   implementation that supersedes `mtg_scraper` (a rewrite, not a
   migration), and archive `mtg_scraper` once feature parity is reached.

**Trade-offs.** Option 1 matches the literal wording of the request
("under `apps/barrins_scripture`") and the precedent already set by
`tolaria_news`, but is real migration work (history-preserving merge,
CI workflow rewrite from a per-repo GitHub Actions setup into whatever
this monorepo's `.github/workflows/CI.yml` does) and means losing
`mtg_scraper`'s independent release cadence. Option 2 is the least
migration work but contradicts the "under `apps/barrins_scripture`"
framing and the `tolaria_news` precedent, and keeps a second,
differently-structured CI/release process alongside the monorepo's own.
Option 3 avoids a risky history-rewrite but throws away a working,
already-scheduled, already-tested (0.2.0, several bugfix releases)
scraper and re-derives its logic from scratch.

**Not decided.** This blocks every other Barrin's Scripture item.

### 1.2 Does Barrin's Scripture get direct database access?

*This is the question the user asked to be formulated, not answered
unilaterally — presented in the same shape as the existing ADRs.*

**Context.** Barrin's Scripture's job is scrape → normalize → persist.
Constitution §4.1 ("Backend owns business logic") and §26.1 ("one
application, one playbook", independent deployability) both push toward
keeping data-model ownership inside `barrins_api`, which is already the
sole owner of every other domain table (`users`, `ts_*`). Constitution
§13.1 ("do not create application-specific user tables") is precedent
for "one app owns identity" that generalizes naturally to "one app owns
the schema."

**Alternatives.**

1. **Barrin's Scripture holds its own `DATABASE_URL` and writes directly**
   to `dl_*`-style tables it also owns/migrates.
2. **Barrin's Scripture never touches Postgres.** It scrapes, writes the
   JSON archive (as today), and calls a private, backend-only ingestion
   route on `barrins_api` (e.g. `POST /internal/scripture/ingest`,
   authenticated by a service credential, never exposed to any frontend)
   that performs the actual insert/upsert. `barrins_api` remains the sole
   owner of the schema and its Alembic migrations.
3. Barrin's Scripture writes to a **separate database/schema** it owns,
   and `barrins_api` reads from it (via a read replica, a foreign data
   wrapper, or a second `DATABASE_URL` configured read-only) to serve the
   Tolaria News BFF.

**Trade-offs.**

- Option 1 is the simplest data path (no extra HTTP hop) but duplicates
  what §26.1's "one application, one playbook" already warns against for
  infrastructure, applied here to schema ownership: two codebases
  (`barrins_api`'s Alembic and Barrin's Scripture's own migration
  tooling) would both need to agree on the same tables' shape, and a
  schema change in one has to be coordinated with the other by hand. It
  also means shipping a second Postgres credential with write access to
  production data to a scheduled scraper — a wider secret-exposure
  surface than today's single `barrins_api` `.env` (ADR-1's model).
- Option 2 keeps exactly one thing (`barrins_api`) owning the schema and
  the migrations, consistent with every other domain in this project
  (`users`, `ts_*`) and with `signup_email_verification.md`'s existing
  pattern of a dedicated internal service boundary. It costs one more
  internal-only route and a service-to-service credential (same shape as
  the already-existing `github_token`/Moxfield-credential precedent:
  narrow-scope, backend-only, never reaching a browser). It also means
  Barrin's Scripture can be redeployed, rolled back, or reworked without
  ever needing a database migration of its own.
- Option 3 avoids any HTTP coupling but introduces a second database (or
  schema) to operate, back up (Constitution §36 already flags backups as
  a real operational cost — a second DB doubles that surface), and
  monitor, for a marginal benefit over option 2's single extra route.

**Recommendation** (not a decision — flagged as such): **Option 2**,
because it's the one that requires zero new infrastructure, matches
every existing precedent in this codebase for "who owns the database,"
and keeps Barrin's Scripture exactly as replaceable/independently
deployable as `tolaria_news` or `tamiyo_scroll` are today. This still
needs the user's sign-off before being written up as an ADR.

### 1.3 Should scrapes still be archived as JSON, outside the database?

**Answering the specific question asked**: yes — but this isn't a new
requirement to design, it's the **existing** behavior of
`mtg_scraper`/`mtg_decklist_cache`, which already writes every scrape to
a JSON file, committed to git, before (today: instead of) any database
write. Whatever Barrin's Scripture becomes, keeping this archive is cheap
(it's already built, tested in production since well before this
conversation) and gives exactly the "replay after a server issue"
property asked for: the DB can be dropped and fully rebuilt by replaying
the JSON archive through the ingestion path (§1.2 option 2's route, or
a bulk-load script). The only open question is **where** that archive
lives once Barrin's Scripture moves (§1.1) — as the same `mtg_
decklist_cache` git submodule, or migrated to object storage (e.g. the
VPS's disk, rotated like `postgres_backup`'s dumps) if the git-submodule
approach doesn't scale as scrape volume grows. Not urgent for v2.0.0;
flagged for the person doing item **T3** to confirm before writing code.

### 1.4 Karn Tablets' scope for v2.0.0

**Context.** The request describes Karn Tablets as "the backend service
in charge of computing/providing ML and DL data" with no further detail,
and no prior planning for it exists anywhere in the repository or
constitution.

**Recommendation**: scope Karn Tablets **out of v2.0.0's delivered
features**, and instead land only the parts that don't block on it:

- The scraped-tournament schema (§1.2's outcome) is designed so Karn
  Tablets can read from it later without a breaking change (Constitution
  §39: "anticipate future features... without implementing them
  prematurely").
- A placeholder `apps/karn_tablets/README.md` + a docs stub under
  `docs/content/back/karn_tablets/`, exactly like `apps/tolaria_news` and
  `apps/barrins_identity` exist today as intent-only placeholders.

A full ML/DL service is a substantial, open-ended scope (model choice,
training data volume, inference hosting, a fourth backend to secure and
monitor) that risks absorbing the whole release if pulled in now. This is
a recommendation, not a decision — confirm before treating Karn Tablets
as "placeholder-only" for v2.0.0.

### 1.5 Shared identity — carried over from the current roadmap, still open

Already flagged in `docs/content/ops/roadmap.md` before this plan existed:
Constitution §13.1 requires one account across every application;
`barrins_identity` is unmerged. Adding **two** more applications this
release (Tolaria News frontend, and Team accounts for Tamiyo Scroll,
§2.1 below) makes this decision more urgent, not less — every new
"multi-user" feature (team membership, cross-app login) is easier to
build once, correctly, than twice. **This is the single most
schedule-critical open decision in this plan** — items T5, T7, S2 and
S1's "toggle to receive" extension all touch identity in some way.

### 1.6 How are Teams created and who can create one? (item 2.1)

**Context.** The request flags this explicitly as undecided ("Need to
workout how the team is created"). No existing concept of a group/team
exists anywhere in the schema — `ts_*` tables are all single-owner.

**Alternatives.**

1. Any authenticated user can create a team and becomes its first
   member/owner; other users join via an invite code or a direct add by
   the team owner.
2. Teams are admin-provisioned only (matches `docs/content/back/
   barrins_api/auth_roles.md`'s existing admin/user role split, if
   team creation is judged sensitive enough to gate).
3. Defer "team" as its own entity entirely, and instead reuse the
   **existing** read-only sharing primitive (`ts_user_settings.
   data_shared`, already live) extended to a **set** of viewers instead
   of "anyone who knows to look" — i.e. no new `teams` table, just a
   `ts_share_grants` table (`owner_id`, `viewer_id`) replacing today's
   single boolean.

**Not decided.** Option 3 is the cheapest to build (extends an
already-tested mechanism rather than inventing a new entity) but doesn't
give a "Team Decks" selector a real group identity to filter on unless a
lightweight `ts_teams`/`ts_team_members` pair is added on top — likely
still needed for item 2.1's "Team Decks" selector regardless of which
option is chosen for creation semantics. Flagged for confirmation before
S2 starts.

### 1.7 Admin usage/metrics dashboard for Tamiyo Scroll

**Confirmed by the user since this was first scoped**: the metrics
portal itself must be available starting **v2.0.0** — but it is a
**v2.0.0-only interim shape**. Long-term, it externalizes into its own
standalone application, covering every publicly-deployed frontend (not
just Tamiyo Scroll), gated through a dedicated user-management pair:
**Barrin's Identity** (backend — already named in
`docs/content/back/barrins_identity/platform.md` as a future
consideration, not yet built) and **Goblin Guide** (frontend for it —
a name introduced in this conversation, appearing nowhere in the
repository, its docs, or the constitution before now, exactly like
Barrin's Scripture and Karn Tablets before it). Both are **explicitly
v3.0.0-scoped by the user — not to be embarked before then.** This
resolves one narrow piece of open question §1.5 (shared identity): for
*this specific feature*, v2.0.0 does not wait on `barrins_identity`.
Tolaria News' own auth and Tamiyo Scroll's team-sharing (§1.6) are
**not** resolved by this — they're a separate question, still open.

**What this means concretely for v2.0.0's scope**:

- The dashboard ships **embedded** in the existing apps for v2.0.0:
  backend routes live in `barrins_api` (not a new service), the UI lives
  in `apps/tamiyo_scroll` (not a new frontend), and admin access is
  gated by the **existing** `AdminUser`/`require_role(UserRole.admin)`
  mechanism already described above — no new auth system for v2.0.0.
- No premature app scaffold: unlike Barrin's Scripture/Karn Tablets
  (§1.1–1.4), there is **no `apps/`-level placeholder to create now**
  for the future standalone metrics app, Barrin's Identity, or Goblin
  Guide — all three are v3.0.0 work, out of scope for the
  `proj/v2.0.0-bump` branch entirely. (Whether `barrins_identity`'s
  existing README/CHANGELOG-only placeholder needs any update to mention
  Goblin Guide is a documentation nicety, not a blocker — not addressed
  here.)

**What v2.0.0's implementation needs to anticipate, per Constitution
§39** ("anticipate future features... without implementing them
prematurely" — simple today, extensible tomorrow), so the v3.0.0
externalization doesn't force a rewrite:

1. **Keep metrics computation as its own service module**
   (e.g. `app/services/metrics/`), not inlined into
   `app/services/tamiyo_scroll/` — a module boundary costs nothing now
   and is what actually gets lifted out wholesale when this becomes its
   own application later.
2. **Design the aggregated data with an app/source dimension from day
   one**, even though v2.0.0 only ever populates it with one value
   (`tamiyo_scroll`) — retrofitting a "which app is this metric about"
   column after Tolaria News and others start feeding the same rollup is
   exactly the kind of avoidable rework §39 is about. This does not mean
   building a multi-app aggregation *pipeline* now (YAGNI, Constitution
   §39/§48) — just not modeling the single-app case in a way that has to
   be undone.
3. **Don't couple the metrics routes' authorization directly to
   `barrins_api`'s specific role enum** any more than necessary — the
   v3.0.0 version authenticates admins via Barrin's Identity/Goblin
   Guide instead, a different provider. Depending on `AdminUser` (the
   convenience alias) is fine for v2.0.0; scattering direct
   `UserRole.admin` checks through the route bodies (rather than through
   the one dependency) would make the later swap harder than it needs to
   be.

**Still open, unchanged from before**: what "métrique" concretely means
(assumed: product/usage analytics — signups, active users, decks,
matches, sharing adoption — see the options considered above) and the
absence of any privacy/data-retention policy in the constitution. Neither
is resolved by the v2/v3 split; both still need confirmation before
S6 starts.

**Options considered for "métrique," restated for context**:

1. **Product/usage analytics**: signups over time, active users
   (daily/weekly), personal decks created, matches logged, card-tests
   submitted, sharing adoption (`data_shared` opt-in rate) — all
   derivable from existing `ts_*`/`users` tables with aggregate queries,
   no new data collection needed. *(Assumed default, unconfirmed.)*
2. **Operational/infrastructure metrics**: request latency, error rates,
   endpoint call volume — this overlaps with, and would likely duplicate,
   the existing HetrixTools setup (`operations/index.md`) rather than
   extend it; Constitution §4.2 ("no duplicated business logic")
   arguably generalizes to "no duplicated monitoring surface." If this is
   what's meant, it may belong in Group D (ops tooling) rather than as a
   Tamiyo Scroll admin page.
3. **Per-user moderation/support view** (e.g. "which accounts exist,
   when did they last log in") — touches account data more directly than
   1 or 2, and has sharper privacy implications.

**A gap worth naming plainly**: this project's constitution
(`docs/content/CLAUDE.md`, 2270 lines, checked) contains no privacy,
data-retention, or analytics policy at all — no section addresses
whether/how aggregate user data may be collected, retained, or shown to
admins. That's not a blocker for option 1 above (it aggregates data the
backend already holds for its normal function, nothing new is collected),
but it is a real, currently-undocumented gap that a dedicated admin
metrics *page* makes more visible than the data merely existing in the
database already did — and one that matters more, not less, once a
future *separate* application (with its own operator/access surface)
is the one showing it in v3.0.0. Worth a short written policy alongside
this feature, even if brief, rather than shipping it silently.

**Architecture for v2.0.0**: a new BFF sub-router
(`app/api/tamiyo_scroll/admin.py`, since v2.0.0 is explicitly
Tamiyo-Scroll-scoped per the user and the future cross-app version is
v3.0.0's job, not this one's), gated by `AdminUser`, calling into the new
`app/services/metrics/` module (point 1 above) which computes aggregates
server-side (Constitution §4.1/§4.2 — no raw data dump to the frontend
for it to compute on), plus a new admin-only route and page in
`apps/tamiyo_scroll`.

---

### 1.8 Tutorial / demo interface for Tamiyo Scroll, no persistence

**Decided by the user**: option 1 (pure frontend, in-memory, no network
calls) — and demo + tutorial ship as **one single interface**, not two
separate deliverables or a fast-follow. Fixture data is authored in a
JSON file. Restated below with the decision folded in; the alternatives
considered are kept for the record.

**Request restated precisely**: a tutorial and demo interface, in one,
with pre-filled sample data from a JSON file, so visitors can discover
the app — explicitly **no persistence** of anything added during that
session.

**What exists to build on.** Routing is a plain `react-router-dom`
`<Routes>` tree in `App.tsx`; every real screen
(`MetagameTab`/`SuiviBo3Tab`/`DecklistTab`) is already wrapped
individually in `<ProtectedRoute><AppShell>...` — nothing else gates
access today besides that one component
(`components/layout/ProtectedRoute.tsx`, ~10 lines: redirects to
`/login` if `session.accessToken === null`). Every data-fetching hook
(`usePersonalDecks`, `useMatches`, `useMetaDecks`, `useCardTests`,
`useStats`, ...) is a thin TanStack Query wrapper around one of the
`src/api/*.ts` modules, which all funnel through the single
`src/api/client.ts`. There is currently no mocking layer in the
production dependency tree (`package.json` has no MSW or equivalent —
only `vitest`/`@testing-library/*`, dev-only).

**Confirmed design**:

- A parallel data-source module mirrors each `src/api/*.ts` file's
  function signatures (the shapes the existing hooks already expect),
  backed by fixture data loaded once from a single JSON file (e.g.
  `src/demo/fixtures.json`, a static import — Vite/TypeScript both
  support importing `.json` directly, no runtime `fetch` needed) and
  held afterward in local component/context state, reset fresh on every
  page load. A `DemoModeProvider` (or equivalent context) supplies this
  module in place of the real one; the existing tab components
  (`MetagameTab`, `SuiviBo3Tab`, `DecklistTab`) render **unmodified**
  against whichever source is active — the demo reuses the real UI, it
  doesn't fork it.
- The demo/tutorial route (e.g. `/demo`) is fully public — no
  `ProtectedRoute`, no token ever issued, no call to `barrins_api` at
  any point. This is what makes "no persistence" a structural guarantee
  rather than an operational promise: there is nothing to reset,
  isolate, or leak between visitors, because nothing ever leaves the
  browser tab.
- One single interface, confirmed: the guided tutorial is presented
  through the same seeded demo screens (e.g. a step/tooltip overlay
  pointing at the pre-filled data already on screen) rather than as a
  separate walkthrough or a second route — one PR, one experience.

**Alternatives considered before this was decided** (kept for context,
not live options anymore):

- **Real backend, a dedicated sandbox account whose writes get
  discarded** (scheduled reset or per-request rollback) — rejected:
  turns "no persistence" into an operational promise, has cross-visitor
  collision risk on a shared account, and is the first feature in this
  plan that would need a publicly reachable, unauthenticated **write**
  path into the real backend, against the spirit of Constitution
  §33/§34 (restrictive CORS, minimal exposed surface).
- **Real frontend, server-side ephemeral session store** — rejected:
  real new backend infrastructure (session store, expiry job) for a
  feature whose entire purpose is onboarding, not core product logic.

**Remaining open points** (not yet decided, listed so they aren't lost):

- Exact fixture content for `fixtures.json`: enough sample decks,
  matches, and card-tests across all three tabs to make the tour
  meaningful — invented for this purpose, never real user data, never
  derived from any real account.
- Entry point: most likely a link from `LoginPage` (which already has a
  footer line, "Account managed by `barrins_api`") — e.g. "Try the demo"
  — and/or from `RootRedirect` in `App.tsx`, which today sends every
  unauthenticated visitor straight to `/login` with no alternative
  offered.

**Decided**: the guided-tour overlay is hand-rolled with the existing
Radix/shadcn primitives already in `src/components/ui/`
(`popover.tsx`, `dialog.tsx`, `card.tsx`, ...) — no new dependency. This
also settles the Playwright question raised for this item (see the note
right after this section): a dedicated tour library was the only
plausible reason to bring Playwright into the demo/tutorial work, and
that path is no longer taken.

---

### A note on Playwright — deferred, not part of v2.0.0

Playwright was suggested to the user during this planning process. It
doesn't fit item S7 (it's a browser-automation/E2E-testing framework,
not a tour-UI library — the primitives decision above settles that
question). Two other places in this project could plausibly use it,
and the user asked for a judgment call on each rather than a blanket
yes/no:

1. **A committed, CI-integrated E2E suite for `apps/tamiyo_scroll`.**
   Real value here isn't hypothetical: Playwright was already used
   informally during the original bootstrap
   (`docs/content/front/tamiyo_scroll/bootstrap.md` — "disposable
   Playwright scripts in the scratchpad" for phase 6-9 validation, and
   again for the 2026-07-16 regression check), and that same doc
   explicitly deferred committing it ("E2E can follow separately").
   Today, `.github/workflows/CI.yml`'s `front` job only runs
   `lint`/`build`/`npm test` (Vitest/Testing Library, unit+component) —
   no browser is ever launched in CI. Making this real means: adding
   `@playwright/test`, a browser-download step
   (`npx playwright install`), a new CI job that also needs
   `barrins_api` + Postgres running and a built frontend to point at
   (heavier than the existing `back` job, which only needs Postgres),
   and writing the scenarios themselves (signup, deck creation, match
   logging, sharing) — real, non-trivial work, not just configuration.
   **Judgment: defer, don't cancel.** It has already demonstrated value
   informally twice; v2.0.0's scope (three candidate new applications,
   several open architecture decisions) is heavy enough without also
   absorbing a first CI-integrated browser-test pipeline. Revisit as a
   dedicated item once v2.0.0's application-level work is further along
   — tracked here so it isn't lost, not scheduled.
2. **Replacing Selenium in the MTGO scraper** (relevant only once item
   T1's repo-migration decision lands). Contained footprint today: 4
   files, ~292 lines (`scraper/utils/selenium_driver.py`,
   `scraper/services/mtgo.py`, `scraper/utils/mtgo.py`), MTGO-only
   (MTGTop8 scraping doesn't use a browser at all). No open bug or pain
   point currently documented against Selenium in `mtg_scraper`'s
   `CHANGELOG.md` beyond one already-fixed reliability issue (0.2.0).
   **Judgment: defer, low priority.** Modernizing tooling with no active
   pain point isn't worth doing ahead of, or bundled into, the
   already-nontrivial T1 migration decision — if T1 lands on "merge into
   the monorepo" and whoever does that work wants to swap Selenium for
   Playwright at the same time, nothing here rules it out, but it isn't
   requested or required for v2.0.0.

Neither is part of the `proj/v2.0.0-bump` scope. Both are recorded here,
not in Group T/S's tables, specifically so they read as deferred
background context rather than committed work items.

---

## 2. Priorities and dependency graph

Work is grouped by theme (mirroring the `A`/`B` lettering convention from
`docs/project/first_production_release/`). Letters don't imply strict
sequential order within a theme, but the dependency column does.

### Group I — Foundational decisions (block everything else)

| # | Item | Depends on | Blocks |
| --- | --- | --- | --- |
| I1 | Resolve shared-identity approach (§1.5) | — | T5 (transitively, T7), S1 (receive-toggle), S2 |
| I2 | Resolve Barrin's Scripture repo location (§1.1) | — | T1–T3 |
| I3 | Resolve Barrin's Scripture DB-access model (§1.2) | I2 | T2, T3 |
| I4 | Confirm Karn Tablets v2.0.0 scope (§1.4) | — | T6 |
| I5 | Confirm Team creation model (§1.6) | — | S2 |
| I6 | Confirm what "metrics" means for the admin dashboard, and confirm the v2.0.0-embedded / v3.0.0-externalized split (§1.7) | — | S6 |

**Nothing else in this document should start implementation before its
row in this table is resolved.** This mirrors how v1.0.0 itself required
resolving the backup-gating and monitoring-provider questions (ADR-4)
before B1/B6 could start.

### Group T — Tolaria News, Barrin's Scripture, Karn Tablets (request item 1)

| # | Item | Depends on | Notes | Page |
| --- | --- | --- | --- | --- |
| T1 | Migrate/create `apps/barrins_scripture` per I2's outcome | I2 | Includes retiring or repointing `mtg_scraper` | [t1-scripture-repo-migration/](t1-scripture-repo-migration/index.md) |
| T2 | Design the scraped-tournament schema in `barrins_api` (the "`dl_*`" domain referenced but never built — see §0, F7) | I3 | This is genuinely new work, not a resurrection of hidden code | [t2-scraped-tournament-schema/](t2-scraped-tournament-schema/index.md) |
| T3 | Build the scrape → JSON-archive → ingest pipeline per I3's outcome | T1, T2 | Keeps the existing `mtg_decklist_cache`-style JSON archive (§1.3) | [t3-scripture-ingestion-pipeline/](t3-scripture-ingestion-pipeline/index.md) |
| T4 | Tolaria News BFF routes (`/api/v1/tolaria-news/...`), publicly readable, no `CurrentUser` requirement — already anticipated by a comment in `bff/tamiyo_scroll.md` ("unlike the Tolaria News BFF which is publicly readable") | T2 | Follows the same router/service-package pattern as the Tamiyo Scroll BFF | [t4-tolaria-news-bff/](t4-tolaria-news-bff/index.md) |
| T5 | `apps/tolaria_news` real frontend (React/Vite), calling `barrins_api`'s BFF only — no direct DB/calculation client-side, per §4.1/§4.2 | T4, I1 | `ops/my-server/tolaria_news.yml` already exists and is ready to deploy real code once this lands | [t5-tolaria-news-frontend/](t5-tolaria-news-frontend/index.md) |
| T6 | `apps/karn_tablets` placeholder scaffold per I4 | I4 | README + docs stub only, unless I4 is revisited | [t6-karn-tablets-scaffold/](t6-karn-tablets-scaffold/index.md) |
| T7 | Docs: `docs/content/back/barrins_scripture/`, `docs/content/back/karn_tablets/` (stub), real content for `docs/content/front/tolaria_news/_links.md` | T1, T4–T6 | Follow the existing per-app docs pattern (`_links.md` + synced README) | [t7-new-apps-docs/](t7-new-apps-docs/index.md) |
| T8 | Deployment playbooks for Barrin's Scripture (scheduled job, not a web service) and Karn Tablets (ML service) | T1, T6, D1 | See Group D — these don't fit the existing `fastapi_backend`/`react_frontend` role shapes | [t8-scripture-karn-playbooks/](t8-scripture-karn-playbooks/index.md) |

### Group S — Tamiyo Scroll changes (request item 2)

| # | Item | Depends on | Notes | Page |
| --- | --- | --- | --- | --- |
| S1 | Re-enable + extend global sharing (request 2.5) | — (I1 only for the new "toggle to receive" half) | Cheapest item in this plan: `SharingControls.tsx` and its backend are already built and tested. The "share" toggle already exists (`data_shared`). The "toggle to receive" half is new — no such concept exists today (any user can currently view any sharer without opting in on their own side) | [s1-global-sharing-reenable/](s1-global-sharing-reenable/index.md) |
| S2 | Team sharing: read-only "Team Decks" selector + flag-to-share | I5, S1 | Builds on S1's mechanism once teams exist | [s2-team-sharing/](s2-team-sharing/index.md) |
| S3 | Auto-flag match result to a specific decklist version, editable after | — | Schema change: add nullable `decklist_version_id` FK to `ts_matches`, defaulting to the deck's currently-active version at creation time (`ts_user_settings.active_personal_deck_id`'s sibling concept, per-deck). Small, unblocked, can start immediately | [s3-match-decklist-version/](s3-match-decklist-version/index.md) |
| S4 | Better decklist display (request 2.3, "UI TBD") | — | No technical blocker — needs a design pass before implementation, same "hifi design first" pattern `handoff.md` used for the original build | [s4-decklist-display-redesign/](s4-decklist-display-redesign/index.md) |
| S5 | PDF report of a training session for a specific deck | S3 (report is more useful once matches carry a version reference) | Backend-generated (Constitution §4.1: no client-side composition of computed stats) — needs a PDF-generation library choice for `barrins_api` (e.g. WeasyPrint or ReportLab), which is itself a new dependency requiring the same escalation Constitution §16.2 already requires for "introducing a dependency" | [s5-pdf-training-report/](s5-pdf-training-report/index.md) |
| S6 | Admin metrics dashboard, embedded in `barrins_api`/`tamiyo_scroll` for v2.0.0 | — (role infrastructure already exists, see §1.7) | Confirmed v2.0.0-embedded, v3.0.0-externalized into a standalone cross-app application accessed via Barrin's Identity/Goblin Guide (not scheduled before v3.0.0) | [s6-admin-metrics-dashboard/](s6-admin-metrics-dashboard/index.md) |
| S7 | Tutorial + demo interface, combined, pre-filled from a JSON fixture file, no persistence | — | **Decided**: option 1 (pure frontend mock, no backend). See §1.8 | [s7-demo-tutorial-interface/](s7-demo-tutorial-interface/index.md) |

### Group F — Fixes flagged in docs and roadmap (request item 3)

**Carried over from `docs/content/ops/roadmap.md`'s existing "should
fix"/"pre-existing gaps" sections** (unchanged by this plan, restated
here for completeness):

| # | Item | Source | Page |
| --- | --- | --- | --- |
| F1 | HetrixTools free-tier 2-tracker cap — now more urgent: this release adds up to 2 more deployable services (Tolaria News frontend, Barrin's Scripture) on top of the existing `tamiyo_scroll` gap | `roadmap.md`, ADR-4 | [f1-hetrixtools-cap/](f1-hetrixtools-cap/index.md) |
| F2 | Release cutting is fully manual (ADR-2's flagged gap) — more repos/tags this release makes this worse | `roadmap.md`, ADR-2 | [f2-release-automation/](f2-release-automation/index.md) |
| F3 | Changelog aggregation heading-level bug in `docs/hooks/sync_changelogs.py` — every new app added (Tolaria News, Barrin's Scripture, Karn Tablets) hits this again | `roadmap.md` | [f3-changelog-heading-bug/](f3-changelog-heading-bug/index.md) |
| F4 | nginx security headers (HSTS, etc.) not implemented | `roadmap.md`, Constitution §29.1 | [f4-nginx-security-headers/](f4-nginx-security-headers/index.md) |
| F5 | Pre-commit secret-scanning is opt-in per developer, no server-side gate | `roadmap.md`, `security/secrets.md` | [f5-precommit-secret-scanning/](f5-precommit-secret-scanning/index.md) |

**Newly found while preparing this plan** (verified directly against the
repo on 2026-07-25, not previously written down anywhere):

| # | Item | Evidence | Page |
| --- | --- | --- | --- |
| F6 | `docs/content/ops/deployment/backend.md`'s "Validation" section states "no dedicated `/health` route in `barrins_api` today" — this is stale. `GET /health` is implemented (`app/api/general/health.py`, mounted in `main.py`) and `docs/content/ops/operations/index.md`'s own "Open items summary" table correctly lists it as implemented. The two docs contradict each other. | Direct code read: `apps/barrins_api/app/api/general/router.py`, `health.py` | [f6-health-doc-fix/](f6-health-doc-fix/index.md) |
| F7 | Several files reference planning documents that do not exist anywhere in the repository: `docs/decklist_integration/`, `docs/tolaria_news/00_plan_general.md`, `docs/tamiyo_scroll_tracker/00_plan_general.md`, `docs/signup_email_verification/00_plan_general.md`, and (found while scoping S6/§1.7) `docs/auth_roles/10_deploiement.md` — cited from `docs/content/back/barrins_api/bff/tamiyo_scroll.md`, `docs/content/back/barrins_api/signup_email_verification.md`, `docs/content/front/tamiyo_scroll/bootstrap.md`, `apps/barrins_api/scripts/create_admin.py`, and from code comments in `app/services/tamiyo_scroll/*.py`, `app/models/tamiyo_scroll.py`, `app/core/security.py`, `app/services/email/*.py`. Either these were real, unpublished planning docs that were never migrated into `docs/content/` during the docs restructuring, or the paths were always aspirational. Worth a deliberate decision: recreate them under `docs/content/` (if the design decisions they're cited for still need a home) or update every citing file to stop pointing at a dead path. | Full-repo search, zero matches for any of the five paths as an existing file | [f7-broken-doc-references/](f7-broken-doc-references/index.md) |

### Group D — Deployment playbooks for new applications/services (request item 4)

| # | Item | Depends on | Notes | Page |
| --- | --- | --- | --- | --- |
| D1 | A documented **playbook template/checklist** generalizing Constitution §37/§26.1 for service *shapes* that don't exist yet in `ops/my-server/roles/` — today there's only `fastapi_backend` (web API) and `react_frontend` (static SPA). Barrin's Scripture is a **scheduled job**, not a long-running web service; Karn Tablets (whenever it's scoped) is likely a third shape again. | I2, I4 | This is the concrete deliverable behind "new applications and services will need a playbook for deployment" — a template, not a finished playbook for a service that isn't designed yet | [d1-playbook-template/](d1-playbook-template/index.md) |
| D2 | Extend monitoring (HetrixTools or its successor per F1) to cover the new service(s) | F1, D1 | | [d2-monitoring-extension/](d2-monitoring-extension/index.md) |
| D3 | Update `security/secrets.md` / `ops/my-server/secrets/README.md` for whatever new credential(s) I3 introduces (e.g. a Barrin's-Scripture-to-`barrins_api` service token) | I3 | Same "never in git" pattern as ADR-1, just documenting the new secret | [d3-secrets-docs-update/](d3-secrets-docs-update/index.md) |

### Group R — Release wrap (mirrors v1.0.0's B1–B7)

| # | Item | Depends on | Page |
| --- | --- | --- | --- |
| R1 | Finalize release content, merge `proj/v2.0.0-bump` → `staging` | All of Groups T/S/F/D above that are in scope | [r1-merge-staging/](r1-merge-staging/index.md) |
| R2 | Promote `staging` → `main` | R1 | [r2-promote-main/](r2-promote-main/index.md) |
| R3 | Tag and cut the release | R2 | [r3-tag-release/](r3-tag-release/index.md) |
| R4 | Deploy from tag (production) | R3, D1/D2 (new services need their playbooks *before* first deploy) | [r4-deploy-production/](r4-deploy-production/index.md) |
| R5 | Write the ADRs this release's decisions require (I1–I6, once resolved) | I1–I6 | [r5-write-adrs/](r5-write-adrs/index.md) |

---

## 3. Branch strategy

Same convention as v1.0.0: all work aggregates on the integration branch
**`proj/v2.0.0-bump`**, branched off `staging`. Each work item above is
its own branch/PR merging into `proj/v2.0.0-bump`. Given this release's
scope (up to three new applications, versus zero in v1.0.0), consider
whether sub-integration branches per group (e.g.
`proj/v2.0.0-bump/scripture`, `proj/v2.0.0-bump/tamiyo-scroll`) are worth
the overhead — not decided here, flagged for whoever opens the first PR.

**Same open item as v1.0.0 carries forward**: confirm
`.github/workflows/CI.yml` triggers on PRs targeting
`proj/v2.0.0-bump`, or run the equivalent local scripts per review.

---

## 4. How each work item's page is structured

Same convention as `docs/project/first_production_release/`. Every page
under a work item follows the same shape:

1. **Done statement** — concrete acceptance criteria.
2. **Tasks** — the implementation breakdown.
3. **UAT** — manual steps to be performed personally by the user to
   confirm the change is applied correctly.
4. **Non-regression tests** — systematic tests added for this item.

**One difference from v1.0.0's pages, stated plainly**: v1.0.0's pages
were written after (or during) the work, describing what was actually
done. Most of this release's pages are written **before** the work,
some for items still blocked on an open decision from §1. Those pages
say so explicitly in their **Status** row (🔲 rather than ✅) and their
Done statement is conditioned on the blocking decision rather than
describing a finished result — nothing on a blocked item's page should
be read as already implemented.

---

## 5. What this document deliberately does not do

- It does not pick a winner for any item in §1 — those are the user's
  calls, framed in the ADR shape this project already uses for exactly
  this kind of decision.
- It does not invent a UI for item S4 ("better decklist display") —
  no design exists yet to describe.
- It does not assume `barrins-project/tolaria_news` (the third connected
  repo) contains anything, since it could not be read (404).
- It does not commit to a PDF library, ML framework, or hosting choice
  for Karn Tablets — all of that is out of scope per §1.4's
  recommendation.
- It does not scope, design, or schedule the standalone metrics
  application, Barrin's Identity, or Goblin Guide themselves — all three
  are confirmed v3.0.0 work. This document only records the two
  forward-compatibility constraints (§1.7) that v2.0.0's embedded
  version needs to honor so that later externalization doesn't force a
  rewrite.

## See also

- [`../../content/ops/roadmap.md`](../../content/ops/roadmap.md) — the
  ecosystem-wide roadmap, updated alongside this plan.
- [`../../content/ops/architecture/decisions.md`](../../content/ops/architecture/decisions.md)
  — ADR-1 through ADR-4; ADRs for §1's resolved decisions should follow
  as ADR-5 onward.
- [`../first_production_release/index.md`](../first_production_release/index.md)
  — the v1.0.0 plan this document's structure is modeled on.
