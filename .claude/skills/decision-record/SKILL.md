---
name: decision-record
description: "Scaffold a new Context/Alternatives/Trade-offs/Decision/Consequences write-up per constitution §16.3 — either an infrastructure/technical ADR (docs/content/ops/architecture/decisions.md) or a constitution amendment proposal (a docs/project/.../constitution-amendment*.md file, for a change to .claude/CLAUDE.md itself). Use whenever a significant technical decision needs recording, or the user asks for an ADR, a decision record, or a constitution amendment."
argument-hint: "Décision à documenter, et son type (ADR technique ou amendement de constitution)"
---

# Decision-record workflow — Barrin's ecosystem

Every significant technical decision in this project is recorded in one
of two places, using the same five-part structure (Constitution §16.3):
**Context, Alternatives, Trade-offs, Decision, Consequences.** Which
place depends on *what* the decision changes.

## Step 0 — Which kind of record is this?

| If the decision... | ...goes in |
| --- | --- |
| changes infrastructure, an app's architecture, a data-flow/scope choice, a library/tooling pick — anything that doesn't rewrite the constitution's own rules | An **ADR** in `docs/content/ops/architecture/decisions.md` |
| changes, adds, or removes a rule in `.claude/CLAUDE.md` itself | A **constitution amendment proposal**, its own file under `docs/project/<version>-bump/` |

If you're not sure which: an ADR documents a decision made *within* the
constitution's existing rules; an amendment documents a change *to*
those rules. When a piece of work needs both (a new rule **and** the
infrastructure decision that motivated it), write both — the amendment
proposal for the rule, a normal ADR for the implementation decision —
don't conflate them into one document.

## Per constitution §5/§6/§16.2 — this is not optional

Every entry below starts from **STOP: identify alternatives, explain
trade-offs, recommend, ask the user before implementation.** Agent 0
"must never silently choose subjective architecture" — a decision-record
skill exists to make that process consistent, not to let you skip it
because the format felt bureaucratic for a small decision. Write the
record *before* implementing, not as after-the-fact documentation of a
choice already made silently.

## The five-part structure

```markdown
### Context

Why is this decision needed? What triggered it — a feature, an
incident, a gap discovered while doing something else? Cite concrete
evidence (file paths, line numbers, prior ADR/proposal numbers) — never
a vague "we should probably."

### Alternatives

Every real option considered, including "do nothing" / "leave it ad
hoc" when that's genuinely on the table. Number them.

### Trade-offs

For each alternative (or at minimum the ones seriously considered):
what it costs and what it buys. Reference this project's own recurring
tensions where relevant — §39/§48 (no premature implementation/unused
abstractions) is the most commonly-cited one against over-building.

### Decision

The option chosen, stated precisely enough that "Applying this decision"
work items can be extracted directly from it. Not "we'll improve X" —
the exact new rule, the exact new section number, the exact schema
change.

### Consequences

What this changes, for whom, and — just as important — what's
**explicitly not** changed or decided by this record. This project's own
proposals are consistently careful about this last part (e.g. "no
purge/retention job is introduced by this proposal" in §11.8's ADR) —
match that discipline; don't let a reader infer a broader decision than
was actually made.
```

## ADR-specific conventions (`docs/content/ops/architecture/decisions.md`)

- Append as `## ADR-N: <short title>` — check the file's last ADR number
  first (`grep -n "^## ADR-" docs/content/ops/architecture/decisions.md`
  to find it) and increment.
- The file's own opening line states its scope: "Technical decisions for
  `ops/my-server/`" — but in practice it already carries app-level
  decisions too (data flow, library choice, pagination shape). Don't
  over-narrow what belongs here; if truly unsure whether an ADR or an
  amendment is the right target, ask rather than guess (§16.2).
- Escalated decisions (anything the constitution's own §16.2 examples
  list — a new dependency, changed API/workflow/deployment behavior) get
  the same "escalated to the user rather than chosen silently" framing
  the file's own intro states as its norm.

## Amendment-specific conventions (`docs/project/<version>-bump/constitution-amendment*.md`)

Follow the house style already established by
`docs/project/v2.0.0-bump/consitution-amendment.md` and
`docs/project/v2.0.0-bump/constitution-amendment-agents-5-6.md`:

- **Header table**: `Target` (always `.claude/CLAUDE.md` — never
  `docs/content/CLAUDE.md`, a path that has never existed in this repo),
  `Initial date`, `Status`, `Source`.
- **One `## Proposal N — <title>` section per rule**, numbered
  continuing from the highest existing proposal across every
  `constitution-amendment*.md` file in the target release directory —
  check all of them, proposals are numbered globally, not per file.
- **Section-numbering strategy — avoid cascading renumbering.** When the
  new rule is a subsection of an existing numbered section (e.g. a new
  `§13.8` under the existing `§13`), insert it directly — this touches
  nothing else. When the new rule doesn't fit under any existing
  section, prefer a **decimal top-level insertion** (`## 10.5`, the
  pattern `§16.3`, `§47.1/§47.2`, and this project's own Agent 5/Agent 6
  addition all use) over renumbering every section from that point to
  the end of the document — a full renumber touches every cross-
  reference in the constitution and in every document that cites a
  section number, for a purely presentational gain. Only renumber
  top-level sections when a decimal insertion is genuinely impossible;
  if you do, that renumbering is itself worth flagging as its own
  finding, per Proposal 1's own note about avoiding "the larger shift an
  earlier draft of this file miscalculated."
- **A "Status" line per proposal**: 🔲 proposed / ✅ accepted (as written,
  or "with modifications" — and if modified, a "What changed from the
  original proposal" subsection explaining exactly what and why) / ❌
  rejected.
- **Never silently rewrite a previously-recorded decision.** If a later
  fact supersedes something already written as "Confirmed by the user"
  or "Decision," **append** a dated correction note ("Superseded
  YYYY-MM-DD: ...") rather than editing the original text — this project
  hit exactly this case when a role name confirmed as `advanced_user`
  turned out to already be implemented in code as `moderator`; the fix
  was a superseding note, not a rewrite of the historical record.
- **An "Applying these proposals" section at the end**, listing exactly
  what changes when each proposal is applied to `.claude/CLAUDE.md`
  (which section number, which file), and — honestly — what's **still
  outstanding** (an ADR per R5 that hasn't been written yet, a code
  change the doc describes but that hasn't shipped). Don't mark
  something "applied" until you've actually made the corresponding edit
  to `.claude/CLAUDE.md`.

## After writing a decision record

- If it's an ADR: no further constitution edit needed unless the
  decision also implies a new rule (see Step 0's "write both" case).
- If it's an amendment proposal: it is **not** live until you also edit
  `.claude/CLAUDE.md` itself — writing the proposal document is not the
  same as applying it. State clearly, to the user, whether you've done
  both or only the proposal.
- Either way, per §21.2, note the new decision in whatever nearby
  documentation it affects (an app's README, a related design doc) if
  it's not just an internal architecture record.
