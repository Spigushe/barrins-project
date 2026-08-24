"""Server-rendered PDF report for a session or a rolling period (S5).

HTML is built with plain string formatting (same convention as
`services/email/smtp_sender.py` — "no pip templating dependency"), then
rendered to PDF via WeasyPrint (I8). Every number here is read from
already-computed `stats`/`decklist_coloring` output, never recalculated —
Constitution §4.1/§4.2.

Two callers feed this module: a specific `TSSession` (sessions.py) and a
rolling "last 30 days" window with no session at all (personal_decks.py)
— see `docs/project/v2.0.0-bump/s5-pdf-training-report/`. Neither the
renderer nor `resolve_report_decklist_version` below know about that
distinction; they only take titles/labels and already-resolved data.

Security note (I8's consequence): the generated HTML must never embed a
user-controlled or externally-fetched URL (no remote images, no
`url()` pointing outside this process) — the exact surface
CVE-2025-68616 concerned, even though it's patched in the pinned version.
Every value below is either a fixed label or escaped user text.
"""

from collections.abc import Sequence
from datetime import datetime
from html import escape

from weasyprint import HTML

from app.models.tamiyo_scroll import (
    TSCardTest,
    TSCardTestEvaluation,
    TSPersonalDecklistVersion,
)
from app.services.tamiyo_scroll.decklist_coloring import ColoredLine
from app.services.tamiyo_scroll.stats import MatchLike, MatchupRow


def _fmt_dt(value: datetime | None) -> str:
    return "—" if value is None else value.strftime("%Y-%m-%d %H:%M UTC")


def _fmt_pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}%"


def format_period(start: datetime, end: datetime | None) -> str:
    """`"Since {start}"` (open-ended) or `"{start} → {end}"` (closed)."""
    if end is None:
        return f"Since {_fmt_dt(start)}"
    return f"{_fmt_dt(start)} → {_fmt_dt(end)}"


def resolve_report_decklist_version(
    versions: Sequence[TSPersonalDecklistVersion],
    period_matches: Sequence[MatchLike],
) -> TSPersonalDecklistVersion | None:
    """The decklist version "used" during the reported period.

    The highest-versioned one referenced by any match in `period_matches`
    — matches carry `decklist_version_id` per S3. Falls back to the
    deck's latest version overall (same rule as
    `personal_decks.get_decklist_view`) when none of those matches
    reference one yet (e.g. an empty period, or pre-S3 matches).
    """
    if not versions:
        return None
    referenced_ids = {
        m.decklist_version_id for m in period_matches if m.decklist_version_id
    }
    referenced = [v for v in versions if v.id in referenced_ids]
    if referenced:
        return max(referenced, key=lambda v: v.version)
    return max(versions, key=lambda v: v.version)


def _stat_tile(label: str, value: str) -> str:
    return (
        '<div class="stat-tile">'
        f'<div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(value)}</div>'
        "</div>"
    )


def _decklist_lines_html(lines: Sequence[ColoredLine]) -> str:
    return "".join(
        f'<div class="decklist-line status-{escape(line["status"])}">'
        f"{escape(line['line'])}</div>"
        for line in lines
    )


def _decklist_section_html(
    version_label: str, colored_lines: Sequence[ColoredLine]
) -> str:
    if not colored_lines:
        return "<p><em>No decklist version available for this deck.</em></p>"
    # Blank lines (section separators in the raw decklist text, e.g.
    # between spells and lands) are dropped rather than rendered as an
    # empty row — printing one would waste a full line-height of vertical
    # space for nothing, working against the one-page goal.
    non_blank = [line for line in colored_lines if line["line"].strip()]
    # Two columns via flexbox, split manually — CSS `column-count`'s
    # balance mode stretches short content to fill the *entire* remaining
    # page height (spreading 60 lines across a whole page), rather than
    # packing them tightly; a manual split sidesteps that entirely.
    midpoint = (len(non_blank) + 1) // 2
    left = _decklist_lines_html(non_blank[:midpoint])
    right = _decklist_lines_html(non_blank[midpoint:])
    label_html = f'<p class="version-label">{escape(version_label)}</p>'
    return (
        f"{label_html}"
        '<div class="decklist">'
        f'<div class="decklist-col">{left}</div>'
        f'<div class="decklist-col">{right}</div>'
        "</div>"
    )


def _matchup_table_html(
    period_label: str,
    period_rows: Sequence[MatchupRow],
    baseline_rows: Sequence[MatchupRow],
) -> str:
    if not period_rows:
        return ""
    baseline_by_opponent = {row["opponent_deck_id"]: row for row in baseline_rows}
    body_rows = []
    for row in period_rows:
        baseline = baseline_by_opponent.get(row["opponent_deck_id"])
        baseline_winrate = baseline["winrate_global"] if baseline else None
        body_rows.append(
            "<tr>"
            f"<td>{escape(row['opponent_deck_name'])}</td>"
            f"<td>{row['match_count']}</td>"
            f"<td>{_fmt_pct(row['winrate_global'])}</td>"
            f"<td>{_fmt_pct(baseline_winrate)}</td>"
            "</tr>"
        )
    header = (
        "<tr><th>Opponent deck</th><th>Matches</th>"
        f"<th>{escape(period_label)} winrate</th>"
        f"<th>Winrate before {escape(period_label.lower())}</th></tr>"
    )
    return (
        "<h2>Matchup comparison</h2>"
        f"<table><thead>{header}</thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table>"
    )


def _card_tests_table_html(
    card_tests: Sequence[TSCardTest], evaluations: Sequence[TSCardTestEvaluation]
) -> str:
    """One row per evaluation (S17) -- a card log with no evaluation yet
    has no rating to report, so it doesn't appear here; its own overall
    `notes` isn't "feedback" in the rating sense this table reports."""
    if not evaluations:
        return "<p><em>No card feedback logged during this period.</em></p>"
    test_by_id = {test.id: test for test in card_tests}
    body_rows = []
    for evaluation in evaluations:
        test = test_by_id.get(evaluation.test_id)
        if test is None:
            continue
        body_rows.append(
            "<tr>"
            f"<td>{escape(test.removed_card_name)}</td>"
            f"<td>{escape(test.added_card_name)}</td>"
            f"<td>{evaluation.rating}/5</td>"
            f"<td>{escape(evaluation.notes or '—')}</td>"
            "</tr>"
        )
    header = (
        "<tr><th>Removed Card</th><th>Added Card</th><th>Rating</th><th>Notes</th></tr>"
    )
    return f"<table><thead>{header}</thead><tbody>{''.join(body_rows)}</tbody></table>"


_CSS = """
@page { size: A4; margin: 1.4cm; }
body { font-family: sans-serif; font-size: 10px; color: #1a1a1a; }
h1 { font-size: 18px; margin-bottom: 0.15em; }
h2 {
  font-size: 12px; margin-top: 0.9em; margin-bottom: 0.3em;
  border-bottom: 1px solid #ccc; padding-bottom: 0.15em;
}
.subtitle { color: #555; margin-top: 0; margin-bottom: 0.5em; }
.version-label { color: #555; font-style: italic; margin: 0 0 0.3em; }
.stat-grid { display: flex; flex-wrap: wrap; gap: 8px; margin: 0.5em 0; }
.stat-tile {
  background: #f2f2f2; border-radius: 6px;
  padding: 5px 10px; min-width: 110px;
}
.stat-tile .label { font-size: 8px; text-transform: uppercase; color: #666; }
.stat-tile .value { font-size: 14px; font-weight: bold; }
table { width: 100%; border-collapse: collapse; margin-top: 0.3em; }
th, td { border: 1px solid #ddd; padding: 2px 5px; text-align: left; font-size: 9px; }
th { background: #f2f2f2; }
.decklist {
  display: flex; gap: 20px;
  font-family: monospace; font-size: 8.5px; line-height: 1.15;
}
.decklist-col { flex: 1; white-space: pre-wrap; }
.decklist-line { padding: 0; }
.status-validated { color: #157347; }
.status-rejected { color: #b02a37; }
.status-in_test { color: #997404; }
.status-neutral { color: #1a1a1a; }
.status-pending { color: #0b5ed7; }
"""


def render_session_report_pdf(
    *,
    title: str,
    subtitle: str,
    period_label: str,
    decklist_version_label: str,
    colored_lines: Sequence[ColoredLine],
    period_match_count: int,
    period_wins: int,
    period_losses: int,
    baseline_wins: int,
    baseline_losses: int,
    period_matchup_rows: Sequence[MatchupRow],
    baseline_matchup_rows: Sequence[MatchupRow],
    card_tests: Sequence[TSCardTest],
    evaluations: Sequence[TSCardTestEvaluation],
) -> bytes:
    """Render a session or rolling-period report to PDF bytes.

    Pure function over already-computed data — never recalculates
    anything itself (Constitution §4.2). `period_label` names the
    reported window in prose (e.g. "Session" or "Last 30 days") and
    drives the stat-tile/table labels below.
    """
    period_winrate = None
    decisive = period_wins + period_losses
    if decisive:
        period_winrate = round(period_wins / decisive * 100, 2)
    baseline_winrate = None
    baseline_decisive = baseline_wins + baseline_losses
    if baseline_decisive:
        baseline_winrate = round(baseline_wins / baseline_decisive * 100, 2)

    stat_grid = "".join(
        [
            _stat_tile(f"{period_label} games", str(period_match_count)),
            _stat_tile(f"{period_label} record", f"{period_wins}W / {period_losses}L"),
            _stat_tile(f"{period_label} winrate", _fmt_pct(period_winrate)),
            _stat_tile(
                f"Winrate before {period_label.lower()}", _fmt_pct(baseline_winrate)
            ),
        ]
    )
    matchup_section = _matchup_table_html(
        period_label, period_matchup_rows, baseline_matchup_rows
    )

    html = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><style>{_CSS}</style></head>
<body>
  <h1>{escape(title)}</h1>
  <p class="subtitle">{escape(subtitle)}</p>

  <div class="stat-grid">{stat_grid}</div>

  {matchup_section}

  <h2>Card feedback during this period</h2>
  {_card_tests_table_html(card_tests, evaluations)}

  <h2>Decklist used</h2>
  {_decklist_section_html(decklist_version_label, colored_lines)}
</body>
</html>"""

    return HTML(string=html).write_pdf()
