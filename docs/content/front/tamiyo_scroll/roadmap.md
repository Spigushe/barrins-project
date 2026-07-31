# Tamiyo Scroll — Feature Roadmap

Backlog of Tamiyo Scroll UX/feature requests, distinct from
[Ops Roadmap](../ops/roadmap.md) (release-cut scope and known issues) and
from `docs/project/v2.0.0-bump/index.md` (internal tracking for the
work already committed to v2.0.0 — S1–S12). This page evaluates backlog
items for a future release bucket; adding one to an actual release plan
still needs the escalate-don't-guess step (Constitution §16.2) before
work starts, same as everything in `v2.0.0-bump/index.md`.

**2026-07-30**: the four "v2.0.0 candidates" below were committed to
v2.0.0 scope as **S12** (`v2.0.0-bump/s12-uiux-polish/index.md`) — kept
here for the backlog record, but they're no longer just an evaluation.
Everything else on this page (v2+, v3, v3+) is still backlog-only, not
committed scope.

Buckets, as given:

- **v2** — targeted for v2.0.0.
- **v2+** — v2.0.0 if it fits, otherwise slips to a later release without
  forcing a rescope.
- **v3** / **v3+** — deliberately after v2.0.0.

v2.0.0 is already scoped with S1–S11 (see `v2.0.0-bump/index.md`) — every
"v2" item below is an **addition** to that scope, not a replacement, so
each one competes for the same release window already carrying a large
committed list (team sharing, decklist versioning, PDF reports, admin
metrics, demo/tutorial, MTGJSON pipeline...). Treat the v2 placements
below as provisional until checked against that existing load.

## v2.0.0 candidates — committed as S12

| Item | Assessment |
| --- | --- |
| Personal-deck creation unclear → add iconography | Pure frontend polish, no backend/schema touch. Cheap, low-risk. **Resolved without a new dependency**: a green `[new]` text label next to the create row (plain Tailwind), not an icon — sidesteps the fact that no icon library exists in `apps/tamiyo_scroll` today. See the S12 page. |
| "Tested cards" matchup select UI to match BO3 opponent select | UI-consistency fix reusing an existing component pattern (`OpponentDeckField`'s combobox). Cheap. |
| Label "final turn" → "winning/losing turns" | Copy-only change — the field is free text, not a turn number, so this is purely a display-label rename, no schema/API impact. Exact final copy still open (see S12 page). |
| Matchup summary column "games" → "matches" | Copy-only change — the column already counts `match_count`; only the header text was wrong. |

**Net assessment**: all four are genuinely cheap (no schema, no new
endpoint, no design pass) and don't compete meaningfully with S1–S11 for
engineering time. **Committed to v2.0.0 as S12**
(`v2.0.0-bump/s12-uiux-polish/index.md`) — full task breakdown, exact
file/line references, and open questions live there.

## v2.0.0-or-later (v2+)

| Item | Assessment |
| --- | --- |
| Edit a match's date | Small CRUD addition — one field, one endpoint update, straightforward form change. Fits the "v2+" bucket cleanly; could realistically go into v2 outright if the two v2+ items below don't. |
| Add opponent name/alias | New field on the match record, plus a form input. Same shape and size as the date edit above — cheap, fits v2+ well. |
| "Portable app" download mode → **PWA (Progressive Web App)** | Clarified: this means installability (manifest + service worker), not a native/Electron-style package. Re-assessed and no longer flagged — a PWA sits naturally on top of the existing Vite/React stack (`vite-plugin-pwa` or an equivalent manifest+service-worker setup), keeps the single nginx-served-SPA deployment shape (§26–§32 untouched, no second build/deploy pipeline), and doesn't need anything like Electron/Tauri. It still needs the ordinary new-dependency approval step (§4.7/§22 — problem, alternatives, maintenance impact) for whichever PWA plugin is chosen, and one scoping question before implementation: how far "offline" goes — installability + static-asset caching only (cheap, low-risk), versus caching/queuing live match data for use while offline (touches §4.1's "backend owns business logic" and data-freshness — a BO3 tracked offline and synced later needs a conflict/merge story). Scoped to the first (installable, cached shell, no offline writes), this fits v2+ comfortably. |
| Configurable data/timeframe for the deck-level PDF report (run outside a session) | Flagged by the user 2026-07-31 while building S5's deck-level report (`GET .../personal-decks/{deck_id}/report.pdf`), which ships v2.0.0 fixed to a rolling last-30-days window covering all data. This item lets the caller pick which data goes into that report and over what timeframe, instead of the fixed window — a report-builder UI (date range + section toggles) plus a parameterized version of `report.py`'s renderer/`compute_period_stats` caller. Self-contained addition on top of already-shipped S5 infrastructure, no new domain concept — v2+ is appropriate. |

## v3.0.0 candidates

| Item | Assessment |
| --- | --- |
| Match tracker: error count + comment on both sides | Error count/comment ship in the same change that removes the "turning point" block from the tracker UI . The `turning_point` column itself stays in the schema (kept for historical data, not dropped/migrated away) — only its display goes away, new columns (`error_count`, `comment`) get added per side. Backend schema change (additive, no destructive migration) plus tracker UI rework. Medium effort — reasonable v3, heavier than the v2+ items above. |
| New winrate starting/not-starting per match | Depends on whether on-the-play/on-the-draw is already captured per game — if it's already recorded (worth checking against the current match schema before scoping further), this is mostly an aggregation/report addition; if not, it needs a new field first. Either way it's a backend calculation plus a report UI addition — v3 is reasonable, but check the existing schema first since it may be cheaper than it looks. |
| "Other" mode for archetype winrate calc, user-chosen tier threshold | A genuine configuration feature (user-defined aggregation threshold), touching both the winrate calculation service and its UI. Correctly sized for v3 — not a small addition. |
| Co-admin a team | Extends the team model decided for v2.0.0 (`v2.0.0-bump/index.md` §1.6 — single owner/creator, no additional roles for v2.0.0). Adding a co-admin role is a deliberate, already-anticipated follow-on (the schema doesn't block it), correctly deferred until after S2 ships and is in real use — v3 is the right bucket, and it should stay sequenced *after* S2 lands, not in parallel with it. |

## v3.0.0-or-later (v3+)

| Item | Assessment |
| --- | --- |
| Opening-hand autocomplete (from decklist) + mulligan counts per side, one row per game | The most substantial item on this list: new per-game data (today's granularity should be checked — if matches only track BO3-level results, this needs a new per-game table), a mulligan-count field per side, and an autocomplete UI sourced from decklist contents. Correctly placed at v3+, and likely deserves its own scoping pass (in the `v2.0.0-bump/index.md` §1 style) before it's committed to any release. |
| Module selection for "new game" (BO3) screen | A UI configuration/preferences feature — which fields/modules show during match entry. Self-contained, no schema risk beyond a user-preferences flag. Correctly v3+; could move up if it turns out cheap once scoped. |
| OTP/OTD winrate by archetype on the PDF report | Depends on "winrate starting/not-starting per match" (the v3 item above) landing first — this is that data surfaced in the PDF report (S5, already v2.0.0 scope) rather than a new calculation. Correctly sequenced after its dependency; v3+ (or right after its v3 dependency ships) is appropriate. |

## Cross-cutting notes

- Three items (co-admin a team, OTP/OTD on PDF, opening-hand tracking)
  each depend on something else on this list or in `v2.0.0-bump/index.md`
  landing first (S2, the starting/not-starting winrate item, and a
  per-game data model respectively) — sequence, don't parallelize, these.
- The PWA item's bucket depends on staying scoped to installability +
  asset caching. If "offline mode" later grows to include queuing live
  match writes made while offline, re-evaluate — that's a materially
  different (and heavier) feature than what's costed into v2+ here.
- Everything below the v2 section is still backlog-only — not added to
  `v2.0.0-bump/index.md`'s committed scope. If any v2+/v3/v3+ item here
  is meant to actually ship in a given release, it needs adding there
  (with the same Context/Alternatives/Trade-offs treatment S1–S12 got)
  rather than tracked only on this page.

## See also

- [Ops Roadmap](../ops/roadmap.md) — release-cut scope and known issues,
  v1.0.0 → v2.0.0.
- `docs/project/v2.0.0-bump/index.md` (internal tracking, not part of
  this published site) — the committed v2.0.0 scope (S1–S12) this
  backlog is evaluated against.
