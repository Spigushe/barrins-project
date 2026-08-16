"""Orchestrates one clustering run: extract -> cluster -> aggregate ->
build the payload pushed to `barrins_api`'s `POST /internal/karn/ingest`.

New module (no equivalent in the ported prior art, which wrote Parquet
files via `run_all.py` instead of pushing structured results to an API --
see ADR-13 for why this pipeline pushes instead).
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from dc_calendar.windowing import Window

from karn_tablets import aggregation, clustering, extract
from karn_tablets.clustering import AlgorithmLiteral
from karn_tablets.schemas import Decklist

logger = logging.getLogger(__name__)

#: Bumped whenever the feature/clustering logic materially changes -- part
#: of every pushed result's §45.2 provenance (source data range, pipeline
#: version, model/algorithm info).
PIPELINE_VERSION = "0.1.0"

DEFAULT_ALGORITHM: AlgorithmLiteral = "kmeans"


@dataclass(frozen=True)
class ArchetypeResult:
    """One cluster's output: its share of the window's metagame and a
    representative decklist (the cluster's centroid-nearest real deck).
    """

    cluster_id: int
    deck_count: int
    share: float  # deck_count / total_decks, in [0, 1]
    representative_mainboard: dict[str, int]  # card name -> qty
    representative_sideboard: dict[str, int]  # card name -> qty (commanders, for DC)


@dataclass(frozen=True)
class ClusteringRunResult:
    """Everything one window's clustering run produces, ready to push."""

    window: Window
    algorithm: str
    total_decks: int
    archetypes: list[ArchetypeResult] = field(default_factory=list)
    pipeline_version: str = PIPELINE_VERSION
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def _card_names_by_uuid(df_cards) -> dict[str, str]:
    return dict(zip(df_cards["uuid"], df_cards["name"], strict=True))


def _rename_decklist(deck: Decklist, names_by_uuid: dict[str, str]) -> Decklist:
    """Maps a Decklist's card_uuid keys back to human-readable card names.

    An unresolved uuid (shouldn't happen -- extract.py only ever returns
    uuids it just looked up) falls back to the raw key rather than
    dropping the line, so a lookup gap surfaces as an odd-looking card
    name instead of silently losing count.
    """
    return Decklist(
        mainboard={
            names_by_uuid.get(uuid_, uuid_): qty
            for uuid_, qty in deck.mainboard.items()
        },
        sideboard={
            names_by_uuid.get(uuid_, uuid_): qty
            for uuid_, qty in deck.sideboard.items()
        },
    )


def run(
    window: Window, algorithm: AlgorithmLiteral = DEFAULT_ALGORITHM
) -> ClusteringRunResult:
    """Runs one full clustering pass over `window` and builds the push payload.

    Empty window (no Duel Commander decks in range) returns a result with
    zero archetypes, not an error -- a genuinely quiet period is a valid
    (if uninteresting) outcome, not a pipeline failure.
    """
    coordinates = clustering.clusterize_by_window(window, algorithm=algorithm)
    if not coordinates:
        logger.info("no decks in window %s -- nothing to cluster", window.label)
        return ClusteringRunResult(window=window, algorithm=algorithm, total_decks=0)

    df_dc = extract.load_deck_cards(window.date_from, window.date_to)
    df_cards = extract.load_cards_features()
    names_by_uuid = _card_names_by_uuid(df_cards)

    decklists = extract.load_decklists_from_df(df_dc)
    deck_id_order = list(df_dc["deck_id"].unique())
    deck_index_by_id = {deck_id: i for i, deck_id in enumerate(deck_id_order)}

    total_decks = len(coordinates)
    cluster_ids = sorted({c.cluster for c in coordinates})

    archetypes: list[ArchetypeResult] = []
    for cluster_id in cluster_ids:
        member_deck_ids = [c.deck_id for c in coordinates if c.cluster == cluster_id]
        member_decks = [decklists[deck_index_by_id[did]] for did in member_deck_ids]

        aggregated = aggregation.aggregate_decks(member_decks, order=2)
        representative_mainboard: dict[str, int]
        representative_sideboard: dict[str, int]
        if aggregated is not None:
            renamed = _rename_decklist(aggregated.decklist, names_by_uuid)
            representative_mainboard = renamed.mainboard
            representative_sideboard = renamed.sideboard
        else:  # pragma: no cover -- member_decks is never empty here
            representative_mainboard = {}
            representative_sideboard = {}

        archetypes.append(
            ArchetypeResult(
                cluster_id=cluster_id,
                deck_count=len(member_decks),
                share=round(len(member_decks) / total_decks, 4),
                representative_mainboard=representative_mainboard,
                representative_sideboard=representative_sideboard,
            )
        )

    return ClusteringRunResult(
        window=window,
        algorithm=algorithm,
        total_decks=total_decks,
        archetypes=archetypes,
    )
