import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

from barrins_scripture import services


def build_parser() -> argparse.ArgumentParser:
    today = datetime.now().strftime("%Y-%m")
    five_days_ago = (datetime.now() - timedelta(days=5)).strftime("%Y-%m")

    parser = argparse.ArgumentParser(
        prog="barrins-scripture",
        description="CLI to scrape MTG tournament data from MTGO and MTGTop8",
    )
    parser.add_argument(
        "--source",
        choices=["mtgo", "mtgtop8"],
        default="mtgo",
        help="source to scrape (default: mtgo)",
    )
    parser.add_argument(
        "--date-from",
        default=five_days_ago,
        help="start month, format YYYY-MM (mtgo only, default: 5 days ago)",
    )
    parser.add_argument(
        "--date-to",
        default=today,
        help="end month, format YYYY-MM (mtgo only, default: today)",
    )
    parser.add_argument(
        "--span",
        type=int,
        default=1000,
        help="number of tournament ids to inspect (mtgtop8 only, default: 1000)",
    )
    parser.add_argument(
        "--id-from",
        type=int,
        default=None,
        help=(
            "starting tournament id to scrape from (mtgtop8 only; default: "
            "resume from the last archived id). Combine with --span to "
            "backfill an arbitrary id range, e.g. --id-from 1 --span 5000."
        ),
    )
    parser.add_argument(
        "--force-mtgo",
        action="store_true",
        help="force re-scraping of already-archived MTGO tournaments",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "directory the JSON archive is written under (creates "
            "<output-dir>/mtgo.com or /mtgtop8.com as needed) - lets the "
            "archive live wherever a deployment manages it (e.g. a plain "
            "clone, not necessarily a git submodule at a fixed path). "
            "Defaults to apps/barrins_scripture/scraped/ if not given."
        ),
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    parser = build_parser()
    args = parser.parse_args()

    if args.source == "mtgo":
        try:
            date_from = datetime.strptime(args.date_from, "%Y-%m")
            date_to = datetime.strptime(args.date_to, "%Y-%m")
        except ValueError:
            parser.error(
                "--date-from/--date-to must be in YYYY-MM format, e.g. 2026-06"
            )
        services.mtgo(date_from, date_to, args.force_mtgo, output_dir=args.output_dir)
    elif args.source == "mtgtop8":
        services.mtgtop8(args.span, output_dir=args.output_dir, id_from=args.id_from)


if __name__ == "__main__":
    main()
