# Roadmap

Tracks each release's scope after the fact, and the concrete items
carried into the next one. Written the same way
[`operations/index.md`](operations/index.md) is: honest about gaps, not
aspirational.

## v0.0.0 → v1.0.0 (finalized)

Before this release, `origin/main` contained only the initial GitHub
Pages scaffold — no application code had ever reached production, and no
release tag existed. Getting to `v1.0.0` shipped `barrins_api` +
`tamiyo_scroll` (`staging` as it stood at cut time) and required:

| Item | What it did |
| --- | --- |
| Monitoring & `/health` | Real `GET /health` with a DB-connectivity check; external uptime and certificate-expiry monitoring via HetrixTools. |
| Sharing feature extraction | Removed the immature "sharing" feature ahead of the first public release. |
| Moxfield deck import | Import a personal deck from a public Moxfield URL; the required credential is handled as a backend-only secret, never reaching the frontend. |
| Changelog split | One `CHANGELOG.md` per sub-repo, aggregated at docs-build time into the site's Changelog section. |
| Deck-selector UX rewrite | Combobox-based deck switching in Tamiyo Scroll. |
| Root README rewrite | Presentation-first root `README.md` (no misleading pre-launch links). |
| API routes reorganization | Emerged while starting the Moxfield import work. |
| `postgres_backup` role | Daily backup plus a verified restore drill — closed the Constitution §36 blocker before the first production migration ever ran. |
| Docs site deployment playbook | `docs.yml`, staging-verified before go-live. |
| Release content finalized, merged to `staging` | |
| Promoted `staging` → `main` | |
| Tagged and cut the release | `v1.0.0` tag, GitHub Release published. |
| Deployed from tag to production | `barrins_api`, `tamiyo_scroll`, and the docs site all live from the release tag. |
| ADR-4 written | Documents the backup-gating, monitoring-provider, and Moxfield-secret-handling decisions made along the way. |

The decisions made along the way are recorded in
[ADR-1 through ADR-4](architecture/decisions.md).

**Deliberately excluded from v1.0.0:**

- `barrins_identity` — mid-implementation on `feat/barrins-identity`, not
  merged into `staging`.
- `tolaria_news` — no application code yet, only
  `apps/tolaria_news/README.md`.

## v1.0.0 → v2.0.0 (known issues to resolve)

`v2.0.0`'s scope grew from "add Tolaria News" to four workstreams: Tolaria
News plus two new backend services (Barrin's Scripture — scraping;
Karn Tablets — ML/DL), a set of Tamiyo Scroll feature additions, a pass
over items already flagged as needing fixes, and a general deployment
playbook for whatever new application/service shape shows up next. Full
detail, priorities, and dependency ordering:
`docs/project/v2.0.0-bump/index.md` (internal release tracking, not part
of this published site).
This section summarizes it; that document is the source of truth for
sequencing.

Infrastructure for Tolaria News specifically is already wired ahead of
the application itself:

- `ops/my-server/tolaria_news.yml` exists (`react_frontend` role,
  release-tag mode in production, its own domain/vhost/SSL) but isn't
  runnable yet — there's no app code behind it, and its own comments say
  so.
- Domains are already reserved: `tolaria.barrins-codex.org` (production),
  `tolaria-staging.barrins-codex.org` (staging) — see
  [Frontend Deployment](deployment/frontend.md).
- [Rollback](deployment/rollback.md) is already documented for when it
  does ship.

### Blocking — nothing below can start until these are resolved

1. **No application code exists yet** for `apps/tolaria_news`. Needs a
   real implementation before `tolaria_news.yml` becomes runnable.
2. **Shared-identity decision is undecided.** Constitution §13.1 requires
   one Barrin's account usable across every application, but
   `barrins_identity` (the dedicated identity service) is still
   mid-implementation and unmerged. Before wiring Tolaria News' auth (and
   now, also, Tamiyo Scroll's new team-sharing feature — see below),
   decide: reuse `barrins_api`'s current auth (same pattern Tamiyo Scroll
   uses today), or wait for `barrins_identity`? Not yet decided — flag per
   Constitution §16.2 before starting that work. **More urgent now**
   than when this was first flagged: two new features depend on it this
   release instead of one.
3. **Barrin's Scripture's location and database-access model are
   undecided.** The scraping service (renamed/migrated from the existing
   public `mtg_scraper` repo) needs a decision on (a) whether it merges
   into this monorepo at `apps/barrins_scripture` or stays a separate
   repository, and (b) whether it gets direct database write access or
   pushes through a `barrins_api`-owned ingestion route. Framed as
   alternatives with trade-offs in
   `v2.0.0-bump/index.md` (§1, "Scope decisions requiring the user's
   input before work starts"), not decided here.
4. **The scraped-tournament data domain does not exist in code.**
   `docs/content/back/barrins_api/bff/tamiyo_scroll.md` and several code
   comments reference a `dl_decks`/`dl_tournaments` domain and a
   `docs/decklist_integration/` design doc as if already built — neither
   exists anywhere in the repository (verified 2026-07-25). This domain
   has to be designed and built for Tolaria News and Barrin's Scripture
   to have anything to read/write, and for Karn Tablets to eventually
   read from later.
5. **Karn Tablets has no scope definition.** No prior planning exists for
   it anywhere in this repository. Recommendation (not yet confirmed):
   scope it to a placeholder for v2.0.0 — see the linked plan.
6. **Team creation/membership model is undecided** (Tamiyo Scroll's new
   "Team Decks" sharing feature) — no group/team entity exists in the
   schema today; see the linked plan for the alternatives considered.

### Should fix before v2.0.0 — not blocking, but compounds with more apps

1. **HetrixTools' free-tier tracker cap (2)** is already fully used by
   `barrins_api` prod + staging; `tamiyo_scroll` isn't separately
   monitored today. Up to two more deployable services this release
   (Tolaria News frontend, Barrin's Scripture) makes this worse, not
   better — revisit the free tier vs. a paid plan before v2.0.0 (see
   ADR-4, [Operations](operations/index.md)).
2. **Release cutting is still fully manual** (the gap ADR-2 flags) —
   tagging and creating the GitHub Release by hand doesn't scale as
   cleanly as more apps share one monorepo tag, and this release may add
   two or three more apps to that tag. Worth automating before release
   cadence increases.
3. **Changelog aggregation has a known cosmetic bug**, found during
   v1.0.0's changelog-split UAT: sub-repo and category headings render at
   the same level in `changelog/index.md`'s "Latest changes" section.
   Every app added to the aggregation — Tolaria News, Barrin's Scripture,
   and Karn Tablets included — will show the same issue until
   `docs/hooks/sync_changelogs.py` is fixed.

### Pre-existing gaps, unrelated to Tolaria News specifically

1. **nginx security headers** (HSTS, etc.) are not implemented
   (Constitution §29.1) — see [Operations](operations/index.md)'s open
   items table.
2. **Pre-commit secret-scanning is opt-in per developer**, not enforced
   by CI or any server-side gate — see
   [Secrets Management](security/secrets.md)'s open item. Worth
   reconsidering as the contributor surface grows.

### Newly found while scoping v2.0.0 (not previously written down)

1. **`deployment/backend.md` contradicts `operations/index.md`.** The
   former's "Validation" section says "no dedicated `/health` route in
   `barrins_api` today"; the latter correctly lists `GET /health` as
   implemented, and it is (`app/api/general/health.py`). One of these two
   pages is stale and needs a fix.
2. **Several docs and code comments cite planning documents that don't
   exist in the repository**: `docs/decklist_integration/`,
   `docs/tolaria_news/00_plan_general.md`,
   `docs/tamiyo_scroll_tracker/00_plan_general.md`,
   `docs/signup_email_verification/00_plan_general.md`, and
   `docs/auth_roles/10_deploiement.md` are referenced from
   `bff/tamiyo_scroll.md`, `signup_email_verification.md`,
   `front/tamiyo_scroll/bootstrap.md`, `scripts/create_admin.py`, and
   multiple files under `app/services/`, `app/models/`, `app/core/` —
   none of the five paths exist anywhere in the repo. Needs a decision:
   recreate them, or update every citing reference.

### v2.0.0 feature additions to Tamiyo Scroll (new this release)

Not carried over from a prior roadmap — newly scoped:

1. Team sharing (read-only "Team Decks" selector, flag-to-share) — see
   blocking item 6 above.
2. Auto-flag a match result to the decklist version active at the time,
   editable afterward.
3. Redesigned decklist display (no design exists yet — needs a design
   pass, not just implementation).
4. PDF export of a training session for a specific deck.
5. Global results sharing: re-enabling the already-built, currently
   disabled `SharingControls.tsx` (`SHARING_ENABLED = false`), plus a new
   "toggle to receive" concept that doesn't exist in the current sharing
   model.
6. Admin usage/metrics dashboard, **confirmed for v2.0.0** but as an
   interim, embedded shape: routes in `barrins_api`, UI in
   `tamiyo_scroll`, gated by the existing `AdminUser`/
   `require_role(UserRole.admin)` mechanism
   ([Auth & Roles](../back/barrins_api/auth_roles.md)) — no new backend
   auth mechanism needed. Long-term (v3.0.0, not before), this
   externalizes into its own standalone application covering every
   public-facing frontend, accessed through a dedicated user-management
   pair: **Barrin's Identity** (backend) and **Goblin Guide** (frontend
   — a new name, not found anywhere in this repo before now). What
   "metrics" should mean concretely is still not specified: assumed to
   be product/usage analytics (signups, active users, decks, matches,
   sharing adoption) unless corrected. Also surfaced while scoping this:
   the constitution has no privacy/data-retention policy at all, worth
   writing one alongside this feature even briefly.
7. Tutorial + demo interface, shipped as **one combined experience**
   (decided, not two separate features), pre-filled from a JSON fixture
   file. **Decided**: pure frontend mock — a parallel data-source module
   reusing the existing tab components unmodified, fully public route,
   no token ever issued, no call to `barrins_api`. "No persistence"
   holds structurally rather than by a reset job. The guided-tour
   overlay is hand-rolled with the existing Radix/shadcn primitives
   already in `src/components/ui/` — no new dependency. Needs zero new
   backend work. See `v2.0.0-bump/index.md` (§1.8, "Tutorial / demo
   interface for Tamiyo Scroll, no persistence") for the alternatives
   that were considered and rejected.

**Playwright — considered, deferred, not part of v2.0.0.** Not a fit for
item 7 above (it's an E2E/browser-automation framework, not a tour
library — settled by the primitives decision). Two other places it could
apply: a committed, CI-integrated E2E suite for `tamiyo_scroll`
(already used informally during the original bootstrap, but explicitly
deferred then too — see `v2.0.0-bump/index.md` ("A note on Playwright —
deferred, not part of v2.0.0")), and replacing Selenium in the MTGO
scraper (relevant only once the
Barrin's Scripture repo-migration decision lands, low priority — no
active pain point today). Neither is scheduled for this release.

Full write-up, including which of these are genuinely cheap (sharing
re-enablement builds on fully-tested existing code) versus which need a
design pass or a new schema entity first: `v2.0.0-bump/index.md`
(§"Group S — Tamiyo Scroll changes (request item 2)").

### Looking ahead — what's already known about v3.0.0

Not a v3.0.0 plan (too early for that) — just the concrete facts already
confirmed, so they aren't lost before that planning starts:

- The admin metrics dashboard shipping in v2.0.0 (embedded in
  `barrins_api`/`tamiyo_scroll`) externalizes into its own standalone
  application in v3.0.0, covering every public-facing frontend.
- Access to it moves, at that point, to a dedicated user-management
  pair: **Barrin's Identity** (backend) and **Goblin Guide** (frontend).
  Neither is scheduled before v3.0.0.

## See also

- `docs/project/v2.0.0-bump/index.md` (internal release tracking, not
  part of this published site) — full priorities, dependency graph, and
  open architectural decisions
  for this release.
- [Decision Records](architecture/decisions.md) — ADR-1 through ADR-4;
  ADR-5 onward should record this release's resolved decisions.
- [Operations](operations/index.md) — current monitoring/backup/logging
  state.
- [Frontend Deployment](deployment/frontend.md) — Tamiyo Scroll / Tolaria
  News playbook reference.
