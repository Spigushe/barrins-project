# Constitution amendment proposals — Agent 5 & Agent 6

[← Back to project index](index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `.claude/CLAUDE.md` (the project constitution) | / |
| **Initial date** | 2026-09-04 | / |
| **Status** | ✅ Proposals 9 and 10 accepted as written (2026-09-04) and applied directly to `.claude/CLAUDE.md` the same day, at the user's explicit request — same treatment as Proposal 8 in `consitution-amendment.md`, not held for a separate review round. | / |
| **Source** | A requested evaluation of the constitution against the repository's actual current shape (7 apps: `barrins_api`, `barrins_identity`, `barrins_scripture`, `goblin_guide`, `karn_tablets`, `tamiyo_scroll`, `tolaria_news`), which surfaced two apps with real architectural weight and no owning agent. | / |

---

## Why this file exists

`.claude/CLAUDE.md` §5–§10 define five agents (Agent 0 through Agent 4),
each with an explicit `Repository:` — Barrin's API (Agent 1), Tamiyo
Scroll (Agent 2), infrastructure (Agent 3), UX (Agent 4), and the
cross-cutting Agent 0. Comparing that list against `apps/` shows two
applications with no owning agent at all:

- **`karn_tablets`** — Duel Commander metagame clustering. The
  constitution already anticipates this discipline in detail (§45
  "Machine Learning Integration": isolation from frontend/auth/reports/
  core domain, reproducibility, dataset/model versioning) but never
  assigns an agent to it. In the repository, `karn_tablets` is real and
  shipping (ADR-6, ADR-13, ADR-15), feeding Tolaria News' public
  `/metagame`/`/archetypes` routes and Tamiyo Scroll's S6 admin
  dashboard.
- **`barrins_identity`** — the RS256 JWT/JWKS identity service. Five ADRs
  (ADR-16 through ADR-20) record its build-out, including `barrins_api`
  dropping its own `users` table and `UserRole` enum to trust
  `barrins_identity`'s JWKS instead. §13 states identity must stay
  "centralized" but never says which agent owns that centralization, and
  Agent 1's `Repository:` line is scoped to "Barrin's API" specifically,
  not to `barrins_identity`.

Per §6 (Agent 0 must never silently choose subjective architecture; must
identify alternatives, explain trade-offs, recommend, and ask the user
before implementation) and §16.3 (every significant technical decision
needs Context/Alternatives/Trade-offs/Decision/Consequences), both
proposals below were presented to the user for independent judgment
before being written into the constitution.

**Reviewed and accepted by the user, 2026-09-04**: both proposals
accepted as presented, plus an explicit instruction that they be
implemented two ways at once — as constitution prose (this document,
applied to `.claude/CLAUDE.md`) **and** as real, invocable Claude Code
subagents (`.claude/agents/agent-5-ml-data-lead.md`,
`.claude/agents/agent-6-identity-access-lead.md`) — see "Applying these
proposals" below.

---

## Proposal 9 — Agent 5: ML & Data Science Lead (Karn Tablets)

**Status: ✅ Accepted as written (2026-09-04)**

**Target**: new section `§10.5` (after `§10` Agent 4, before `§11`
Backend Development Standards).

### Context

`karn_tablets` implements exactly the discipline §45 already describes
in the abstract — clustering, archetype extraction, isolation from the
core domain — but no agent in §6–§10 is responsible for it. In practice
this means whichever agent happens to touch `karn_tablets` (most likely
Agent 1, since it is Python) inherits ML-specific obligations (§45.2:
every result needs source data, dataset version, and model information)
that are not part of Agent 1's own listed responsibilities and easy to
drop under the assumption "it's just another Python service."

### Alternatives

1. **Say nothing.** Leave `karn_tablets` implicitly under Agent 1 by
   widening Agent 1's `Repository:` line from "Barrin's API" to "all
   backend Python services."
2. **Create Agent 5, scoped to `karn_tablets` and its ML discipline
   specifically** — chosen.
3. **Fold `karn_tablets` under Agent 0** (Solution Architect), on the
   grounds that ML work is cross-cutting and already touches §45's
   ecosystem-wide rules.

### Trade-offs

Option 1 is cheapest to write but re-creates the exact failure mode §45
was written to prevent: a generalist backend agent optimizing for
`barrins_api`'s domain concerns (API contracts, migrations, business
rules) has no natural reason to prioritize dataset reproducibility or
model versioning — these are ML-specific disciplines, not generic
backend ones. Option 3 overloads Agent 0, whose role (§6) is review,
validation, and cross-project coordination, not hands-on implementation
of any one service — assigning it a specific app's day-to-day ownership
contradicts "Agent 0 does not replace implementation agents." Option 2
costs one more agent definition but keeps the ML discipline's specific
obligations (§45.1/§45.2) attached to an agent whose whole mandate is
that discipline, the same way Agent 2's UX-specific concerns don't leak
into Agent 1's checklist today.

### Decision

Add `§10.5 Agent 5 — ML & Data Science Lead`, mirroring Agent 0–4's
existing structure (Role / Repository / Responsibilities / Restrictions).
Repository: Karn Tablets. Responsibilities include maintaining the
clustering/archetype pipeline, keeping ML isolated per §45.1, enforcing
§45.2's data-quality requirements, maintaining job-health observability
(ADR-15), and bringing future ML features (§45's card-impact weighting,
matchup analysis, etc.) to Agent 0 for review before scope grows, per
§39/§48. Restrictions explicitly forbid embedding ML inference directly
into `barrins_api`'s domain services, shipping against unvalidated data,
or exposing model internals as a raw API contract (must go through a
DTO/schema boundary per §4.3). See `.claude/CLAUDE.md` §10.5 for the
full text as applied.

### Consequences

`karn_tablets` gets an agent whose full mandate is its own discipline,
instead of inheriting ML-specific obligations as an afterthought to a
generalist backend role. Doesn't block or require any change to
`karn_tablets`'s current implementation — this is a governance change,
not a code change.

---

## Proposal 10 — Agent 6: Identity & Access Lead (Barrins Identity)

**Status: ✅ Accepted as written (2026-09-04)**

**Target**: new section `§10.6` (after the new `§10.5`, before `§11`
Backend Development Standards).

### Context

`barrins_identity` is now the ecosystem's single identity authority
(ADR-16 through ADR-20): it issues and signs RS256 JWTs, publishes a
JWKS endpoint every other app verifies against, owns the cross-app user
directory (ADR-19), and `barrins_api` has already dropped its own
`users` table and `UserRole` enum to depend on it (ADR-20). §13
("Authentication Architecture") states identity decisions "must remain
centralized" but assigns no agent to that centralization, and neither
Agent 1 (`Repository: Barrin's API`) nor Agent 3 (infrastructure
security — CORS, TLS, VPS hardening, not auth-protocol design) covers
it today.

### Alternatives

1. **Say nothing.** Treat `barrins_identity` as within Agent 1's scope
   once Agent 1's repository line is widened (same widening as Proposal
   9's Option 1 would require for `karn_tablets`).
2. **Fold identity into Agent 3.** Agent 3 already lists "security
   hardening" and owned "authentication; authorization" language exists
   in Agent 0's Authority list (§6) — extend Agent 3's mandate downward
   into protocol-level identity design.
3. **Create Agent 6, scoped to `barrins_identity` and the identity
   protocol specifically** — chosen.

### Trade-offs

Option 1 repeats the same problem Proposal 9 rejected for
`karn_tablets`: a generalist backend agent has no specific reason to
prioritize identity's distinct concerns (token/cookie security
properties, JWKS rotation, cross-app directory consistency) over
`barrins_api`'s own domain work. Option 2 conflates two different kinds
of security: Agent 3's mandate (§9) is infrastructure-level — VPS,
reverse proxy, TLS, CORS — while identity protocol design (signing
algorithm choice, refresh-token/cookie handling, role-claim shape) is an
application-level concern that five dedicated ADRs already treat as its
own body of decisions, not an infrastructure afterthought; conflating
them risks Agent 3 becoming responsible for decisions it has no
protocol-level context to make well. Option 3 costs one more agent
definition but matches the weight `barrins_identity` already carries in
the ADR log (5 dedicated ADRs, more than any single feature elsewhere in
the project) and gives every consuming app (`barrins_api`, Tamiyo
Scroll, Tolaria News, Goblin Guide) one clear place to point disputes
about identity contracts, rather than negotiating with whichever agent
happens to own the calling app that week.

### Decision

Add `§10.6 Agent 6 — Identity & Access Lead`, mirroring Agent 0–4's
existing structure. Repository: Barrin's Identity, plus the
identity-facing parts of Goblin Guide, `libs/identity_client/`, and
`libs/goblin_guide/`. Responsibilities include owning JWT/JWKS design
(§13.1, ADR-16), account roles/tiers (§13.6) and the group/team
ownership-transfer path (§13.7), the cross-app directory (ADR-19), and
coordinating the identity cutover for every consuming app so none of
them re-implements its own user table (§13.1). Restrictions explicitly
forbid a consuming app maintaining a parallel user/role source of truth,
changing token/cookie security properties without Agent 3 and Agent 0
sign-off (since that crosses into Agent 3's CORS/TLS-adjacent
infrastructure-security territory), or exposing internal identity
implementation details (§23.1). See `.claude/CLAUDE.md` §10.6 for the
full text as applied.

### Consequences

Gives the ecosystem's single identity authority a named, accountable
owner instead of leaving it to whichever agent happens to be touching
`barrins_api` or Goblin Guide that day. The explicit "Agent 3 + Agent 0
sign-off" restriction on security-property changes is a deliberate seam
between Agent 6 (protocol design) and Agent 3 (infrastructure) —
intended to prevent exactly the conflation Option 2 above would have
caused, not to create a standing turf dispute; if the two agents
disagree in practice, §5's conflict-resolution process (STOP, present
alternatives, wait for the user) applies same as any other
inter-agent disagreement.

---

## Open item — not adopted: a Data Ingestion Lead for Barrins Scripture

A third candidate was raised during the underlying evaluation:
`barrins_scripture` (the MTGO/MTGTop8 scraper) has its own real
discipline — external-site scraping resilience, archive-first behavior,
and a documented production incident
(`docs/project/v2.0.0-bump/barrins-scripture-mtgtop8-oom-incident.md`).
Constitution Amendment Proposal 4 (bulk/heavy data must not live in the
primary repository, `.claude/CLAUDE.md` §26.5) is directly downstream of
this app's needs.

**This candidate is not proposed for adoption here.** Unlike
`karn_tablets` and `barrins_identity`, `barrins_scripture`'s distinct
concerns (scrape resilience, archive discipline) are narrower in scope
and don't yet carry a comparable weight of dedicated architectural
decisions (no ADRs are dedicated solely to it the way ADR-16–20 are to
identity). Recorded here as an open question rather than silently
dropped, per §16.2 — if `barrins_scripture` grows a comparable body of
dedicated decisions, this is where that future proposal should be added.

---

## A note on section numbering

Both new agents are inserted as `§10.5` and `§10.6` — decimal
subsections of the existing `§5`–`§10` Agent Governance block — rather
than as new top-level sections (which would require renumbering every
section from the old `§11` onward, all the way through the old `§51`/
`§52`, and updating every cross-reference in this document and
elsewhere in the repository that cites a section number). This follows
the same precedent `consitution-amendment.md` already established for
§13.6/§13.7/§16.3/§47.1/§47.2 in the live constitution: a decimal
insertion that touches nothing else, chosen deliberately over a
full-document renumber for the same reason that document gives — the
smaller, surgical change is preferred when it fully solves the problem
without inventing disruption nobody asked for (§39/§48).

This is a presentation-level choice, not a substantive one: it does not
change Agent 5/6's authority or standing relative to Agent 0–4, only
how the section is numbered.

---

## Applying these proposals

Applied directly to `.claude/CLAUDE.md`, 2026-09-04, as part of the same
pass that also caught up Proposals 2–6 from `consitution-amendment.md`
(see that document's own "Applying these proposals" section):

1. Inserted `§10.5 Agent 5 — ML & Data Science Lead` and `§10.6 Agent 6 —
   Identity & Access Lead`, both after `§10` Agent 4 and before `§11`
   Backend Development Standards, per the numbering note above.
2. Implemented both agents a second way, per the user's explicit
   instruction ("both" — prose and real subagents, not one or the
   other): `.claude/agents/agent-5-ml-data-lead.md` and
   `.claude/agents/agent-6-identity-access-lead.md`, invocable Claude
   Code subagents whose system prompts are derived from this document
   and the corresponding constitution sections, not a separate,
   independently-drifting description.
3. **Still outstanding, not done in this pass**: per §21.2 (architecture
   documentation) and the same R5/ADR expectation
   `consitution-amendment.md` already flags as outstanding for
   Proposals 1–6, a dedicated ADR recording this agent-governance change
   has not been written. Whoever runs the next ADR pass should include
   Proposals 9 and 10 alongside the still-outstanding 1–6.
