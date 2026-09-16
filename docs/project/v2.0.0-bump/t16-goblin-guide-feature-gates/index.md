# T16. Goblin Guide — feature gate engine (admin-toggleable feature flags)

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_identity` (registry + API), `libs/goblin_guide/` + `apps/goblin_guide/` (admin screen), `libs/identity_client/` (consumer helper), any consuming app that registers a gate (first consumer: `apps/barrins_api`'s Tamiyo Scroll mulligan/misplay counters, [#123/#124](../../issue-scoping/123-124-structured-match-log.md)) | / |
| **Initial date** | 2026-09-15 | Scoped from the request, not yet decided |
| **Status** | 🔲 **Scoped — decision needed** | Do not implement before the Decisions section is answered |
| **Source** | User request during [#123/#124 scoping](../../issue-scoping/123-124-structured-match-log.md) (2026-09-15): *"Plan the addition of a gate engine for admins on goblin guide to open/close features that would be flagged as gateable."* | |
| **Dependency** | **T15** (admin-only Goblin Guide screen precedent — `ServiceAccountsScreen`'s `useCurrentUser()` admin gate + `ForbiddenPanel`); the existing `Role` hierarchy and `require_role()` / `ModeratorUser` / `AdminUser` dependencies in `apps/barrins_api/app/core/roles.py` + `app/dependencies/auth.py` | / |

---

## Context

While scoping [#123/#124](../../issue-scoping/123-124-structured-match-log.md)
(structured per-game mulligan/misplay tracking), the role-gating question
("close circle" restriction, both issues list it as a *possible
evolution*) came back **in scope**, but split into two layers once the
existing infra was checked:

- A **static role floor** already exists and needs no new work:
  `apps/barrins_api/app/core/roles.py` defines `Role.user < moderator <
  ml_developer < admin`; `apps/barrins_api/app/dependencies/auth.py`
  exposes `require_role()` and the `ModeratorUser` / `MLDevUser` /
  `AdminUser` convenience dependencies. Gating a route or a UI section at
  "moderator and above" is a one-line `Depends(require_role(Role.moderator))`
  today.
- What does **not** exist is a way for an **admin to flip a feature on
  or off at runtime**, independent of a code deploy, layered on top of
  that static floor — e.g. "moderator+ users can see the new counters,
  but I (admin) want to switch them off for everyone while I check
  something, without shipping a build." That is the **gate engine**
  this item scopes.

This is deliberately **not** blocking #123/#124: that feature ships
gated at a static `moderator` floor using existing infra now, and
becomes this engine's first registered gate once T16 lands (see
#123/#124 D7). T16 exists so that *this* need — and any future one —
doesn't get a one-off, feature-specific toggle hand-rolled inside
whichever app happens to want it first.

### Why Goblin Guide, not the owning app

Constitution §13.6: account roles/tiers are backend-owned and
auditable, never a frontend-trusted flag. Ownership of roles themselves
sits with `barrins_identity` (ADR-16/ADR-20) — `barrins_api`'s own
`UserRole` enum was retired for exactly this reason. A **generic**
feature-gate registry (not just Tamiyo Scroll's) is the same kind of
cross-app, admin-controlled concern as T15's service-account management,
which already lives in `barrins_identity` + Goblin Guide rather than in
any one consuming app. Parking the registry inside `barrins_api` would
tie a cross-ecosystem admin tool to one app's domain and give Goblin
Guide's admin panel an awkward cross-app call into Tamiyo Scroll's BFF
namespace to manage a Tolaria News or Karn Tablets gate later.

## The data question

A "gate" needs, at minimum:

- a stable **key** the consuming app's code references (e.g.
  `tamiyo_scroll.match_game_log`);
- an **enabled** boolean an admin toggles;
- optionally, a **minimum role** the gate additionally requires (so a
  gate can express "moderator+, and currently on" — matching #123/#124's
  need — or "everyone, and currently on" for a rollout kill-switch with
  no role component at all);
- audit fields (`updated_by`, `updated_at`) — Constitution §13.6's
  "auditable" requirement, and §23.1's ban on silent privilege changes.

Consuming apps need a fast, reliable way to read current gate state
without adding a hard runtime dependency on `barrins_identity`'s
availability for every request.

## Alternatives

### A. Gate registry owned by `barrins_identity`, consumed via `libs/identity_client`

`barrins_identity` gains a small `feature_gates` table
(`key`, `enabled`, `min_role`, `updated_by`, `updated_at`) and two
endpoints: `GET /api/v1/feature-gates` (any authenticated caller —
consuming apps and the Goblin Guide admin screen both read from this)
and `PATCH /api/v1/feature-gates/{key}` (`AdminUser`-equivalent only,
i.e. `barrins_identity`'s own admin check). `libs/identity_client` grows
a `getFeatureGates()` / cached lookup helper any app (backend or
frontend) can call. Goblin Guide gets a new admin-only
`FeatureGatesScreen`, structurally identical to T15's
`ServiceAccountsScreen` (`useCurrentUser()` admin gate, `ForbiddenPanel`
for everyone else, a list + toggle UI, no create/delete — gates are
pre-registered by code, not admin-created).

- **Trade-offs:** reuses T15's exact pattern (admin gate, shared
  library, `libs/identity_client`); keeps the registry where role/access
  concerns already live; works for *any* future consuming app, not just
  Tamiyo Scroll. Cost: every consuming app takes a network dependency on
  `barrins_identity` to read gate state on the request path (mitigated
  by caching — see Decisions below), and `barrins_identity` grows a
  concern (feature flags) slightly outside its original "identity"
  framing, though no more than T15's service-accounts did.

### B. Gate registry owned by `barrins_api`, scoped to Tamiyo Scroll only

A `feature_gates` table and admin endpoints inside `barrins_api`, with
Goblin Guide's admin panel making a cross-app call into `barrins_api` to
manage it (or, worse, Tamiyo Scroll growing its own admin gate screen
outside Goblin Guide entirely).

- **Trade-offs:** zero new work in `barrins_identity`, fastest to ship
  for #123/#124 specifically. Rejected: the user's ask is explicitly
  general ("features," plural, "flagged as gateable" — a registration
  concept, not a Tamiyo-Scroll-specific switch), and this shape either
  breaks Goblin Guide's role as the one admin surface (§13.6) or forces
  every future gate into `barrins_api` regardless of which app owns the
  gated feature. Doesn't scale past the first consumer.

### C. Dedicated new feature-flag service/dependency (e.g. an off-the-shelf flag SaaS or library)

- **Trade-offs:** Rejected outright under §22's dependency-approval
  process — the need (a handful of admin-toggleable booleans, audited,
  role-aware) is far below the complexity an external flag service
  solves for, and it would add a new secret, a new network dependency,
  and a new vendor relationship for a problem the existing identity
  admin surface already covers structurally (per Alternative A).

## Recommendation

**Alternative A.** Registry in `barrins_identity`, `FeatureGatesScreen`
in Goblin Guide mirroring T15, consumed via `libs/identity_client`.

## Decisions needed (flagged, not guessed)

1. **Registry location.** `barrins_identity` (recommended) vs.
   `barrins_api`-scoped vs. external service — confirm Alternative A.
2. **How gates get registered.** Code-declares-key-on-first-use
   (a consuming app calls an idempotent "ensure this key exists,
   default off/on" on startup or first check) vs. a manual migration
   per gate in `barrins_identity` vs. an admin free-text "create a gate"
   affordance in the UI. Recommendation: code-declared keys with a
   migration-seeded default — keeps "what gates exist" reviewable in the
   consuming app's own PR, not typed into a UI by an admin who has to
   know the exact key string.
3. **Read-path performance / staleness tolerance.** A gate check on
   every request to a consuming app's endpoint means either (a) a network
   call to `barrins_identity` per request (adds latency + a hard
   dependency), (b) a short-TTL cache in the consuming app (some staleness
   after an admin toggle, e.g. up to 30–60s), or (c) the gate state
   riding along in the identity JWT/JWKS-verified claims (stale for the
   lifetime of the access token, i.e. until next refresh — likely too
   stale for a "flip it off right now" kill-switch use case). Needs a
   decision before any consuming app wires against this.
4. **Does `min_role` live on the gate, or stay purely in the consuming
   app's own `require_role()` call?** #123/#124 D7 already applies a
   static `moderator` floor independently of any gate. If gates also
   carry a `min_role`, that's two places a role check for the same
   feature could live (drift risk, Constitution §4.2 "never implement
   the same rule twice"). Recommendation: gates are a pure on/off
   switch, no `min_role` field — role floors stay exactly where they are
   today (the consuming app's own `require_role()`), so there's exactly
   one place per feature that decides "who can see this at all," and
   exactly one place that decides "is it currently switched on."
5. **Scope of the first release.** Ship the registry + admin screen with
   zero real gates wired up (pure infra, #123/#124 stays on its static
   `moderator` floor until a follow-up wires it to a real gate), or land
   #123/#124's counters as the very first registered gate in the same
   effort? Recommendation: ship T16 as pure infra first (testable,
   reviewable on its own, no coupling to #123/#124's own schedule), wire
   #123/#124 to it as a small follow-up once both are done.

## Consequences

- **Schema:** one additive migration in `barrins_identity` — new
  `feature_gates` table. No backfill, no destructive change.
- **API contract:** `barrins_identity` gains `GET /api/v1/feature-gates`
  (list, any authenticated caller) and `PATCH
  /api/v1/feature-gates/{key}` (admin only). Documented per §21.1.
- **Frontend:** Goblin Guide gains `FeatureGatesScreen` (admin-only,
  T15-pattern) and a shell route; `libs/identity_client` (or a new
  frontend-side hook in whichever library a consuming frontend uses)
  gains a gate-read helper.
- **Consuming apps:** any app wiring a gate takes on the read-path
  decision from D3 (network call, cache, or claim-embedded) — this is a
  per-consumer implementation detail, not something T16 forces uniformly
  unless D3 lands as a single shared pattern in `libs/identity_client`.
- **Security:** gate writes are `AdminUser`-only and audited
  (`updated_by`/`updated_at`), consistent with §13.6 and §23.1. Gate
  *reads* are available to any authenticated caller (a gate's on/off
  state is not itself sensitive), never anonymous, to avoid leaking the
  existence/naming of unreleased features pre-auth.
- **Docs:** an ADR (`docs/content/ops/architecture/decisions.md`)
  documenting the registry's location and the D3 read-path decision,
  per the constitution's decision-record convention — this item's
  Decisions section above is the input to that ADR, not a substitute for
  it.
- **Tests:** backend — gate CRUD, non-admin `403` on write, `404` on an
  unknown key. Frontend — `FeatureGatesScreen` non-admin access panel
  (mirrors T15's `ServiceAccountsScreen` test), list + toggle happy path.
