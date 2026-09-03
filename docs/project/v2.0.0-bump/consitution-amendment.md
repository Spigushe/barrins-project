# Constitution amendment proposals — v2.0.0-bump

[← Back to project index](index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `docs/content/CLAUDE.md` (the project constitution) | / |
| **Initial date** | 2026-07-25 | / |
| **Status** | ✅ Proposals 1–6 reviewed and accepted (1, 4, 5, 6 as written; 2, 3 with modifications, see each). 🔲 **Proposal 7 added 2026-08-03, not yet reviewed.** ✅ **Proposal 8 added and accepted 2026-08-24, applied directly to `.claude/CLAUDE.md` the same day** (§11.8). Proposals 2–7 nothing yet applied to `CLAUDE.md` — that's R5/ADR work | / |
| **Source** | Decisions recorded in `index.md` §1.2, §1.3, §1.6, §1.7, §1.9 | / |

---

## Why this file exists

Resolving `index.md` §1's open decisions surfaced places where the
constitution (`docs/content/CLAUDE.md`) has **no existing rule to point
to** — not disagreements with what it already says, but genuine gaps a
v2.0.0 feature now depends on. Per Constitution §5 (Agent Governance:
"when agents disagree on subjective decisions, STOP... wait for user
decision") and §16.3 (every significant technical decision needs
Context/Alternatives/Trade-offs/Decision/Consequences), each proposal
below was written for independent sign-off — the user could accept,
reject, or amend any one without affecting the others.

**Reviewed by the user, 2026-07-26**: Proposals 1, 4, 5 accepted as
written; Proposals 2 and 3 accepted with modifications (each proposal
below documents exactly what changed and why).

**Reviewed by the user, 2026-07-27**: Proposal 6 (inbound
rate-limiting), surfaced while resolving §1.9/I7, **accepted as
written**. All six proposals are now reviewed.

**Added 2026-08-03, not yet reviewed**: Proposal 7 (long-lived
integration branches need a documented workaround for this repo's
squash-only/linear-history branch protection), discovered live while
executing RA2 — recorded per the user's instruction to store the finding
for later rather than leave it undocumented, ahead of the full `v2.0.0`
release's own `proj/v2.0.0-bump` → `staging` promotion (Group R) hitting
the same thing.

None are yet applied to `docs/content/CLAUDE.md` itself — see "Applying
these proposals" at the end of this file for that remaining step.

**Confirmed by the user (2026-07-25):** "Advanced User" names the
existing `role_c` placeholder (ordinal level 2 in
`docs/content/back/barrins_api/auth_roles.md`'s `UserRole` enum, the
role explicitly marked "TBD" there) — not `ml_developer` (level 3,
already a specific, meaningful role). Proposal 2 below is written
against that confirmation, no longer flagged as open.

---

## Proposal 1 — Privacy, Data Retention & Analytics Policy

**Status: ✅ Accepted (2026-07-26)**, with one condition from the user:
**if/when this needs to align with GDPR (or similar) regulation, that
must be an extension of this policy, not a replacement of it.** Whoever
does that future work should amend this section in place — adding
retention schedules, consent flows, data-subject-access handling on top
of what's here — rather than superseding it with a separate policy
document. Recorded here so that constraint survives past this
conversation.

**Target**: new top-level section, `§51` — inserted **before** the
current `§51 Final Instruction`, which shifts to `§52` (a single +1
shift; see "Applying these proposals" below for why the other four
proposals don't renumber anything).

### Context

`index.md` §1.7 named this gap directly: the constitution contains no
privacy, data-retention, or analytics policy anywhere in its 2270 lines.
S6 (admin metrics dashboard) is the first feature to make this visible
in practice — it's a dedicated admin surface over aggregate user data,
not just the data merely existing in the database already implied.

### Alternatives

1. Say nothing at the constitution level; let each feature that touches
   aggregate/personal data write its own ad hoc note (S6's original page
   proposed exactly this: "a short written note... even a paragraph").
2. Add a durable, general policy at the constitution level that any
   current or future feature touching aggregate or personal data can
   point to, rather than reinventing per feature.
3. Adopt a full formal privacy/compliance policy (e.g. GDPR-grade
   retention schedules, consent flows, data-subject-access-request
   handling) ahead of any regulatory requirement to do so.

### Trade-offs

Option 1 is cheapest but means S2 (team data visible to members),
S6 (aggregate metrics), and any future feature each re-derive the same
answer independently, with no guarantee they land on the same one.
Option 3 is speculative work with no current trigger (no jurisdiction
requirement is currently in scope, no third-party data processor is
being introduced) — exactly what Constitution §39/§48 already warn
against ("do not implement unused features prematurely"). Option 2 is
the minimum durable rule that removes the gap without inventing
compliance machinery nobody has asked for yet.

### Decision (proposed)

Add a new section stating:

- Aggregate or derived analytics computed **only from data the backend
  already holds for its normal function** (e.g. counting existing rows)
  does not require additional user consent, but must be documented
  alongside the feature that computes it: what is measured, why, and who
  can see it (mirrors the existing API-documentation requirement in
  §21, extended to analytics surfaces specifically).
- Introducing any **new** tracking/telemetry collection not already
  implied by the feature's own function (a first- or third-party
  analytics SDK, session recording, additional request logging beyond
  what already exists for security purposes) goes through the same
  dependency-approval process as §22 (Dependency Management), applied
  explicitly to data-collection tooling and not only code libraries.
- Admin-facing aggregate views must not expose a specific non-admin
  user's individual behavior beyond what already exists elsewhere in
  admin tooling (a metrics dashboard shows counts/trends, not "user X
  did Y at time Z," unless an existing admin feature — e.g. the user
  list — already exposes that).
- No automatic data-retention/deletion policy exists today for user data
  (accounts, decks, matches), and this proposal does not invent one. It
  is named here explicitly as an **open compliance question**, to be
  resolved before any feature that requires it (e.g. a jurisdiction with
  a "right to be forgotten" requirement) is targeted — not before
  v2.0.0.

### Consequences

Gives S6 — and any future admin-facing aggregate view — a rule to point
to instead of inventing one per feature. Doesn't block v2.0.0: S6's
staged metric set (account/deck/match counts, `index.md` §1.7) already
complies by construction, since it's pure aggregation over existing
data, nothing newly collected.

---

## Proposal 2 — Account Tiers May Gate Features

**Status: ✅ Accepted with modifications (2026-07-26)** — see "What
changed from the original proposal" below before reading the rest,
since the Context/Alternatives/Trade-offs were written before this
feedback and are kept only for the reasoning that still holds.

**Target**: new subsection `§13.6` (Authentication Architecture already
ends at `§13.5`), plus a corresponding update to
`docs/content/back/barrins_api/auth_roles.md`'s role table — the latter
is documentation of an existing implementation, not a constitution
change, but is listed here since both should land together.

### What changed from the original proposal

1. **No mention of monetization.** The original draft described this
   tier as potentially linked to "a kind of paywall (Patreon for
   example)" — **the user explicitly rejected naming any potential
   paywall now.** The Decision below is rewritten to say only that a
   role may gate features, with no statement of *why* or *whether* that
   ever involves payment. If a paywall is decided later, that's its own
   future decision — this proposal must not pre-announce it.
2. **Ownership, simplified (amendment 2)**: user roles — including
   `role_c`/Advanced User — are **owned by `barrins_api` until
   `barrins_identity` is implemented.** Not framed as already
   conceptually `barrins_identity`'s in the meantime — `barrins_api`'s
   `UserRole` enum is simply the owner, full stop, the same as every
   other role today, until that app exists to actually take it over.
   Ownership transfers only once `barrins_identity` is real, not before.
3. **Backend-driven warning, not a frontend guess (amendment 3)**: the
   API must keep returning the current user's actual role as-is (e.g.
   `user`), but must **also** expose a separate, backend-owned signal
   for whether that user **may be moved up to Advanced User** — this is
   what determines *when* the frontend renders a "this may evolve"
   comment, not a frontend-side guess based on the plain role value.
   Consistent with §4.1 (backend owns business logic; frontend renders
   what it's given, the same shape as the constitution's own
   `available_actions` example).

### Context

`index.md` §1.6 confirmed team creation is open to any user for v2.0.0,
but flagged that a **later** release may gate team creation behind a
role tier. The constitution's Authentication Architecture (§13) never
mentions feature-gating roles at all; `auth_roles.md`'s `UserRole` enum
already has an unnamed placeholder role (`role_c`, level 2, "final name
and scope not yet decided") that fits this concept better than
inventing a new one.

### Alternatives

1. Say nothing at the constitution level now; decide role-to-feature
   gating logic ad hoc whenever a gated feature is actually built.
2. Add a general principle now — roles may gate features, backend-owned
   and auditable — without committing to *which* feature gets gated,
   when, or why, and finalize the existing `role_c` placeholder's name
   to `advanced_user` so it stops reading as unfinished.
3. Design a full entitlements system now (subscription/grant state,
   automated role assignment) ahead of any concrete feature needing it.

### Trade-offs

Option 1 risks exactly the kind of undocumented, one-off authorization
logic §4.2 ("no duplicated business logic") and §23.3 ("every endpoint
must define... authorization requirement") already guard against, the
first time a gated feature actually ships. Option 3 is out of scope
today — no entitlement/billing feature is part of v2.0.0 or even
confirmed for a later release; building it now would be exactly the
premature implementation §39/§48 warn against. Option 2 costs one
documentation update and states a principle without committing to
implementation or to a reason.

### Decision (proposed)

- Add `§13.6`: account roles/tiers may gate access to specific features.
  This section does **not** state why a role might be restricted
  (payment, moderation, invitation-only, or anything else) — only that
  the mechanism exists and is backend-owned. Any code that assigns or
  revokes such a role is backend-owned and auditable — never a
  frontend-trusted flag, consistent with §4.1 ("backend owns business
  logic"). **Ownership**: `barrins_api`'s `UserRole` enum owns account
  roles until `barrins_identity` is implemented — ownership transfers
  then, not before (amendment 2).
- The API returns the user's actual current role as-is, plus a separate
  backend-owned flag for whether that user **may be moved up to
  Advanced User**. The frontend uses that flag — not its own
  judgment — to decide *when* to render a "this may evolve" comment
  (amendment 3): the decision of when to warn a user is backend logic,
  not frontend guesswork, per §4.1.
- **Confirmed (see "Why this file exists" above)**: finalize `role_c`
  (level 2) as `advanced_user` in `auth_roles.md`, replacing its
  "🔲 placeholder" marker. Per `auth_roles.md`'s own design note,
  `require_role()` compares ordinal levels, not names, so this is a
  rename with no logic change — every existing `RoleCUser` caller keeps
  working unchanged.

### Consequences

Doesn't force building team-creation gating in v2.0.0 — §1.6 already
confirmed v2.0.0 ships with team creation open to everyone. Gives a
later release a documented hook (a named role, a stated ownership path
to `barrins_identity`, a required UI warning) instead of an ad hoc
decision made under schedule pressure at that time — and does so
without committing, even implicitly, to monetizing anything.

---

## Proposal 3 — Teams/Groups as a Shared Ecosystem Concept

**Status: ✅ Accepted with modifications (2026-07-26)** — see "What
changed from the original proposal" below.

**Target**: new subsection `§13.7` only. The originally-proposed `§23.4`
(backend validation of cross-user content) is **not** being added — see
point 2 below.

### What changed from the original proposal

1. **Ownership clarified, and it's not permanent.** Teams are groups of
   persons. Confirmed: `§13.7`'s "modeled once, shared across
   applications" principle still holds, but ownership isn't
   `barrins_api` indefinitely — it transfers to
   `barrins_identity`/Goblin Guide once they're released, the same
   pattern as Proposal 2's Advanced User role and §1.7's admin
   dashboard. Until then, `barrins_api` is the interim, single owner
   (no per-app duplication) — not a permanent home.
2. **The original Option 2 (state the principle now) is adopted, as
   proposed. Additionally: Option 3 (a full generic groups subsystem) is
   not rejected outright — it's planned to ship alongside the
   `barrins_identity` implementation**, though not necessarily in its
   first wave/release. This is new: the original proposal treated
   Option 3 as premature and out of scope indefinitely; the user's
   guidance narrows that to "not yet, but tracked as real future work
   tied to a specific milestone (`barrins_identity`'s build-out)," not
   an open-ended maybe.
3. **The backend-validation rule (originally proposed `§23.4`) is
   dropped from this proposal entirely — the user was explicit that
   this must not become a constitutional rule attached to teams/groups.**
   Instead: **backend validation of as much data as possible remains a
   general direction for *later Tamiyo Scroll releases*** — a goal to
   keep pursuing feature-by-feature (as S2's own deck-validation gate
   already does via S8), not a `CLAUDE.md` rule triggered by "content
   becomes visible to another user." Recorded here so the intent isn't
   lost, but it does not get its own numbered section.

### Context

`index.md` §1.6 introduces `ts_teams`/`ts_team_members` — the first
group/multi-user entity in the schema. Constitution §13.1 states "the
same account must be usable by every application" but says nothing about
*groups* of accounts.

### Alternatives

1. Leave the group concept as a Tamiyo-Scroll-specific implementation
   detail, scoped only to S2's page.
2. State it as an ecosystem-level principle now, since Tolaria News and
   any future application are equally likely to need a group concept
   later — **chosen**.
3. Design a full generic "groups" subsystem shared across every app —
   **deferred, but scheduled**: alongside `barrins_identity`'s
   implementation, not necessarily its first wave.

### Trade-offs

Option 1 risks the same problem §13.1 was written to prevent for
identity: a second application inventing its own, differently-shaped
group concept instead of reusing one. Option 3 built *now* would be
speculative — no second consumer of "groups" exists yet, so a generic
subsystem would be designed against a sample size of one, contrary to
§39/§48 — which is why it's tied to `barrins_identity`'s own timeline
(a real milestone) rather than open-ended. Option 2 states the
principle now without prescribing a schema beyond what S2 already
needs, and is compatible with Option 3 landing later without rework.

### Decision (proposed)

- Add `§13.7`: group/team-like entities (teams, and any future
  organization-style entity) are modeled once, generalizing §13.1's
  "one account, shared across applications" to "one group concept,
  shared across applications." **Ownership**: `barrins_api` is the
  interim owner (matching where `ts_teams`/`ts_team_members` actually
  live for v2.0.0); ownership transfers to `barrins_identity`/Goblin
  Guide once released — not a permanent `barrins_api` responsibility.
- **Note, not a rule**: a full generic groups subsystem (the original
  Option 3) is expected to ship alongside `barrins_identity`'s
  implementation (timing within that effort not yet decided — possibly
  not its first wave). This is forward context for whoever plans that
  work, not a constitutional requirement being added now.
- **Explicitly not added**: any rule tying backend content-validation to
  group/team visibility. See "What changed" point 3 above — validating
  as much data as possible stays a working direction for future Tamiyo
  Scroll releases, pursued feature-by-feature, not a `CLAUDE.md` section.

### Consequences

Gives S2 (and Tolaria News, if it ever needs groups) an existing
ownership principle to point to, with an honest timeline for when a
fuller subsystem might replace the interim `barrins_api`-owned version.
Avoids over-promising a validation guarantee as a blanket rule — S2's
own deck-validation gate (via S8) remains the concrete, scoped example
of "validate before cross-user exposure," rather than that becoming a
generalized constitutional obligation applied to every future feature
regardless of cost. **Note (2026-07-27)**: S2's gate itself was
subsequently deferred to v3.0.0 (see `s2-team-sharing/index.md`) — it no
longer ships in v2.0.0, but stays the intended first concrete instance of
this working direction once S8 exists.

---

## Proposal 4 — Bulk/Heavy Data Must Not Live in the Primary Repository

**Status: ✅ Accepted as written (2026-07-26)** — no changes requested.

**Target**: new subsection `§26.5` (Infrastructure and Deployment
Architecture currently ends at `§26.4`).

### Context

`index.md` §1.3 decided the scrape archive (already gigabytes, growing)
needs its own dedicated "dump sub-repo," never inlined into the monorepo.
This is a specific instance of a rule the constitution never states
generally: keeping `barrins-project/barrins-project` itself cheap to
clone regardless of how much archival/generated data the ecosystem
accumulates.

### Alternatives

1. Treat this as a one-off decision scoped only to Barrin's Scripture's
   archive (recorded in `index.md` §1.3 and T1/T3's pages only).
2. State it as a general infrastructure principle, so Tolaria News'
   scraped-tournament data (T2/T3) and any future bulk dataset inherit
   the same constraint without rediscovering it under time pressure.
3. Move to object storage (a VPS disk path, an S3-compatible bucket)
   for all bulk data instead of git submodules, superseding the existing
   `mtg_decklist_cache` pattern entirely.

### Trade-offs

Option 1 leaves the next data-heavy feature to rediscover the same
constraint from scratch, likely after the monorepo has already grown
uncomfortably large — the exact failure mode §1.3 flagged. Option 3 is a
bigger infrastructure change than anything currently justifies (no
current pain point with the git-submodule approach beyond size,
`mtg_decklist_cache` is live and working) and duplicates work already
flagged as a *future* fallback in §1.3 itself ("if the git-submodule
approach doesn't scale as scrape volume grows"). Option 2 generalizes
the existing, working pattern without changing it.

### Decision (proposed)

Add `§26.5`: any dataset expected to grow unbounded or reach non-trivial
size (scrape archives, generated reports, large fixtures) lives in its
own dedicated repository or storage location, referenced by the monorepo
(git submodule, external bucket, etc.) — never committed directly into
an application's own repository history. Mirrors the existing
`mtg_decklist_cache` precedent, generalized so Tolaria News' scraped-
tournament data and any future bulk dataset inherit the same constraint
by default.

### Consequences

Turns T1/T3's dump-sub-repo requirement from a one-off decision into a
standing rule; directly relevant to T2/T3 (scraped-tournament schema and
its own archive) without needing a second, separate decision later.

---

## Proposal 5 — Maintenance-Mode Write Containment for Internal Endpoints

**Status: ✅ Accepted as written (2026-07-26)** — no changes requested.

**Target**: new subsection `§31.4` (API Deployment currently ends at
`§31.3`, Database migration policy).

### Context

`index.md` §1.2 requires the new internal ingestion route
(`POST /internal/scripture/ingest`) to reject or queue writes during
maintenance windows, rather than failing opaquely or writing against a
database mid-migration. §31.3 already covers migration *policy*
(backup, verify, test) but says nothing about runtime write behavior
during a migration or maintenance window, for endpoints whose caller is
a scheduled job or another service — not a human-driven frontend.

### Alternatives

1. Leave this as a Barrin's Scripture-specific implementation detail,
   built once for T3 and not documented as a reusable pattern.
2. State a general rule for internal/service-to-service endpoints now,
   so any future scheduled writer (a real Karn Tablets, if I4 ever
   resolves toward direct DB access; any other internal ingestion route)
   inherits the same expectation.
3. Build a global maintenance-mode page/flag that blocks the entire API,
   reused for this narrower need.

### Trade-offs

Option 1 means the next internal writer re-derives the same design
(a maintenance flag, checked where) independently. Option 3 is broader
than the actual problem: §1.2's requirement is specifically about one
internal ingestion route, not the whole API — a blanket maintenance page
would block `tamiyo_scroll`'s and `tolaria_news`' normal traffic for a
Barrin's Scripture-only migration, which is a bigger blast radius than
the decision calls for. Option 2 states the general shape without
overreaching.

### Decision (proposed)

Add `§31.4`: any endpoint whose caller is not a human-driven frontend
(scheduled jobs, service-to-service ingestion routes) must be able to
reject or defer writes during a declared maintenance window, via an
explicit, narrowly-scoped check at the point of writing — never a
blanket, application-wide maintenance page unless the whole application
is actually down for that reason.

### Consequences

Gives T3 a documented pattern to implement against instead of an ad hoc
flag invented for this one route; a future internal writer (Karn
Tablets, if I4 ever resolves toward direct database access) inherits the
same expectation without a second decision.

---

## Proposal 6 — Inbound Rate-Limiting for Public/Unauthenticated Endpoints

**Status: ✅ Accepted as written (2026-07-27)** — no changes requested.
Added while resolving §1.9/I7; reviewed independently of Proposals 1–5
above.

**Target**: new subsection `§23.4` (Security Principles — this slot is
free again: the original Proposal 3 draft proposed `§23.4` for a
different rule, which the user rejected outright; see Proposal 3's "What
changed." No conflict, no renumbering impact — same as the other
subsection insertions in this document.)

### Context

Resolving §1.9 (how to restrict Tolaria News' public BFF routes)
surfaced a wider gap while researching the answer: **`barrins_api` has
no inbound rate-limiting anywhere today.** The only limiter that exists
is the Moxfield client's *outbound* limiter (A3 — caps calls the backend
makes *to* Moxfield, ≤1 req/s, module-level, single-process). Inbound
limiting on `POST /auth/token` is already a known, documented gap
(`auth_roles.md`'s backlog, P-03: "recommended before opening the
frontend," never built). §1.9's decision (Option 4: public reads stay
open, restricted by rate-limiting rather than caller identity) now makes
this a hard *requirement* for Tolaria News' BFF, not just a
recommendation for one login route — the same missing capability blocks
both.

### Alternatives

1. Leave rate-limiting as a per-feature concern, built ad hoc whenever a
   specific route needs it (as §1.9/T4 would do alone, without this
   proposal).
2. State a general principle now: any public/unauthenticated endpoint
   must have inbound rate-limiting, enforced at a layer that stays
   correct under multiple workers — without prescribing the exact
   policy (key/threshold/window) per endpoint, which stays a per-feature
   decision.
3. Design a full, ecosystem-wide rate-limiting/API-gateway layer now,
   ahead of any second concrete need beyond Tolaria News' BFF and
   `POST /auth/token`.

### Trade-offs

Option 1 means T4 solves this alone, and the next public route (or the
still-open `POST /auth/token` gap) re-derives the same design —
including the same easy-to-miss per-worker trap (a naïve in-process
limiter multiplies its effective limit by worker count, since nothing
today states this must be avoided). Option 3 is speculative
infrastructure ahead of a second real need — exactly what §39/§48 warn
against, and a bigger lift than either current consumer (T4, P-03)
justifies alone. Option 2 fixes the "correct layer" mistake ecosystem-
wide without committing to infrastructure nobody's asked for.

### Decision (proposed)

Add `§23.4`: every endpoint that accepts requests without per-user
authentication (public reads, login/token endpoints before a session
exists) must be protected by inbound rate-limiting, enforced at a layer
that remains correct across every worker process — nginx
(`limit_req`/`limit_conn`, since nginx already fronts every backend per
§29 and is shared across workers by construction) for coarse, per-IP
limits, or a shared-state store (Redis/DB, keyed per client) if
finer-grained control is needed. An in-process limiter (a bare
`asyncio.Lock`/counter with no cross-worker coordination) does **not**
satisfy this — it's the same mistake the Moxfield outbound limiter's own
documented caveat already flags for a different direction (outbound,
not inbound), generalized here to make sure it isn't repeated inbound.
The exact policy (key, threshold, window, response shape) is left
per-endpoint, decided where that endpoint is implemented (e.g. T4's own
page, and separately for `POST /auth/token`'s P-03).

### Consequences

Gives T4 (and whoever eventually picks up `POST /auth/token`'s P-03) a
rule to build against instead of inventing the "which layer, why"
reasoning from scratch, and forecloses the specific per-worker mistake
before it ships once instead of catching it in review each time.

---

## Proposal 7 — Long-Lived Integration Branches Need an Exception to Squash-Only/Linear-History

**Status: 🔲 Proposed, not yet reviewed** — added 2026-08-03, discovered
live while executing RA2 (`ra2-merge-staging/index.md`, the
`v2.0.0-alpha` release plan's `proj/v2.0.0-bump` → `staging` step).

**Target**: new subsection `§18.5` (after existing §18.4, Git Standards
— this is a branch/merge-strategy rule, not a release-deployment rule,
so it belongs alongside the existing commit-philosophy rules rather than
in §25 Release Policy).

### Context

F9 (`f9-proj-branch-protection/index.md`) added a repository ruleset
requiring PRs (no direct pushes) on `proj/*` branches, mirroring
`staging`/`main`'s existing protection. Checking that protection's exact
shape while resolving RA2's own conflict (`gh api
repos/.../rules/branches/...`) surfaced that both `staging` and
`proj/v2.0.0-bump` share one repository-wide ruleset requiring
`allowed_merge_methods: ["squash"]`, `required_linear_history`, and
`non_fast_forward` (no force-push) — every merge between any two
branches in this repository, including between two long-lived
integration branches, is forced to be a squash commit.

This has a structural consequence nothing in this project's docs
anticipated: **squash merges never advance the git merge-base between
the two branches involved.** Reconciling `proj/v2.0.0-bump` with
`staging` (RA1 §1.11's T1/T2-inert decision meant they'd diverged on
`apps/tamiyo_scroll/package.json`/`package-lock.json` and
`apps/barrins_api/uv.lock`, from unrelated dependency bumps landing on
each branch independently) required a "sync" PR (#47, mirroring the
existing #40 precedent from v1.0.0-bump's own history) to resolve a real
textual conflict. But because #47 squash-merged into
`proj/v2.0.0-bump`, git's recorded merge-base with `staging` **stayed
frozen** at the commit from *before either branch had diverged*
(`9fa40bf`, 2026-07-25) — so the identical conflict reappeared
immediately on the next comparison (RA2's own PR, checked via `gh pr
view --json mergeable`), and would keep reappearing on every future
comparison between these two branches for as long as they both touch the
same lines, no matter how many times a sync PR "resolves" it. A second
sync PR (#48) confirmed this: it squash-merged with **zero net diff**
(content was already fully reconciled) and, as predicted, did not clear
the conflict.

**The actual fix** (used to unblock RA2): build the reconciliation
branch starting **from the target branch** (`staging`) and merge the
*source* branch (`proj/v2.0.0-bump`) into it, resolving the conflict
once, so `staging` becomes a real git ancestor of the result — a PR from
that branch back into `staging` then computes as a clean, trivial diff,
because nothing on `staging`'s side needs reconciling against a stale
base anymore. This only works one-directionally (it fixed the
`proj/v2.0.0-bump` → `staging` direction; the reverse — syncing
`staging`'s later changes back into `proj/v2.0.0-bump`, as PR #47/#48
attempted — remains structurally unfixable under squash-only, since
`proj/v2.0.0-bump` is not the branch actually being merged into GitHub's
UI in that direction either way).

### Alternatives

1. **Leave it undocumented.** Whoever hits this next (the same
   `proj/v2.0.0-bump` → `staging` promotion happens again for the full
   `v2.0.0` release, per `index.md`'s Group R) re-derives the same
   "why is this still conflicting after I just fixed it" confusion from
   scratch.
2. **Record the mechanism and the one-directional workaround** (build
   from the target branch, not the source branch) as a documented rule —
   without changing the branch-protection ruleset itself.
3. **Carve out a ruleset exception** allowing real merge commits (not
   squash) specifically between long-lived integration branches
   (`proj/*` ↔ `staging`), which would let the merge-base actually
   advance and prevent this class of conflict from recurring at all —
   at the cost of `staging`'s/`proj/*`'s history no longer being fully
   linear, and touches repo-wide merge-button settings, not just this
   one pair of branches.

### Trade-offs

Option 1 costs nothing to write but guarantees the same debugging
detour recurs at least once more this release cycle (the full `v2.0.0`'s
own `proj/v2.0.0-bump` → `staging` promotion, Group R). Option 3 is the
structurally cleaner fix (real ancestry, no recurring conflict at all)
but is a repository-wide policy change the user explicitly declined to
make when this was found live (2026-08-03) — "keep squash-syncing" was
chosen over changing merge settings, matching this project's general
preference (§39/§48, YAGNI) for not re-architecting infrastructure to
solve a problem a documented workaround already handles. Option 2
matches that decision: cheap, no infrastructure change, and turns a
one-off discovery into a repeatable recipe.

### Decision (proposed)

Add `§18.5`: when reconciling two long-lived branches under this
repository's squash-only/linear-history branch protection, **build the
reconciliation branch starting from whichever branch is the merge
*target*, merging the *source* branch into it** — never the reverse —
so the target becomes a real ancestor of the result and the resulting PR
computes as a clean diff instead of re-deriving the same conflict from a
stale, frozen merge-base. Document plainly that squash merges do not
advance the merge-base between the branches involved, so a conflict
"resolved" by squash-merging into the *source* branch (e.g. syncing
`staging`'s changes into `proj/v2.0.0-bump`) will **not** clear the
corresponding conflict in the *opposite* direction (`proj/v2.0.0-bump`
into `staging`) — these are two independent reconciliations under
squash-only, not one.

### Consequences

Gives whoever runs the full `v2.0.0` release's own `proj/v2.0.0-bump` →
`staging` promotion (Group R, not Group RA) a documented recipe instead
of re-discovering this the same way RA2 did. Doesn't fix the underlying
mechanism (still squash-only) — a future release could still hit
one-off confusion the first time a *different* pair of long-lived
branches needs reconciling, but at least this exact `proj/*` ↔ `staging`
shape now has a written answer.

---

## Proposal 8 — Deletions Default to Soft-Delete (Archive), Not Physical Removal

**Status: ✅ Accepted (2026-08-24)** — decided live in conversation while
implementing S17, applied directly to `.claude/CLAUDE.md` the same day
(unlike Proposals 2-7, still pending the ADR/merge pass) since the user
explicitly asked for the constitution itself to be updated, not just this
record — same treatment Proposal 1 already got.

**Target**: new subsection `§11.8` (after existing §11.7 Pydantic
schemas, before §12 BFF Architecture — a backend/DB-modeling convention,
not a §51 privacy/retention rule). §11 already ends at §11.7, so this is
a clean append; no renumbering.

### Context

Implementing S17 (`s17-card-log-matchup-evaluations/`) shipped
`DELETE /card-tests/{id}` as a real SQL `DELETE` — and because
`TSCardTestEvaluation.test_id` has `ondelete="CASCADE"`, deleting a card
log silently, permanently destroyed every match-up evaluation logged
against it, with no way back. The user flagged this as unacceptable and
stated the general rule this project has never actually written down:
**by default, every delete action in the application should be a
disguised archive** — the record disappears from the user's active view,
but stays in the database.

An audit of every existing delete operation
(`apps/barrins_api/app/api/tamiyo_scroll/`) found the same inconsistency
already existed project-wide, not just in the new S17 code:

- **Already soft-delete** (an `archived_at` column, list queries filter
  it out): `TSPersonalDeck` (`personal_decks.py`), `TSMetaDeck`
  (`meta_decks.py`), `TSSession` (`sessions.py`). Of these, only
  `TSSession` has a working *restore* path
  (`PATCH /sessions/{id}` with `SessionPatch.restore`) —
  `TSPersonalDeck`/`TSMetaDeck` can be archived but never un-archived
  today.
- **Hard delete** (`session.delete(...)`, no soft-delete column at all):
  `TSCardTest` + `TSCardTestEvaluation` (the S17 pair described above),
  `TSMatch` (`matches.py`), `TSTeam` and its full cascade family
  (`TSTeamMember`/`TSTeamDeckFlag`/`TSTeamDeckThread`/`TSTeamDeckMessage`,
  all `ondelete="CASCADE"` off `ts_teams.id` — one `delete_team` call
  today destroys rows in all four tables at once), and
  `TSPersonalDecklistVersion` (`delete_decklist_version` — this one
  carries a deliberate prior rationale, "Option G": the *version* is the
  delete target, not the deck, cf.
  `docs/tamiyo_scroll_tracker/00_plan_general.md`).

### Alternatives

1. **Status quo.** Keep deciding hard-delete-vs-soft-delete per table,
   case by case, as today.
2. **Blanket soft-delete default.** Every user-triggered delete action
   sets an archival marker instead of removing the row; the row becomes
   invisible to normal reads but stays in the database indefinitely.
   Physical deletion becomes an internal-only operation (an admin tool, a
   scheduled purge, or a §51 GDPR-driven data-subject-access deletion),
   never a direct consequence of a user clicking "delete". A specific
   table/action may still justify a real hard delete, but only as an
   explicit, documented exception — not the unstated default it is today.
3. **Same as 2, plus a time-boxed purge job** (e.g. archived rows expire
   after 90 days).

### Trade-offs

Option 1 is exactly the inconsistency that just caused real data loss in
S17 and will keep recurring as new features are built — no reason to
expect it to self-correct. Option 2 guarantees no accidental data loss
and gives one consistent mental model ("delete = archive"), at the cost
of: every delete-reachable table needing an archive column, a migration,
a filtered read path, and (a new requirement most tables don't meet
today) a restore path; and cascading children needing to archive
alongside their parent rather than being destroyed — a
`ondelete="CASCADE"` foreign key can only express *delete*, not
*archive*, so the Teams family (the deepest cascade chain in the schema)
needs its own redesign, not just a bulk column addition. Option 3 invents
a retention/purge schedule that §51 explicitly says not to add
speculatively ("not before it is actually needed") — premature here,
revisit only once §51's already-open retention question is actually
forced by a real requirement (e.g. GDPR).

### Decision (proposed)

Option 2. Every user-triggered delete action defaults to soft-delete; a
real hard delete requires an explicit, documented exception (a
code-level comment/docstring stating why), never the unstated default.
Two existing hard deletes were reviewed against this new default and
resolved by the user the same day:

- **`TSTeam` deletion** (`teams.py::delete_team`) — previously the one
  intentional hard-delete exception in the codebase (an invite-code
  re-entry confirmation gate). **Converts to archive**, no exception
  kept — its cascade family (`TSTeamMember`/`TSTeamDeckFlag`/
  `TSTeamDeckThread`/`TSTeamDeckMessage`) needs the same treatment.
- **`TSPersonalDecklistVersion` deletion**
  (`personal_decks.py::delete_decklist_version`) — **stays a hard-delete
  exception**, per the pre-existing Option G rationale (the version, not
  the deck, is deliberately the real delete target).

### Consequences

`TSCardTest`/`TSCardTestEvaluation` were converted the same day (new
`archived_at` columns, migration `6cf95145f67e`, delete routes set
`archived_at` instead of calling `session.delete`, list/report queries
filter `archived_at.is_(None)`) — no restore path yet, matching
`TSPersonalDeck`/`TSMetaDeck`'s current state rather than over-building
ahead of the rest. The remaining conversions (`TSPersonalDeck`/
`TSMetaDeck`'s missing restore path, `TSMatch`, and the Teams
cascade-family redesign) are tracked as a new item,
`s18-deletion-defaults-to-archive/`, not implemented in this pass — the
scope (a schema-wide, cross-cutting change touching most of the Tamiyo
Scroll domain) is comparable to S17 itself and needs its own pass. No
purge/retention job is introduced by this proposal — archived data grows
unbounded until §51's separate, still-open retention question is
resolved; this is a deliberate non-goal here, not an oversight.

---

## Applying these proposals

**Reviewed by the user 2026-07-26 and 2026-07-27.** Outcome: Proposals
1, 4, 5, 6 accepted as written; 2 and 3 accepted with the modifications
described in each ("What changed from the original proposal"). **All
six proposals are now reviewed and accepted.** None are applied to
`docs/content/CLAUDE.md` yet — that's still separate work, done here:

**Proposal 8, added and accepted 2026-08-24**: unlike 2-7, applied
directly to `.claude/CLAUDE.md` as the new `§11.8` the same day it was
decided (see Proposal 8's own Status line for why) — not part of the
batch below.

1. Insert the new **subsections** — §13.6, §13.7 (both after existing
   §13.5), §23.4 (after §23.3, Proposal 6), §26.5 (after §26.4), §31.4
   (after §31.3). These are subsections of already-numbered sections, so
   **inserting them does not renumber anything else** — §14, §24, §27,
   §32, etc. are unaffected, the same way adding §13.5 wouldn't have
   required renumbering §14.
   (Note: `§23.4` was originally proposed under Proposal 3 for a
   *different* rule, rejected outright — see Proposal 3's "What changed."
   The `§23.4` slot is reused here for Proposal 6's unrelated,
   since-accepted rate-limiting rule.)
2. Insert the new **top-level** section (Proposal 1) as the new `§51`,
   immediately before the current `§51 Final Instruction`, which shifts
   to `§52`. This is the only renumbering this whole document causes —
   a single +1 shift at the very end, not the larger shift an earlier
   draft of this file miscalculated. Renumber any cross-reference to
   the old `§51 Final Instruction` (if any exist elsewhere in the repo)
   accordingly.
3. Update `docs/content/back/barrins_api/auth_roles.md`'s role table and
   `UserRole` enum comment for Proposal 2 (`role_c` → `advanced_user`,
   level 2 — confirmed above), **without** adding any payment/paywall
   language per Proposal 2's "What changed."
4. Per R5 (`index.md` Group R), write an ADR for each applied proposal —
   this document is the Context/Alternatives/Trade-offs input, not the
   ADR itself. Per §3.1, these ADRs must be merged into
   `proj/v2.0.0-bump` before R1, not written after the fact.
5. **Proposal 6's ADR** is additionally the natural place to also close
   out `auth_roles.md`'s pre-existing P-03 backlog item (inbound
   rate-limiting on `POST /auth/token`), since both share the same root
   cause and fix pattern.
