"""Shared fixtures/helpers for Karn Tablets ingest + read tests (ADR-13)."""

import uuid
from datetime import UTC, date, datetime

import pytest
from pydantic import SecretStr

from app.config import settings
from app.models.mtgjson import Card, MTGSet

TOKEN = "test-karn-token"  # noqa: S105
INGEST_URL = "/internal/karn/ingest"
BFF = "/bff/tolaria-news"

#: 60 shared cards -- the base of every test archetype's representative
#: mainboard. Variants swap a handful of names to tune Jaccard overlap.
_BASE_CARDS = [f"Card {i:02d}" for i in range(60)]


@pytest.fixture(autouse=True)
def _configured_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings.base, "karn_ingest_token", SecretStr(TOKEN))


@pytest.fixture()
async def karn_reference_cards(db_session) -> None:
    """`mj_cards` rows the `/metagame` + `/archetypes` routes resolve
    against for card-image `scryfall_id`, land detection, and the
    field-prevalence signature filter (`app.services.karn.read`)."""
    db_session.add(
        MTGSet(
            code="KTT",
            name="Karn Tablets Test",
            release_date=date(2026, 1, 1),
            type="expansion",
            base_set_size=5,
            total_set_size=5,
            keyrune_code="ktt",
        )
    )
    await db_session.flush()

    def _card(
        number: str,
        name: str,
        type_line: str,
        scryfall_id: str | None,
        supertypes: list[str] | None = None,
    ) -> Card:
        return Card(
            id=uuid.uuid4(),
            set_code="KTT",
            name=name,
            type_line=type_line,
            supertypes=supertypes or [],
            color_identity=[],
            rarity="common",
            number=number,
            scryfall_id=scryfall_id,
        )

    db_session.add_all(
        [
            _card(
                "1",
                "Snow-Covered Plains",
                "Basic Snow Land — Plains",
                "plains-id",
                supertypes=["Basic", "Snow"],
            ),
            _card("2", "Sol Ring", "Artifact", "sol-ring-id"),
            _card("3", "Command Tower", "Land", "command-tower-id"),
            _card("4", "Brainstorm", "Instant", "brainstorm-id"),
            _card(
                "5",
                "Gaea's Cradle",
                "Legendary Land",
                "gaeas-cradle-id",
                supertypes=["Legendary"],
            ),
            _card(
                "6", "Commander One", "Legendary Creature — Human", "commander-one-id"
            ),
        ]
    )
    await db_session.commit()


def mainboard(swap: int = 0, prefix: str = "Alt") -> dict[str, int]:
    """The base 60-card list with its last `swap` entries replaced by
    `{prefix} NN` names -- `swap=0` is the reference archetype, a small
    `swap` stays above the match threshold, a full swap is disjoint.
    """
    kept = _BASE_CARDS[: 60 - swap]
    swapped = [f"{prefix} {i:02d}" for i in range(swap)]
    return dict.fromkeys([*kept, *swapped], 1)


def archetype(
    cluster_id: int,
    deck_count: int,
    total: int,
    *,
    swap: int = 0,
    prefix: str = "Alt",
    commander: str = "Commander One",
) -> dict:
    return {
        "cluster_id": cluster_id,
        "deck_count": deck_count,
        "share": round(deck_count / total, 4),
        "representative_mainboard": mainboard(swap=swap, prefix=prefix),
        "representative_sideboard": {commander: 1} if commander else {},
    }


def payload(
    *,
    kind: str = "rolling_30d",
    label: str = "rolling_30d:2026-08-27",
    date_from: str = "2026-07-28",
    date_to: str = "2026-08-27",
    algorithm: str = "kmeans",
    generated_at: datetime | None = None,
    archetypes: list[dict] | None = None,
    total_decks: int | None = None,
    fmt: str | None = None,
) -> dict:
    archetypes = archetypes if archetypes is not None else [archetype(1, 30, 30)]
    total = (
        total_decks
        if total_decks is not None
        else sum(a["deck_count"] for a in archetypes)
    )
    body = {
        "window": {
            "kind": kind,
            "date_from": date_from,
            "date_to": date_to,
            "label": label,
        },
        "algorithm": algorithm,
        "total_decks": total,
        "pipeline_version": "0.1.0",
        "generated_at": (generated_at or datetime.now(UTC)).isoformat(),
        "archetypes": archetypes,
    }
    if fmt is not None:
        body["format"] = fmt
    return body


def headers() -> dict[str, str]:
    return {"X-Karn-Token": TOKEN}


def rolling_label(day: date) -> str:
    return f"rolling_30d:{day.isoformat()}"
