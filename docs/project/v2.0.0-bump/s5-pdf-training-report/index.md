# S5. PDF report of a training session

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/barrins_api`, `apps/tamiyo_scroll` | / |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — needs a PDF-library escalation (Constitution §16.2) | / |
| **Source** | Request item 2.4 | / |
| **Dependency** | S3 (more useful once matches carry a version reference) | / |

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

## Done statement (once the library choice is escalated and confirmed)

- A new endpoint (e.g. `GET .../personal-decks/{id}/report.pdf` or
  scoped to a training session/date range — exact scope TBD) returns a
  server-rendered PDF summarizing: the decklist version used, matches
  logged against it (leveraging S3's version stamp), win rates, and
  card-test feedback.
- No client-side PDF composition — the frontend only triggers a download
  of a backend-rendered file.

## Tasks

- [ ] Escalate the PDF-library choice (WeasyPrint vs. ReportLab vs.
      another) — not decided here.
- [ ] Design the report's exact scope: one training session vs. a whole
      deck's history vs. a date range — not specified in the request,
      needs a follow-up question before implementation.
- [ ] Implement the rendering service, consuming the same
      `stats`/`decklist_coloring` services already used elsewhere (no
      duplicated calculation, Constitution §4.2).
- [ ] Add the download trigger in the frontend.

## UAT (manual)

- [ ] Generate a report for a deck with real match/card-test history on
      staging; confirm the PDF's numbers match what the UI already shows
      for the same deck.

## Non-regression tests

- New backend test asserting the PDF-generating service calls the same
  `stats`/`decklist_coloring` functions as the JSON endpoints (same
  numbers, different rendering) rather than a parallel calculation.
