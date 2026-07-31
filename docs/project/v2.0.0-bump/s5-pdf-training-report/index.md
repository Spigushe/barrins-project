# S5. PDF report of a training session

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api`, `apps/tamiyo_scroll` | / |
| **Initial date** | 2026-07-30 | / |
| **Status** | ✅ Done (2026-07-31) — **I8 resolved 2026-07-27**: WeasyPrint | / |
| **Source** | Request item 2.4 | / |
| **Dependency** | S3 (more useful once matches carry a version reference), S9 (defines what "training session" actually means — resolves this page's report-scope open task) | / |

---

## Context

No PDF-generation capability exists anywhere in `barrins_api` today.
Constitution §4.1 (backend owns business logic) argues for generating
the PDF server-side, from already-computed stats, rather than composing
it client-side from raw data — consistent with how every other
Tamiyo Scroll calculation already works. Choosing a library
(e.g. WeasyPrint, ReportLab) is itself "introducing a dependency,"
which Constitution §16.2 requires escalating rather than picking
silently.

**Confirmed by the user (2026-07-26)**: this choice **requires a real
ADR**, not just the inline escalation note this page originally had —
tracked as **I8** in the Group I table (`../index.md`), following the
same "foundational decision → R5 writes the ADR" pattern as I1–I7.

## I8 — decided (2026-07-27): WeasyPrint

The user gave the deciding criteria rather than naming a library:
**most stable, still being developed, strong security, no data loss.**
Researched against those criteria (web search, 2026-07-27):

### Alternatives considered

1. **WeasyPrint** — pure-Python HTML/CSS-to-PDF renderer (CSS Paged
   Media spec). Ships releases roughly every 2–3 months — a clear,
   current active-development signal. Two disclosed CVEs: CVE-2025-68616
   (SSRF protection bypass in `default_url_fetcher` via HTTP redirect,
   patched in 68.0) and CVE-2026-49452 (a CSS-properties vulnerability
   affecting `--presentational-hints` on untrusted HTML, patched in a
   later release — exact version to confirm at implementation time).
   Both are scoped to **untrusted HTML / external URL fetching**.
2. **ReportLab** — mature canvas/Platypus-based PDF toolkit, ~3.5M
   monthly PyPI downloads, actively maintained (release cadence less
   clearly evidenced than WeasyPrint's). Two disclosed CVEs, both
   remote-code-execution class: CVE-2023-33733 (RCE via `rl_safe_eval`,
   exploitable through crafted markup converted to PDF, patched in
   3.6.13) and CVE-2019-17626 (RCE via crafted XML in `paraparser`).
   Both stem from expression-evaluation/markup-parsing features built
   into the library's own templating layer — a recurring design-level
   risk surface, not a one-off bug.

### Trade-offs against the stated criteria

- **Security**: WeasyPrint's disclosed vulnerabilities require untrusted
  HTML or external URL fetching to trigger — neither applies here, since
  S5's report is rendered from backend-authored HTML/CSS built from
  already-computed, trusted stats (no user-uploaded HTML, no need to
  fetch remote URLs from within the template). ReportLab's disclosed
  vulnerabilities are RCE-class, tied to a "safe eval"/markup-parsing
  feature that's harder to guarantee is never exercised, since it's part
  of the library's own internal templating rather than an opt-in feature
  the caller can simply avoid using.
- **Actively developed**: WeasyPrint's 2–3 month release cadence is a
  clear, current signal. ReportLab is maintained but its cadence wasn't
  as clearly evidenced in available sources.
- **No data loss**: WeasyPrint's CSS-based layout is close to WYSIWYG —
  what's written in the HTML/CSS template is what renders, the same
  mental model as a browser. ReportLab requires explicitly placing every
  element via its canvas/flowable API — more manual control, but more
  room for a developer to silently omit or truncate content with no
  rendering-time signal, which cuts against "no data loss" for a report
  meant to accurately reflect real stats.
- **Stability**: both are mature libraries; this doesn't separate them.

### Decision

**WeasyPrint**, on the stated criteria: actively developed, disclosed
vulnerabilities don't apply to this trusted, backend-authored use case,
and its CSS-based rendering model reduces the risk of silently-missing
content. Also reuses the team's existing HTML/CSS skillset (the frontend
is already Tailwind-based) rather than introducing an unfamiliar
drawing/flowable API.

### Consequences

- `weasyprint` becomes a new backend dependency (Constitution §22 —
  this research is the required escalation record).
- Pin to the latest release at implementation time, confirmed to include
  fixes for both CVE-2025-68616 (≥68.0) and CVE-2026-49452 (exact
  version to verify then, not asserted here).
- Report templates are authored as HTML/CSS (e.g. Jinja2-rendered HTML
  fed to WeasyPrint), consuming the same `stats`/`decklist_coloring`
  services already used elsewhere (§4.1/§4.2 — no duplicated
  calculation).
- Implementation safeguard: the generated HTML must never include a
  user-controlled or externally-fetched URL (e.g. no remote images from
  arbitrary sources) — only backend-controlled, fixed assets — since
  that's the exact scenario CVE-2025-68616 concerned, even though it's
  patched.
- Sources:
  - [Python PDF library comparison (2026)](https://www.nutrient.io/blog/best-python-pdf-libraries/)
  - [CVE-2025-68616](https://www.sentinelone.com/vulnerability-database/cve-2025-68616/)
  - [CVE-2026-49452 advisory](https://advisories.gitlab.com/pkg/pypi/weasyprint/CVE-2025-68616/)
  - [CVE-2023-33733](https://arcticwolf.com/resources/blog/cve-2023-33733-rce-vulnerability-in-reportlab-pdf-toolkit/)
  - [ReportLab CVE history](https://www.cvedetails.com/vulnerability-list/vendor_id-22377/product_id-76137/Reportlab-Reportlab.html)

This resolves I8.

## Done statement

- `GET .../sessions/{id}/report.pdf`, scoped to one S9 `ts_sessions`
  session, returns a server-rendered PDF (via WeasyPrint) summarizing:
  the decklist version used, matches logged against it during that
  session (leveraging S3's version stamp), win rates vs. the session's
  baseline (S9's comparison, reused rather than recomputed), and
  card-test feedback for the same deck/period.
- **Added during implementation (2026-07-31, user request)**:
  `GET .../personal-decks/{deck_id}/report.pdf` — the same report shape
  with no session required, for a rolling last-30-days window across all
  of a deck's history. Folds in S1's shared/merged sharer data
  (`build_merged_view`) when the viewer has `receive_shared_data`
  enabled, same as the live `/archetype-summary`/`/matchup-summary`
  endpoints. Fixed to the last 30 days for now — letting the caller pick
  the data/timeframe instead is deferred, see
  `docs/content/front/tamiyo_scroll/roadmap.md`'s v2+ table.
- Both reports share one calculation path
  (`stats.compute_period_stats`/`PeriodStats`) and one renderer
  (`report.render_session_report_pdf`) — no duplicated winrate/matchup
  logic between the session-scoped and deck-level variants
  (Constitution §4.2).
- The decklist section is two columns, tight line spacing, and placed
  last in the report (fits on one page for a typical decklist).
- Matches against an archived opponent deck are excluded entirely from
  both reports (and from S9's session comparison, where the same bug
  pre-existed) rather than surfacing as an unresolvable "Opponent deck:
  ?" row.
- No "Baseline games" stat tile — removed from both report variants per
  user request (2026-07-31); the record/winrate baseline comparisons
  stay, only the raw baseline match-count tile was dropped.
- No client-side PDF composition — the frontend only triggers a download
  of a backend-rendered file: a "Download report (PDF)" button on the
  session summary panel, a matching file-pdf icon button per session row
  (`apps/tamiyo_scroll/src/components/icons.tsx`, inlined Font Awesome
  SVG rather than a new icon-library dependency), and a "Download report
  (PDF)" button on the deck's current-decklist section for the
  deck-level report.

## Tasks

- [x] Add `weasyprint` as a backend dependency (pinned to `>=69.0`,
      confirmed to include both CVEs' fixes).
- [x] Design the report's exact scope: **resolved by S9** — "training
      session" is now a real entity (`ts_sessions`), not TBD. The report
      is scoped to one session, reusing S9's session-vs-baseline
      comparison rather than a whole deck's history or an arbitrary date
      range. Extended during implementation with a second, session-less
      "last 30 days" scope for the deck-level report (see Done
      statement).
- [x] Implement the rendering service, consuming the same
      `stats`/`decklist_coloring` services already used elsewhere (no
      duplicated calculation, Constitution §4.2), plus S9's comparison
      output for the session-vs-baseline section.
- [x] Add the download trigger in the frontend (session summary button,
      per-row icon, and deck-level report button).

## UAT (manual)

- [x] Generate a report for a deck with real match/card-test history on
      staging; confirm the PDF's numbers match what the UI already shows
      for the same deck.

## Non-regression tests

- Backend: `tests/tamiyo_scroll/test_session_report.py` and
  `test_deck_report.py` assert the PDF-generating service is called with
  the same numbers the JSON comparison/stats endpoints return (same
  `stats`/`decklist_coloring` calculation, different rendering) rather
  than a parallel calculation — plus coverage for archived-opponent
  exclusion, the 30-day period/baseline split, and shared-data inclusion.
- Frontend: `SessionsSections.test.tsx` and
  `CurrentDecklistSection.test.tsx` assert each download trigger calls
  the report mutation with the right id/filename.
