"""Local, personal report: aggregate every Duel Commander deck of one commander.

Not part of the scheduled Karn Tablets job (nothing here is pushed to
barrins_api, nothing is exposed as an API contract) -- a manual analysis
tool, run by hand to study one commander's decks and work towards a
functional list.

Inspired by barrins-archive/mtgdc_aggregator and the archived
barrins_api/app/services/ml/dc_report.py, rebuilt on top of what Karn Tablets
already ships (aggregation.aggregate_decks, features.FUNCTION_PATTERNS,
dc_calendar) -- no PDF/plotly/kaleido, Markdown + CSV + Moxfield .txt only.

Read-only: only SELECT queries, never writes to the database.

Usage (from the repo root, PowerShell):
    $env:REPORT_DATABASE_URL = "postgresql://<user>:<pwd>@<host>:5432/<db>"
    uv run --project apps/karn_tablets python `
        apps/karn_tablets/scripts/commander_report.py --commander "Ertai Resurrected"

Options worth knowing:
    --commander X [--commander Y]  repeat for a partner pair (both required)
    --exact                        command zone must be exactly these commanders
    --days 365                     history length (or --date-from / --date-to)
    --deck my_deck.txt             compare a Moxfield export against the meta
    --study "Card A" "Card B"      detailed playability of specific cards
    --order 2 --limit 100          aggregation order / max decks aggregated

DB URL: REPORT_DATABASE_URL, else KARN_TABLETS_DATABASE_URL_RO from
apps/karn_tablets/.env. The credential needs SELECT on bs_* and mj_cards;
mj_cards.legalities (banlist filter) and mj_sets (recent-card suggestions)
are optional -- each section is skipped with a warning when unavailable.

Output: scripts/outputs/<commander>-<date>/ (git-ignored) unless --out is
given -- report.md, aggregated.txt, variant_<k>.txt, cards.csv.
"""

import argparse
import datetime as dt
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from dc_calendar.windowing import banlist_period_containing
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from karn_tablets.aggregation import aggregate_decks
from karn_tablets.extract import _with_sync_driver
from karn_tablets.features import FUNCTION_PATTERNS
from karn_tablets.schemas import Decklist

APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = Path(__file__).resolve().parent / "outputs"
# Same markdownlint config CI applies to docs/content (.github/workflows/CI.yml).
MARKDOWNLINT_CONFIG = APP_ROOT.parents[1] / "docs" / ".markdownlint.jsonc"
MD_WRAP = 80  # MD013's default line length

FORMAT = "Duel Commander"
PRIMARY_TYPES = [
    "Land",
    "Creature",
    "Planeswalker",
    "Battle",
    "Instant",
    "Sorcery",
    "Artifact",
    "Enchantment",
]


# ─── Data access ──────────────────────────────────────────────────────────────


class DB:
    def __init__(self, url: str) -> None:
        self.engine = create_engine(_with_sync_driver(url), pool_pre_ping=True)

    def q(self, sql: str, params: dict | None = None) -> pd.DataFrame:
        with self.engine.connect() as conn:
            return pd.read_sql_query(text(sql), conn, params=params or {})


def load_decks(
    db: DB, commanders: list[str], exact: bool, date_from: dt.date, date_to: dt.date
) -> pd.DataFrame:
    exists = "\n".join(
        "AND EXISTS (SELECT 1 FROM bs_deck_cards c WHERE c.deck_id = d.id "  # noqa: S608
        f"AND c.board = 'sideboard' AND c.card_name ILIKE :cmd{i})"
        for i in range(len(commanders))
    )
    if exact:
        exists += (
            "\nAND (SELECT count(*) FROM bs_deck_cards c WHERE c.deck_id = d.id "
            "AND c.board = 'sideboard') = :n_cmd"
        )
    # S608: only fixed SQL fragments are interpolated (`exists` above);
    # every user-supplied value (commander names) goes through bound params.
    sql = f"""
        SELECT d.id::text AS deck_id, d.player, d.result, d.date,
               t.id::text AS tournament_id, t.name AS tournament_name,
               t.players AS players_count, t.source::text AS source,
               s.rank AS standing_rank
        FROM bs_decks d
        JOIN bs_tournaments t ON t.id = d.tournament_id
        LEFT JOIN bs_standings s ON s.tournament_id = t.id AND s.player = d.player
        WHERE t.format = :format AND t.date BETWEEN :date_from AND :date_to
        {exists}
        ORDER BY d.date DESC, d.id
    """  # noqa: S608
    params: dict[str, object] = {
        "format": FORMAT,
        "date_from": date_from,
        "date_to": date_to,
        "n_cmd": len(commanders),
    }
    params.update({f"cmd{i}": c for i, c in enumerate(commanders)})
    df = db.q(sql, params)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df.drop_duplicates("deck_id").reset_index(drop=True)


def load_cards(db: DB, deck_ids: list[str]) -> pd.DataFrame:
    return db.q(
        """
        SELECT dc.deck_id::text AS deck_id, dc.board::text AS board,
               dc.card_name, dc.count, mc.type_line, mc.mana_value,
               mc.mana_cost, mc.color_identity, mc.rarity, mc.text
        FROM bs_deck_cards dc
        LEFT JOIN LATERAL (
            SELECT c.type_line, c.mana_value, c.mana_cost, c.color_identity,
                   c.rarity, c.text
            FROM mj_cards c WHERE c.name = dc.card_name ORDER BY c.id LIMIT 1
        ) mc ON TRUE
        WHERE dc.deck_id = ANY(CAST(:ids AS uuid[]))
        """,
        {"ids": deck_ids},
    )


def load_banned(db: DB) -> tuple[set[str], str | None]:
    try:
        has_col = db.q(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'mj_cards' AND column_name = 'legalities'"
        )
        if has_col.empty:
            return set(), "mj_cards.legalities absent de cette base"
        df = db.q(
            "SELECT DISTINCT name FROM mj_cards "
            "WHERE lower(legalities->>'duel') = 'banned'"
        )
        return set(df["name"].str.lower()), None
    except Exception as exc:
        return set(), f"banlist illisible ({type(exc).__name__})"


def load_recent_candidates(db: DB, since: dt.date) -> tuple[pd.DataFrame, str | None]:
    try:
        df = db.q(
            """
            WITH first_print AS (
                SELECT c.name, MIN(s.release_date) AS first_release
                FROM mj_cards c JOIN mj_sets s ON s.code = c.set_code
                GROUP BY c.name
            )
            SELECT DISTINCT ON (c.name) c.name AS card_name, s.name AS set_name,
                   fp.first_release, c.type_line, c.mana_value, c.color_identity,
                   c.rarity, c.text
            FROM mj_cards c
            JOIN mj_sets s ON s.code = c.set_code
            JOIN first_print fp ON fp.name = c.name
            WHERE fp.first_release >= :since
              AND s.type IN ('expansion', 'core', 'draft_innovation',
                             'masters', 'commander')
              AND (c.side IS NULL OR c.side = 'a')
            ORDER BY c.name, s.release_date
            """,
            {"since": since},
        )
        df = df[pd.to_datetime(df["first_release"]).dt.date >= since]
        return df, None
    except Exception as exc:
        return pd.DataFrame(), f"cartes récentes indisponibles ({type(exc).__name__})"


# ─── Pure analysis helpers ────────────────────────────────────────────────────


def top8_flag(row: pd.Series) -> bool | None:
    """Top 8 when known: bs_standings rank first, else MTGTop8's
    '1'/'3-4'/'5-8' result string. MTGO decks without standings -> unknown.
    """
    if pd.notna(row.get("standing_rank")):
        return int(row["standing_rank"]) <= 8
    if row.get("source") == "mtgtop8" and isinstance(row.get("result"), str):
        m = re.fullmatch(r"\s*(\d+)(?:\s*-\s*(\d+))?\s*", row["result"])
        if m:
            return int(m.group(2) or m.group(1)) <= 8
    return None


def primary_type(type_line: object) -> str:
    if not isinstance(type_line, str):
        return "Inconnu"
    front = type_line.split("//")[0]
    for t in PRIMARY_TYPES:
        if t in front:
            return t
    return "Autre"


def functions_of(card_text: object) -> list[str]:
    if not isinstance(card_text, str):
        return []
    return [
        fn
        for fn, pats in FUNCTION_PATTERNS.items()
        if any(p.search(card_text) for p in pats)
    ]


def ci_list(ci: object) -> list[str]:
    if ci is None or (isinstance(ci, float) and np.isnan(ci)):
        return []
    if isinstance(ci, str):
        return [c for c in ci if c in "WUBRG"]
    if isinstance(ci, list | tuple | np.ndarray):
        return [str(c) for c in ci]
    return []


def parse_moxfield(path: Path) -> tuple[dict[str, int], dict[str, int]]:
    main: dict[str, int] = {}
    side: dict[str, int] = {}
    in_side = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower().strip("/ :")
        if low in {"sideboard", "commander", "commanders"}:
            in_side = True
            continue
        if line.startswith("//"):
            in_side = "side" in low or "command" in low
            continue
        m = re.match(r"^(\d+)x?\s+(.+?)(\s+\([A-Z0-9]+\)\s*\S*)?$", line)
        count, card = (int(m.group(1)), m.group(2).strip()) if m else (1, line)
        target = side if in_side else main
        target[card] = target.get(card, 0) + count
    return main, side


def md_table(df: pd.DataFrame, fmt: dict[str, str] | None = None) -> str:
    if df.empty:
        return "Aucune donnée."
    fmt = fmt or {}
    cols = list(df.columns)
    # Compact pipe style ("| a | b |", "| --- | --- |") -- docs' MD060 config.
    out = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in df.iterrows():
        cells = []
        for c in cols:
            v = row[c]
            if c in fmt and pd.notna(v):
                cells.append(format(v, fmt[c]))
            elif isinstance(v, float) and pd.isna(v):
                cells.append("—")
            elif isinstance(v, float) and v.is_integer():
                cells.append(str(int(v)))
            else:
                cells.append(str(v).replace("|", "/"))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def wrap_md(block: str) -> str:
    """Wraps one Markdown block at MD013's 80 columns.

    Headings and tables are left as-is (docs' config exempts tables from
    MD013); list items and blockquotes keep their marker/indentation.
    """
    block = block.strip("\n")
    if block.startswith(("|", "#")):
        return block
    if block.startswith("> "):
        return textwrap.fill(
            block[2:],
            MD_WRAP,
            initial_indent="> ",
            subsequent_indent="> ",
            break_long_words=False,
            break_on_hyphens=False,
        )
    if block.startswith("- "):
        return "\n".join(
            textwrap.fill(
                item[2:],
                MD_WRAP,
                initial_indent="- ",
                subsequent_indent="  ",
                break_long_words=False,
                break_on_hyphens=False,
            )
            for item in block.split("\n")
        )
    return textwrap.fill(block, MD_WRAP, break_long_words=False, break_on_hyphens=False)


def run_markdownlint(report: Path) -> str:
    """Runs markdownlint-cli2 --fix on the generated report, with the docs
    site's config (the same one CI applies to docs/content), and summarises
    whatever --fix could not repair. Never fails the generation: a missing
    Node.js/npx or a network error only yields a warning line.
    """
    npx = shutil.which("npx")
    if npx is None:
        return "markdownlint ignoré : npx introuvable (Node.js requis)."
    cmd = [npx, "--yes", "markdownlint-cli2", "--fix", report.name]
    if MARKDOWNLINT_CONFIG.is_file():
        cmd += ["--config", str(MARKDOWNLINT_CONFIG)]
    # S603: fixed argument list, executable resolved by shutil.which, no shell.
    result = subprocess.run(  # noqa: S603
        cmd,
        cwd=report.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0:
        return "markdownlint : OK"
    output = (result.stdout + result.stderr).splitlines()
    issues = [line for line in output if line.startswith(f"{report.name}:")]
    if not issues:
        return "markdownlint n'a pas pu tourner :\n" + "\n".join(output[-5:])
    return (
        f"markdownlint : {len(issues)} problème(s) restant(s) après --fix\n"
        + "\n".join(issues[:20])
    )


PDF_CSS = """
@page { size: A4; margin: 14mm 12mm; }
body { font: 10pt/1.4 "Segoe UI", Arial, sans-serif; color: #1a1a1a; }
h1 { font-size: 18pt; border-bottom: 2px solid #333; padding-bottom: 4px; }
h2 { font-size: 14pt; margin-top: 18px; border-bottom: 1px solid #bbb;
     break-after: avoid; }
h3 { font-size: 11pt; margin-top: 12px; break-after: avoid; }
table { border-collapse: collapse; width: 100%; font-size: 8.5pt;
        margin: 6px 0 10px; }
th, td { border: 1px solid #ccc; padding: 2px 5px; text-align: left; }
th { background: #eee; }
tr { break-inside: avoid; }
tr:nth-child(even) td { background: #fafafa; }
blockquote { margin: 6px 0; padding: 4px 10px; border-left: 3px solid #d9822b;
             background: #fdf3e7; }
code { font-family: Consolas, monospace; font-size: 9pt; }
"""


def _md_inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<em>\1</em>", s)


def md_to_html(markdown: str, title: str) -> str:
    """Converts the Markdown subset this script emits (headings, paragraphs,
    "- " lists, "> " quotes, pipe tables, `code`/**bold**/_italic_) to a
    standalone HTML page. Deliberately not a general Markdown parser --
    avoids adding a dependency for a report whose shape this file controls.
    """
    out: list[str] = []
    for block in re.split(r"\n\s*\n", markdown.strip()):
        lines = block.split("\n")
        first = lines[0]
        if m := re.match(r"^(#{1,6}) (.*)$", first):
            level = len(m.group(1))
            out.append(f"<h{level}>{_md_inline(m.group(2))}</h{level}>")
        elif first.startswith("|"):
            rows = [
                [c.strip() for c in line.strip().strip("|").split("|")]
                for line in lines
                if not re.fullmatch(r"\|[\s\-:|]+\|", line.strip())
            ]
            head = "".join(f"<th>{_md_inline(c)}</th>" for c in rows[0])
            body = "".join(
                "<tr>" + "".join(f"<td>{_md_inline(c)}</td>" for c in r) + "</tr>"
                for r in rows[1:]
            )
            out.append(
                f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
            )
        elif first.startswith("- "):
            items: list[str] = []
            for line in lines:
                if line.startswith("- "):
                    items.append(line[2:])
                elif items:
                    items[-1] += " " + line.strip()
            out.append(
                "<ul>" + "".join(f"<li>{_md_inline(i)}</li>" for i in items) + "</ul>"
            )
        elif first.startswith(">"):
            text_ = " ".join(line.lstrip(">").strip() for line in lines)
            out.append(f"<blockquote>{_md_inline(text_)}</blockquote>")
        else:
            out.append(f"<p>{_md_inline(' '.join(lines))}</p>")
    return (
        '<!doctype html>\n<html lang="fr"><head><meta charset="utf-8">'
        f"<title>{html.escape(title)}</title><style>{PDF_CSS}</style></head>"
        f"<body>{''.join(out)}</body></html>\n"
    )


def find_browser() -> str | None:
    """Chrome/Edge/Chromium executable: CHROME_PATH first, then PATH, then
    the usual Windows install locations.
    """
    if (env := os.environ.get("CHROME_PATH")) and Path(env).is_file():
        return env
    for name in ("chrome", "google-chrome", "chromium", "chromium-browser", "msedge"):
        if found := shutil.which(name):
            return found
    for base in (
        os.environ.get("PROGRAMFILES"),
        os.environ.get("PROGRAMFILES(X86)"),
        os.environ.get("LOCALAPPDATA"),
    ):
        if not base:
            continue
        for rel in (
            "Google/Chrome/Application/chrome.exe",
            "Microsoft/Edge/Application/msedge.exe",
        ):
            if (candidate := Path(base) / rel).is_file():
                return str(candidate)
    return None


def export_pdf(report: Path, title: str) -> str:
    """report.md -> report.html (kept, printable) -> report.pdf via headless
    Chrome/Edge. Never fails the generation: a missing browser or a print
    error only yields a warning line.
    """
    page = report.with_suffix(".html")
    page.write_text(
        md_to_html(report.read_text(encoding="utf-8"), title), encoding="utf-8"
    )
    browser = find_browser()
    if browser is None:
        return f"PDF ignoré : Chrome/Edge introuvable (CHROME_PATH). HTML : {page.name}"
    pdf = report.with_suffix(".pdf")
    # A throwaway profile, so an already-open Chrome window can't swallow the
    # headless run (it would otherwise hand off to it and print nothing).
    with tempfile.TemporaryDirectory() as profile:
        cmd = [
            browser,
            "--headless",
            "--disable-gpu",
            "--no-first-run",
            f"--user-data-dir={profile}",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf}",
            page.resolve().as_uri(),
        ]
        try:
            # S603: fixed argument list, executable resolved locally, no shell.
            subprocess.run(  # noqa: S603
                cmd, capture_output=True, timeout=120, check=False
            )
        except subprocess.TimeoutExpired:
            return f"PDF échoué : Chrome n'a pas répondu en 120 s. HTML : {page.name}"
    if not pdf.is_file() or pdf.stat().st_size == 0:
        return f"PDF échoué (aucun fichier produit). HTML : {page.name}"
    return f"PDF : {pdf.name}"


def moxfield(main: dict[str, int], side: dict[str, int]) -> str:
    lines = [f"{n} {c}" for c, n in sorted(main.items())]
    if side:
        lines += ["", "// Commander"] + [f"{n} {c}" for c, n in sorted(side.items())]
    return "\n".join(lines) + "\n"


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ─── Report ───────────────────────────────────────────────────────────────────


class CommanderReport:
    def __init__(
        self,
        args: argparse.Namespace,
        decks: pd.DataFrame,
        cards: pd.DataFrame,
        banned: set[str],
        banned_note: str | None,
        recent: pd.DataFrame,
        recent_note: str | None,
    ) -> None:
        self.a = args
        self.decks = decks.copy()
        self.cards = cards.copy()
        self.banned = banned
        self.notes = [n for n in (banned_note, recent_note) if n]
        self.recent = recent
        self.md: list[str] = []

    # ── analysis ──
    def analyse(self) -> None:
        d, c = self.decks, self.cards
        d["top8"] = d.apply(top8_flag, axis=1)
        d["period"] = d["date"].apply(
            lambda x: "{} → {}".format(*banlist_period_containing(x))
        )
        recent_cut = self.a.date_to - dt.timedelta(days=self.a.recent_days)
        d["is_recent"] = d["date"] > recent_cut

        self.main = c[c["board"] == "mainboard"].copy()
        self.side = c[c["board"] == "sideboard"].copy()
        self.n = d["deck_id"].nunique()

        zones = self.side.groupby("deck_id")["card_name"].apply(
            lambda s: " + ".join(sorted(s))
        )
        d["command_zone"] = d["deck_id"].map(zones).fillna("?")

        # Card metadata, one row per name
        meta = c.drop_duplicates("card_name").set_index("card_name")[
            ["type_line", "mana_value", "mana_cost", "color_identity", "rarity", "text"]
        ]
        meta["type"] = meta["type_line"].apply(primary_type)
        meta["functions"] = meta["text"].apply(functions_of)
        self.meta = meta

        top8_ids = set(d.loc[d["top8"] == True, "deck_id"])
        recent_ids = set(d.loc[d["is_recent"], "deck_id"])
        old_ids = set(d["deck_id"]) - recent_ids
        self.top8_ids, self.recent_ids, self.old_ids = top8_ids, recent_ids, old_ids

        g = self.main.groupby("card_name")
        stats = pd.DataFrame(
            {"decks": g["deck_id"].nunique(), "avg_copies": g["count"].mean()}
        )
        stats["play_rate"] = stats["decks"] / self.n

        def rate(ids: set[str]) -> pd.Series:
            if not ids:
                return pd.Series(np.nan, index=stats.index)
            sub = (
                self.main[self.main["deck_id"].isin(ids)]
                .groupby("card_name")["deck_id"]
                .nunique()
            )
            return (sub / len(ids)).reindex(stats.index).fillna(0.0)

        stats["top8_rate"] = (
            rate(top8_ids) if len(top8_ids) >= self.a.min_top8 else np.nan
        )
        stats["recent_rate"] = rate(recent_ids) if recent_ids else np.nan
        stats["older_rate"] = rate(old_ids) if old_ids else np.nan
        stats["trend"] = stats["recent_rate"] - stats["older_rate"]
        stats["type"] = meta["type"].reindex(stats.index)
        stats["mv"] = meta["mana_value"].reindex(stats.index)
        stats["banned"] = [n.lower() in self.banned for n in stats.index]
        stats["tier"] = np.select(
            [
                stats["play_rate"] >= self.a.core,
                stats["play_rate"] >= self.a.fringe,
                stats["decks"] >= 2,
            ],
            ["core", "flex", "tech"],
            default="rare",
        )
        self.stats = stats.sort_values(["play_rate", "decks"], ascending=False)

        # Per-deck structure (lands, curve, functions)
        mm = self.main.merge(
            meta[["type", "functions"]],
            left_on="card_name",
            right_index=True,
            how="left",
        )
        self.mm = mm
        per_deck = []
        for deck_id, grp in mm.groupby("deck_id"):
            row = {
                "deck_id": deck_id,
                "cards": grp["count"].sum(),
                "lands": grp.loc[grp["type"] == "Land", "count"].sum(),
            }
            nonland = grp[grp["type"] != "Land"]
            w = nonland["count"]
            row["avg_mv"] = (
                float((nonland["mana_value"].fillna(0) * w).sum() / w.sum())
                if w.sum()
                else np.nan
            )
            for fn in FUNCTION_PATTERNS:
                row[fn] = int(
                    grp.loc[
                        grp["functions"].apply(
                            lambda f, fn=fn: isinstance(f, list) and fn in f
                        ),
                        "count",
                    ].sum()
                )
            per_deck.append(row)
        self.per_deck = pd.DataFrame(per_deck)

        # Commander colour identity (for recent-card candidates): the most
        # frequent command zone's cards.
        ci: set[str] = set()
        top_zone = d["command_zone"].mode()
        for name in top_zone.iloc[0].split(" + ") if len(top_zone) else []:
            ci |= set(ci_list(meta["color_identity"].get(name)))
        self.color_identity = ci

    def aggregate(
        self, deck_ids: list[str]
    ) -> tuple[dict[str, int], dict[str, int]] | None:
        ordered = self.decks[self.decks["deck_id"].isin(deck_ids)].sort_values(
            "date", ascending=False
        )["deck_id"]
        decklists = []
        for did in ordered:
            grp = self.cards[self.cards["deck_id"] == did]
            decklists.append(
                Decklist(
                    mainboard=grp[grp["board"] == "mainboard"]
                    .groupby("card_name")["count"]
                    .sum()
                    .astype(int)
                    .to_dict(),
                    sideboard=grp[grp["board"] == "sideboard"]
                    .groupby("card_name")["count"]
                    .sum()
                    .astype(int)
                    .to_dict(),
                )
            )
        agg = aggregate_decks(decklists, order=self.a.order, limit=self.a.limit)
        if agg is None:
            return None
        main = {
            k: int(v)
            for k, v in agg.decklist.mainboard.items()
            if k.lower() not in self.banned
        }
        side = {k: int(v) for k, v in agg.decklist.sideboard.items()}
        return self.normalise(main, side)

    def normalise(
        self, main: dict[str, int], side: dict[str, int]
    ) -> tuple[dict[str, int], dict[str, int]]:
        """Bring main + command zone to exactly 100 cards using overall play rates."""
        pr = self.stats["play_rate"].to_dict()
        target = 100 - sum(side.values())
        main = dict(main)
        self.norm_removed, self.norm_added = [], []
        for card in sorted(main, key=lambda x: pr.get(x, 0.0)):
            if sum(main.values()) <= target:
                break
            main[card] -= 1
            if main[card] == 0:
                del main[card]
            self.norm_removed.append(card)
        if sum(main.values()) < target:
            for card in self.stats.index:
                if sum(main.values()) >= target:
                    break
                if card not in main and not self.stats.loc[card, "banned"]:
                    main[card] = 1
                    self.norm_added.append(card)
        return main, side

    def cluster(self) -> None:
        self.labels = None
        if self.n < max(12, self.a.k_min * 4):
            self.cluster_note = (
                f"Trop peu de decks ({self.n}) pour chercher des variantes."
            )
            return
        from sklearn.cluster import KMeans
        from sklearn.decomposition import PCA
        from sklearn.feature_extraction.text import TfidfTransformer
        from sklearn.metrics import silhouette_score

        pivot = (
            self.main.groupby(["deck_id", "card_name"])["count"]
            .sum()
            .unstack(fill_value=0)
        )
        self.tfidf = TfidfTransformer().fit(pivot.values)
        X = self.tfidf.transform(pivot.values).toarray()
        n_comp = min(20, X.shape[0] - 1, X.shape[1])
        self.pca = PCA(n_components=n_comp, random_state=42).fit(X)
        Xp = self.pca.transform(X)
        best = None
        for k in range(self.a.k_min, min(self.a.k_max, len(pivot) - 1) + 1):
            km = KMeans(n_clusters=k, n_init="auto", random_state=42).fit(Xp)
            s = silhouette_score(Xp, km.labels_)
            if best is None or s > best[0]:
                best = (s, k, km)
        if best is None:
            self.cluster_note = "Clustering impossible."
            return
        self.silhouette, self.k, self.km = best
        self.pivot_cols = list(pivot.columns)
        self.labels = pd.Series(self.km.labels_, index=pivot.index)
        self.cluster_note = f"{self.k} variantes, silhouette {self.silhouette:.2f}" + (
            " — variantes peu distinctes, à lire avec prudence."
            if self.silhouette < 0.1
            else "."
        )

    def nearest_variant(self, main: dict[str, int]) -> int | None:
        if self.labels is None:
            return None
        vec = np.array([[main.get(c, 0) for c in self.pivot_cols]], dtype=float)
        xp = self.pca.transform(self.tfidf.transform(vec).toarray())
        return int(np.argmin(np.linalg.norm(self.km.cluster_centers_ - xp, axis=1)))

    # ── rendering ──
    def h(self, level: int, t: str) -> None:
        self.md.append(f"{'#' * level} {t}")

    def p(self, t: str) -> None:
        # Consecutive "- " items form one tight list instead of separate blocks.
        if t.startswith("- ") and self.md and self.md[-1].startswith("- "):
            self.md[-1] += "\n" + t
        else:
            self.md.append(t)

    def deck_profile(self, main: dict[str, int]) -> pd.DataFrame:
        """Structure of one list vs. the average deck of this commander."""
        rows = []
        lands = sum(n for c, n in main.items() if self.meta["type"].get(c) == "Land")
        nonland = {c: n for c, n in main.items() if self.meta["type"].get(c) != "Land"}

        def mvf(c: str) -> float:
            v = self.meta["mana_value"].get(c)
            return 0.0 if v is None or pd.isna(v) else float(v)

        mv = sum(mvf(c) * n for c, n in nonland.items()) / max(1, sum(nonland.values()))
        rows.append(("Terrains", lands, self.per_deck["lands"].mean()))
        rows.append(
            ("CMC moyen (hors terrains)", round(mv, 2), self.per_deck["avg_mv"].mean())
        )
        for fn in FUNCTION_PATTERNS:
            mine = sum(
                n
                for c, n in main.items()
                if fn in (self.meta["functions"].get(c) or [])
            )
            rows.append((fn, mine, self.per_deck[fn].mean()))
        df = pd.DataFrame(
            rows, columns=["Indicateur", "Cette liste", "Moyenne des decks"]
        )
        df["Moyenne des decks"] = df["Moyenne des decks"].round(1)
        return df

    def card_table(
        self, names: list[str], counts: dict[str, int] | None = None
    ) -> pd.DataFrame:
        s = self.stats.reindex(names)
        df = pd.DataFrame(
            {
                "Carte": names,
                "Qté": [counts.get(n, "") for n in names]
                if counts
                else [""] * len(names),
                "Type": s["type"].fillna("?").values,
                "MV": s["mv"].values,
                "Play rate": s["play_rate"].fillna(0).values,
                "Top 8": s["top8_rate"].values,
                "Tendance": s["trend"].values,
                "Tier": s["tier"].fillna("absent").values,
            }
        )
        if not counts:
            df = df.drop(columns="Qté")
        return df

    def render(self, out_dir: Path) -> Path:
        a, d = self.a, self.decks
        pct = {"Play rate": ".0%", "Top 8": ".0%", "Tendance": "+.0%", "MV": ".0f"}
        title = " + ".join(a.commander)
        self.h(1, f"{title} — rapport d'agrégation Duel Commander")
        self.p(
            f"Généré le {dt.date.today()} · fenêtre {a.date_from} → {a.date_to}"
            f" · ordre d'agrégation {a.order} · seuils core ≥ {a.core:.0%},"
            f" flex ≥ {a.fringe:.0%}."
        )
        for n in self.notes:
            self.p(f"> ⚠ {n}")

        # Overview
        self.h(2, "Vue d'ensemble")
        top8_known = d["top8"].notna().sum()
        self.p(
            f"- **{self.n} decks** sur **{d['tournament_id'].nunique()} tournois**, "
            f"{d['player'].nunique()} joueurs distincts"
        )
        self.p(
            "- Sources : "
            + ", ".join(f"{k} ({v})" for k, v in d["source"].value_counts().items())
        )
        top8_count = int((d["top8"] == True).sum())
        self.p(f"- Top 8 connu pour {top8_known} decks, dont {top8_count} en top 8")
        self.p(
            f"- Récents (≤ {a.recent_days} j) : {len(self.recent_ids)} decks"
            " — base de la colonne « Tendance »"
        )
        zones = d["command_zone"].value_counts()
        if len(zones) > 1:
            self.h(3, "Zones de commandement")
            self.p(
                md_table(
                    pd.DataFrame(
                        {
                            "Commandant(s)": zones.index,
                            "Decks": zones.values,
                            "Part": zones.values / self.n,
                        }
                    ),
                    {"Part": ".0%"},
                )
            )
        per = (
            d.groupby("period")
            .agg(
                Decks=("deck_id", "nunique"),
                Top8=("top8", lambda s: int((s == True).sum())),
            )
            .reset_index()
        )
        self.h(3, "Par période de banlist")
        self.p(md_table(per.rename(columns={"period": "Période"})))

        # Aggregated list
        agg = self.aggregate(list(d["deck_id"]))
        if agg:
            main, side = agg
            (out_dir / "aggregated.txt").write_text(
                moxfield(main, side), encoding="utf-8"
            )
            total = sum(main.values()) + sum(side.values())
            self.h(2, f"Liste agrégée ({total} cartes) — `aggregated.txt`")
            self.p(
                f"Agrégation des {min(self.n, a.limit)} decks les plus récents. "
                "La colonne Tier situe chaque carte dans le méta du commandant."
            )
            if self.norm_removed or self.norm_added:
                self.p(
                    f"Normalisation à 100 : retirées {self.norm_removed or '—'},"
                    f" ajoutées {self.norm_added or '—'}."
                )
            self.h(3, "Structure")
            self.p(md_table(self.deck_profile(main)))
            by_type: dict[str, list[str]] = {}
            for card in main:
                by_type.setdefault(self.meta["type"].get(card, "Inconnu"), []).append(
                    card
                )
            for t in [*PRIMARY_TYPES, "Autre", "Inconnu"]:
                if t in by_type:
                    names = sorted(
                        by_type[t],
                        key=lambda c: (-self.stats["play_rate"].get(c, 0), c),
                    )
                    self.h(3, f"{t} ({sum(main[c] for c in names)})")
                    self.p(md_table(self.card_table(names, main), pct))
            if side:
                self.p("**Commandant(s)** : " + ", ".join(side))
            borderline = [
                c for c in main if self.stats["tier"].get(c) in ("tech", "rare")
            ]
            if borderline:
                self.h(3, "Points faibles de la liste agrégée")
                self.p(
                    "Cartes retenues mais peu jouées (< seuil flex) :"
                    " les premières à remettre en question."
                )
                self.p(
                    md_table(
                        self.card_table(
                            sorted(
                                borderline,
                                key=lambda c: self.stats["play_rate"].get(c, 0),
                            )
                        ),
                        pct,
                    )
                )
            left_out = [
                c
                for c in self.stats.index
                if c not in main
                and self.stats.loc[c, "play_rate"] >= a.fringe
                and not self.stats.loc[c, "banned"]
            ]
            if left_out:
                self.h(3, "Laissées de côté malgré un play rate ≥ flex")
                self.p(md_table(self.card_table(left_out[:25]), pct))
        else:
            main = {}

        # Core / flex / risers
        self.h(2, "Méta du commandant")
        core = self.stats[self.stats["tier"] == "core"]
        self.h(3, f"Squelette core ({len(core)} cartes ≥ {a.core:.0%})")
        self.p(", ".join(core.index) or "_aucune_")
        flex = self.stats[self.stats["tier"] == "flex"]
        self.h(3, f"Slots flex ({len(flex)} cartes)")
        self.p(md_table(self.card_table(list(flex.index)), pct))
        if self.stats["trend"].notna().any():
            movers = self.stats[self.stats["decks"] >= 2].dropna(subset=["trend"])
            self.h(3, f"En hausse (≤ {a.recent_days} j vs avant)")
            self.p(
                md_table(
                    self.card_table(
                        list(
                            movers.sort_values("trend", ascending=False).head(15).index
                        )
                    ),
                    pct,
                )
            )
            self.h(3, "En baisse")
            self.p(
                md_table(
                    self.card_table(list(movers.sort_values("trend").head(15).index)),
                    pct,
                )
            )
        if self.stats["top8_rate"].notna().any():
            perf = self.stats[(self.stats["decks"] >= 3)].copy()
            perf["delta"] = perf["top8_rate"] - perf["play_rate"]
            self.h(3, "Sur-représentées en top 8")
            self.p(
                "Écart top 8 - play rate global (≥ 3 decks)."
                " Signal faible sur petits échantillons."
            )
            self.p(
                md_table(
                    self.card_table(
                        list(perf.sort_values("delta", ascending=False).head(15).index)
                    ),
                    pct,
                )
            )

        # Variants
        self.cluster()
        self.h(2, "Variantes")
        self.p(self.cluster_note)
        if self.labels is not None:
            overall = self.stats["play_rate"]
            for k in range(self.k):
                ids = list(self.labels[self.labels == k].index)
                sub = self.main[self.main["deck_id"].isin(ids)].groupby("card_name")[
                    "deck_id"
                ].nunique() / len(ids)
                sig = (sub - overall.reindex(sub.index)).sort_values(ascending=False)
                sig = sig[sub.reindex(sig.index) >= 0.5].head(12)
                t8 = d[d["deck_id"].isin(ids)]["top8"]
                t8_hits, t8_known = int((t8 == True).sum()), int(t8.notna().sum())
                self.h(
                    3,
                    f"Variante {k} — {len(ids)} decks ({len(ids) / self.n:.0%}),"
                    f" top 8 : {t8_hits}/{t8_known}",
                )
                self.p(
                    "Cartes signature : "
                    + ", ".join(f"{c} ({sub[c]:.0%})" for c in sig.index)
                )
                vagg = self.aggregate(ids)
                if vagg:
                    (out_dir / f"variant_{k}.txt").write_text(
                        moxfield(*vagg), encoding="utf-8"
                    )
                    self.p(f"Liste agrégée : `variant_{k}.txt`")

        # Personal deck
        if a.deck:
            mine, mine_side = parse_moxfield(Path(a.deck))
            mine_total = sum(mine.values()) + sum(mine_side.values())
            self.h(2, f"Ton deck — `{Path(a.deck).name}` ({mine_total} cartes)")
            nv = self.nearest_variant(mine)
            if nv is not None:
                self.p(f"Variante la plus proche : **{nv}**")
            if main:
                common = sum(min(n, main.get(c, 0)) for c, n in mine.items())
                self.p(
                    "Recouvrement avec la liste agrégée :"
                    f" {common}/{sum(main.values())} cartes"
                )
            banned_in = [c for c in mine if c.lower() in self.banned]
            if banned_in:
                self.p(f"> ⚠ Bannies en Duel Commander : {', '.join(banned_in)}")
            unknown = [c for c in mine if c not in self.meta.index]
            self.h(3, "Structure")
            self.p(md_table(self.deck_profile(mine)))
            cuts = sorted(
                [
                    c
                    for c in mine
                    if (
                        self.stats["play_rate"].get(c, 0) < a.fringe
                        and self.meta["type"].get(c) != "Land"
                    )
                    or c not in self.stats.index
                ],
                key=lambda c: self.stats["play_rate"].get(c, 0),
            )
            self.h(
                3, f"Candidates au retrait ({len(cuts)}) — play rate < {a.fringe:.0%}"
            )
            self.p(md_table(self.card_table(cuts, mine), pct))
            adds = [
                c
                for c in self.stats.index
                if c not in mine
                and self.stats.loc[c, "play_rate"] >= a.fringe
                and not self.stats.loc[c, "banned"]
            ]
            self.h(
                3,
                f"Candidates à l'ajout ({len(adds)}) — play rate ≥ {a.fringe:.0%},"
                " absentes de ton deck",
            )
            self.p(md_table(self.card_table(adds), pct))
            if unknown:
                self.p(
                    "_Jamais jouées par ce commandant dans la fenêtre_ : "
                    + ", ".join(unknown)
                )

        # Studied cards
        if a.study:
            self.h(2, "Cartes étudiées")
            rows = []
            for name in a.study:
                hit = self.stats.index[self.stats.index.str.lower() == name.lower()]
                if len(hit):
                    rows.append(hit[0])
                else:
                    self.p(
                        f"- **{name}** : jamais jouée par ce commandant sur la fenêtre."
                    )
            if rows:
                df = self.card_table(rows)
                df["Decks"] = self.stats.loc[rows, "decks"].values
                df["Copies moy."] = self.stats.loc[rows, "avg_copies"].round(2).values
                if self.labels is not None:
                    for k in range(self.k):
                        ids = set(self.labels[self.labels == k].index)
                        played = (
                            self.main[self.main["deck_id"].isin(ids)]
                            .groupby("card_name")["deck_id"]
                            .nunique()
                        )
                        df[f"V{k}"] = [played.get(r, 0) / len(ids) for r in rows]
                        pct[f"V{k}"] = ".0%"
                self.p(md_table(df, pct))

        # Recent printings
        if not self.recent.empty:
            played = set(self.stats.index.str.lower())
            ci = self.color_identity
            cand = self.recent[
                self.recent["color_identity"].apply(lambda x: set(ci_list(x)) <= ci)
                & ~self.recent["card_name"].str.lower().isin(played)
                & ~self.recent["card_name"].str.lower().isin(self.banned)
                & ~self.recent["type_line"].fillna("").str.contains("Basic Land")
            ].copy()
            if not cand.empty and not self.per_deck.empty:
                profile = np.array(
                    [self.per_deck[fn].mean() for fn in FUNCTION_PATTERNS]
                )
                cand["fn"] = cand["text"].apply(functions_of)
                cand["score"] = cand["fn"].apply(
                    lambda f: float(
                        sum(
                            profile[i]
                            for i, fn in enumerate(FUNCTION_PATTERNS)
                            if fn in f
                        )
                    )
                )
                rank = {"mythic": 0, "rare": 1, "uncommon": 2, "common": 3}
                cand["r"] = cand["rarity"].str.lower().map(rank).fillna(4)
                cand = cand.sort_values(["score", "r"], ascending=[False, True]).head(
                    25
                )
                identity = "".join(sorted(ci)) or "?"
                self.h(
                    2,
                    f"Cartes récentes jamais jouées ici (≤ {a.days_sets} j,"
                    f" identité {identity})",
                )
                self.p(
                    "Triées par adéquation avec les fonctions que ce commandant"
                    " joue le plus. Piste de réflexion, pas une recommandation."
                )
                self.p(
                    md_table(
                        pd.DataFrame(
                            {
                                "Carte": cand["card_name"],
                                "Extension": cand["set_name"],
                                "Sortie": cand["first_release"],
                                "Type": cand["type_line"],
                                "Fonctions": cand["fn"].apply(", ".join),
                            }
                        )
                    )
                )

        # Decks list
        self.h(2, "Decks analysés")
        dl = d.sort_values("date", ascending=False)[
            [
                "date",
                "tournament_name",
                "players_count",
                "player",
                "result",
                "standing_rank",
                "command_zone",
            ]
        ]
        self.p(
            md_table(
                dl.rename(
                    columns={
                        "date": "Date",
                        "tournament_name": "Tournoi",
                        "players_count": "Joueurs",
                        "player": "Joueur",
                        "result": "Résultat",
                        "standing_rank": "Rang",
                        "command_zone": "Commandant(s)",
                    }
                )
            )
        )

        report = out_dir / "report.md"
        report.write_text(
            "\n\n".join(wrap_md(block) for block in self.md) + "\n", encoding="utf-8"
        )
        self.stats.rename_axis("card_name").to_csv(
            out_dir / "cards.csv", encoding="utf-8"
        )
        return report


# ─── CLI ──────────────────────────────────────────────────────────────────────


def build_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--commander",
        action="append",
        required=True,
        help="nom exact (ILIKE, %% accepté) ; répéter pour un duo partner",
    )
    p.add_argument(
        "--exact",
        action="store_true",
        help="la zone de commandement doit être exactement ces commandants",
    )
    p.add_argument("--days", type=int, default=365)
    p.add_argument("--date-from", type=dt.date.fromisoformat)
    p.add_argument("--date-to", type=dt.date.fromisoformat, default=dt.date.today())
    p.add_argument(
        "--recent-days",
        type=int,
        default=90,
        help="fenêtre « récente » pour la colonne Tendance",
    )
    p.add_argument(
        "--days-sets",
        type=int,
        default=180,
        help="ancienneté max des cartes récentes suggérées",
    )
    p.add_argument("--order", type=int, default=2)
    p.add_argument(
        "--limit",
        type=int,
        default=100,
        help="nb max de decks (les plus récents) agrégés",
    )
    p.add_argument("--core", type=float, default=0.85)
    p.add_argument("--fringe", type=float, default=0.30)
    p.add_argument(
        "--min-top8",
        type=int,
        default=5,
        help="nb min de decks top 8 pour afficher la colonne Top 8",
    )
    p.add_argument("--k-min", type=int, default=2)
    p.add_argument("--k-max", type=int, default=6)
    p.add_argument("--deck", help="export Moxfield de ton deck à comparer")
    p.add_argument("--study", nargs="+", help="cartes à étudier en détail")
    p.add_argument(
        "--out", help="dossier de sortie (défaut : scripts/outputs/<commandant>-<date>)"
    )
    p.add_argument(
        "--no-lint",
        action="store_true",
        help="ne pas passer markdownlint (--fix) sur report.md après génération",
    )
    p.add_argument(
        "--pdf",
        action="store_true",
        help="exporter aussi report.html + report.pdf (Chrome/Edge headless)",
    )
    a = p.parse_args(argv)
    a.date_from = a.date_from or a.date_to - dt.timedelta(days=a.days)
    return a


def main() -> None:
    load_dotenv(APP_ROOT / ".env")
    a = build_args()
    url = os.environ.get("REPORT_DATABASE_URL") or os.environ.get(
        "KARN_TABLETS_DATABASE_URL_RO"
    )
    if not url:
        sys.exit("REPORT_DATABASE_URL (ou KARN_TABLETS_DATABASE_URL_RO) non défini.")
    db = DB(url)
    print(f"> Base : {db.engine.url.host}/{db.engine.url.database}")

    decks = load_decks(db, a.commander, a.exact, a.date_from, a.date_to)
    if decks.empty:
        sys.exit(
            f"Aucun deck {FORMAT} pour {a.commander}"
            f" entre {a.date_from} et {a.date_to}."
        )
    print(f"> {len(decks)} decks, chargement des cartes…")
    cards = load_cards(db, list(decks["deck_id"]))
    banned, banned_note = load_banned(db)
    recent, recent_note = load_recent_candidates(
        db, a.date_to - dt.timedelta(days=a.days_sets)
    )

    slug = f"{slugify('-'.join(a.commander))}-{dt.date.today()}"
    out = Path(a.out) if a.out else DEFAULT_OUTPUT_ROOT / slug
    out.mkdir(parents=True, exist_ok=True)
    rep = CommanderReport(a, decks, cards, banned, banned_note, recent, recent_note)
    print("> Analyse…")
    rep.analyse()
    print("> Agrégation et rapport…")
    path = rep.render(out)
    if not a.no_lint:
        print("> markdownlint…")
        print(run_markdownlint(path))
    if a.pdf:
        print("> Export PDF…")
        print(export_pdf(path, " + ".join(a.commander)))
    print(f"OK Rapport : {path.resolve()}")
    print(f"  Fichiers : {', '.join(sorted(f.name for f in out.iterdir()))}")


if __name__ == "__main__":
    main()
