"""Synchronous, read-only data extraction from barrins_api's `bs_*`/`mj_cards`
tables (Karn Tablets holds a credential scoped to reads only -- T6, ADR-13).

Adapted from the prior attempt at this
(`barrins-archive/barrins_api/app/services/ml/extract.py`), which targeted
a `dl_*` schema that was later redesigned into `bs_*` (T2) and a bare
`cards` table later prefixed `mj_cards` (S8) -- table/column names below
match the schema actually shipped, not the archived code's.

Duel-Commander-only (`t.format = 'Duel Commander'`) throughout: Karn
Tablets' only two named consumers (Tolaria News, S6) both only ever want
this one format (T6, ADR-13) -- see `tolaria_news.md`'s own format check
in `barrins_api`'s `services/tolaria_news/decks.py` for the same literal.

`bs_deck_cards.card_name` is a raw string with no FK to `mj_cards` (T2) --
resolved here via a `LATERAL` join on an exact name match, picking an
arbitrary matching printing when several share a name (same accepted v1
concession `services/tolaria_news/decks.py` already makes for the public
BFF). Names with no match are dropped (logged), not carried through as a
featureless row -- a small, expected fraction (typos, un-imported
printings) shouldn't meaningfully skew an averaged feature vector.
"""

import datetime as dt
import logging
from functools import lru_cache

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from karn_tablets.config import database_url
from karn_tablets.schemas import Decklist

logger = logging.getLogger(__name__)

DUEL_COMMANDER_FORMAT = "Duel Commander"


@lru_cache(maxsize=1)
def _engine() -> Engine:
    url = database_url()
    if not url:
        raise RuntimeError(
            "KARN_TABLETS_DATABASE_URL_RO is not set -- Karn Tablets needs a "
            "read-only credential scoped to bs_*/mj_cards to extract anything."
        )
    return create_engine(url, pool_pre_ping=True)


def read_sql(query: str, params: dict[str, object] | None = None) -> pd.DataFrame:
    with _engine().connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params or {})


def load_deck_cards(date_from: dt.date, date_to: dt.date) -> pd.DataFrame:
    """Every `bs_deck_cards` row for Duel Commander decks in `[date_from, date_to]`.

    Columns: deck_id, card_uuid (mj_cards.id, may be unresolved -> dropped
    below), count, is_sideboard, tournament_id, date, players_count.
    """
    df = read_sql(
        """
        SELECT
            dc.deck_id::text AS deck_id,
            mc.card_uuid::text AS card_uuid,
            dc.count,
            (dc.board = 'sideboard') AS is_sideboard,
            d.tournament_id::text AS tournament_id,
            d.date,
            t.players AS players_count
        FROM bs_deck_cards dc
        JOIN bs_decks d ON d.id = dc.deck_id
        JOIN bs_tournaments t ON t.id = d.tournament_id
        LEFT JOIN LATERAL (
            SELECT c.id AS card_uuid
            FROM mj_cards c
            WHERE c.name = dc.card_name
            ORDER BY c.id
            LIMIT 1
        ) mc ON TRUE
        WHERE t.format = :format
          AND t.date BETWEEN :date_from AND :date_to
        """,
        {"format": DUEL_COMMANDER_FORMAT, "date_from": date_from, "date_to": date_to},
    )
    if df.empty:
        return df

    unresolved = int(df["card_uuid"].isna().sum())
    if unresolved:
        logger.debug(
            "dropping %d deck-card row(s) with no mj_cards match (%s..%s)",
            unresolved,
            date_from,
            date_to,
        )
    return df.dropna(subset=["card_uuid"]).reset_index(drop=True)


def load_cards_features() -> pd.DataFrame:
    """Intrinsic features of every non-token card printing.

    Includes `text`/`mana_cost` (functional classification, mana pips) and
    `type_line`/`types` (card-type detection).
    """
    return read_sql("""
        SELECT id::text AS uuid, name, mana_value, colors, color_identity,
               types, subtypes, supertypes, keywords,
               rarity, power, toughness, loyalty,
               text, mana_cost, type_line
        FROM mj_cards
    """)


def load_decklists_from_df(df_dc: pd.DataFrame) -> list[Decklist]:
    """Converts `load_deck_cards`'s output into a list of `Decklist`,
    ordered by `df_dc["deck_id"].unique()`.
    """
    result: list[Decklist] = []
    for deck_id in df_dc["deck_id"].unique():
        group = df_dc[df_dc["deck_id"] == deck_id]
        mainboard = dict(
            group[~group["is_sideboard"]].groupby("card_uuid")["count"].sum()
        )
        sideboard = dict(
            group[group["is_sideboard"]].groupby("card_uuid")["count"].sum()
        )
        result.append(Decklist(mainboard=mainboard, sideboard=sideboard))
    return result
