"""CLI entry point (`karn-tablets`) -- the systemd-timer target (T8, ADR-13:
a scheduled job, no inbound API, mirrors `scripture_scraper`'s shape).

Runs one clustering pass per requested window kind and pushes each result
to `barrins_api`. Never raises past `main()` for a single window's
failure -- one bad window shouldn't block the others in the same tick.
"""

import argparse
import datetime as dt
import logging

from dc_calendar.windowing import WindowKind, resolve_windows
from dotenv import load_dotenv

from karn_tablets import config, pipeline, push
from karn_tablets.clustering import AlgorithmLiteral

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="karn-tablets",
        description=(
            "Cluster Duel Commander tournament decks into archetypes and "
            "push the result to barrins_api's POST /internal/karn/ingest."
        ),
    )
    parser.add_argument(
        "--window",
        choices=["rolling_30d", "banlist_period", "both"],
        default="both",
        help="which window mode(s) to run (default: both)",
    )
    parser.add_argument(
        "--date-to",
        default=None,
        help="reference date, format YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--algorithm",
        choices=["kmeans", "dbscan", "gmm"],
        default="kmeans",
        help="clustering algorithm (default: kmeans)",
    )
    parser.add_argument(
        "--api-url",
        default=config.barrins_api_url(),
        help="barrins_api base URL (env: BARRINS_API_URL)",
    )
    parser.add_argument(
        "--token",
        default=config.karn_ingest_token(),
        help="shared ingestion secret (env: KARN_INGEST_TOKEN)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run clustering but skip the push -- for local inspection",
    )
    return parser


def _window_kinds(choice: str) -> tuple[WindowKind, ...]:
    if choice == "both":
        return (WindowKind.rolling_30d, WindowKind.banlist_period)
    return (WindowKind(choice),)


def run(
    date_to: dt.date,
    window_choice: str,
    algorithm: AlgorithmLiteral,
    api_url: str | None,
    token: str | None,
    dry_run: bool,
) -> bool:
    """Runs every requested window; returns whether every push succeeded
    (always `True` in `--dry-run`, since nothing is pushed).
    """
    all_succeeded = True
    for window in resolve_windows(date_to, _window_kinds(window_choice)):
        logger.info("clustering window %s", window.label)
        result = pipeline.run(window, algorithm=algorithm)

        if dry_run:
            logger.info(
                "dry-run: window %s -> %d decks, %d archetypes (not pushed)",
                window.label,
                result.total_decks,
                len(result.archetypes),
            )
            continue

        if not api_url or not token:
            logger.error(
                "cannot push window %s: --api-url/--token not configured",
                window.label,
            )
            all_succeeded = False
            continue

        if not push.push(result, api_url, token):
            all_succeeded = False

    return all_succeeded


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    # Local dev only -- systemd sets real env vars in production, no .env there.
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args()

    if args.date_to:
        try:
            date_to = dt.date.fromisoformat(args.date_to)
        except ValueError:
            parser.error("--date-to must be in YYYY-MM-DD format, e.g. 2026-06-15")
    else:
        date_to = dt.date.today()

    if not config.database_url():
        parser.error(
            "KARN_TABLETS_DATABASE_URL_RO is not set -- Karn Tablets needs a "
            "read-only credential scoped to bs_*/mj_cards to run at all."
        )

    succeeded = run(
        date_to, args.window, args.algorithm, args.api_url, args.token, args.dry_run
    )
    if not succeeded:
        raise SystemExit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
