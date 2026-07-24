"""Routes /personal-decks, .../versions*, .../decklist-view."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models.tamiyo_scroll import (
    DecklistVersionSource,
    TSCardTest,
    TSPersonalDeck,
    TSPersonalDecklistVersion,
)
from app.schemas.responses_tamiyo_scroll import (
    ResponseDecklistLine,
    ResponseDecklistVersion,
    ResponsePersonalDeck,
)
from app.schemas.tamiyo_scroll import (
    DecklistVersionCreate,
    MoxfieldImportRequest,
    PersonalDeckCreate,
)
from app.services.tamiyo_scroll.decklist_coloring import color_decklist
from app.services.tamiyo_scroll.ownership import ResolvedOwner

router = APIRouter()


async def _get_owned_personal_deck(
    session: DatabaseSession, deck_id: uuid.UUID, owner_id: uuid.UUID
) -> TSPersonalDeck:
    result = await session.execute(
        select(TSPersonalDeck).where(
            TSPersonalDeck.id == deck_id, TSPersonalDeck.owner_id == owner_id
        )
    )
    deck = result.scalar_one_or_none()
    if deck is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Personal deck not found."
        )
    return deck


async def _create_version(
    session: DatabaseSession,
    deck: TSPersonalDeck,
    content: str,
    source: DecklistVersionSource,
) -> TSPersonalDecklistVersion:
    # Locks the parent deck's row to prevent a race on the version number
    # between two concurrent requests (cf. plan, Points of vigilance).
    await session.execute(
        select(TSPersonalDeck).where(TSPersonalDeck.id == deck.id).with_for_update()
    )
    max_version_result = await session.execute(
        select(func.max(TSPersonalDecklistVersion.version)).where(
            TSPersonalDecklistVersion.personal_deck_id == deck.id
        )
    )
    next_version = (max_version_result.scalar_one_or_none() or 0) + 1

    version = TSPersonalDecklistVersion(
        personal_deck_id=deck.id,
        version=next_version,
        content=content,
        source=source,
    )
    session.add(version)
    await session.commit()
    await session.refresh(version)
    return version


@router.get("/personal-decks", response_model=list[ResponsePersonalDeck])
async def list_personal_decks(
    session: DatabaseSession,
    owner: ResolvedOwner,
    include_archived: bool = False,
) -> list[ResponsePersonalDeck]:
    stmt = select(TSPersonalDeck).where(TSPersonalDeck.owner_id == owner.id)
    if not include_archived:
        stmt = stmt.where(TSPersonalDeck.archived_at.is_(None))
    stmt = stmt.order_by(TSPersonalDeck.created_at)
    result = await session.execute(stmt)
    return [ResponsePersonalDeck.model_validate(d) for d in result.scalars().all()]


@router.post(
    "/personal-decks",
    response_model=ResponsePersonalDeck,
    status_code=status.HTTP_201_CREATED,
)
async def create_personal_deck(
    payload: PersonalDeckCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponsePersonalDeck:
    deck = TSPersonalDeck(owner_id=current_user.id, name=payload.name)
    session.add(deck)
    await session.commit()
    await session.refresh(deck)
    return ResponsePersonalDeck.model_validate(deck)


@router.delete("/personal-decks/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_personal_deck(
    deck_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Archive the deck (`archived_at`) — never a SQL DELETE, cf. plan Option G."""
    deck = await _get_owned_personal_deck(session, deck_id, current_user.id)
    deck.archived_at = datetime.now(UTC)
    session.add(deck)
    await session.commit()


@router.get(
    "/personal-decks/{deck_id}/versions", response_model=list[ResponseDecklistVersion]
)
async def list_decklist_versions(
    deck_id: uuid.UUID,
    session: DatabaseSession,
    owner: ResolvedOwner,
) -> list[ResponseDecklistVersion]:
    deck = await _get_owned_personal_deck(session, deck_id, owner.id)
    result = await session.execute(
        select(TSPersonalDecklistVersion)
        .where(TSPersonalDecklistVersion.personal_deck_id == deck.id)
        .order_by(TSPersonalDecklistVersion.version.desc())
    )
    return [ResponseDecklistVersion.model_validate(v) for v in result.scalars().all()]


@router.post(
    "/personal-decks/{deck_id}/versions",
    response_model=ResponseDecklistVersion,
    status_code=status.HTTP_201_CREATED,
)
async def create_decklist_version(
    deck_id: uuid.UUID,
    payload: DecklistVersionCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseDecklistVersion:
    deck = await _get_owned_personal_deck(session, deck_id, current_user.id)
    version = await _create_version(
        session, deck, payload.content, DecklistVersionSource.manual
    )
    return ResponseDecklistVersion.model_validate(version)


@router.post(
    "/personal-decks/{deck_id}/versions/import-moxfield",
    response_model=ResponseDecklistVersion,
    status_code=status.HTTP_201_CREATED,
)
async def import_moxfield_placeholder(
    deck_id: uuid.UUID,
    payload: MoxfieldImportRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseDecklistVersion:
    """Create a placeholder version — no real scraping in v1 (cf. Non-goals)."""
    deck = await _get_owned_personal_deck(session, deck_id, current_user.id)
    placeholder = (
        "Import Moxfield en attente de l'extension BFF future — "
        f"lien fourni : {payload.moxfield_url}"
    )
    version = await _create_version(
        session, deck, placeholder, DecklistVersionSource.moxfield_import
    )
    return ResponseDecklistVersion.model_validate(version)


@router.delete(
    "/personal-decks/{deck_id}/versions/{version_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_decklist_version(
    deck_id: uuid.UUID,
    version_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Actually deletes the version — it's not the deck that's targeted (Option G)."""
    deck = await _get_owned_personal_deck(session, deck_id, current_user.id)
    result = await session.execute(
        select(TSPersonalDecklistVersion).where(
            TSPersonalDecklistVersion.id == version_id,
            TSPersonalDecklistVersion.personal_deck_id == deck.id,
        )
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Version not found."
        )
    await session.delete(version)
    await session.commit()


@router.get(
    "/personal-decks/{deck_id}/decklist-view", response_model=list[ResponseDecklistLine]
)
async def get_decklist_view(
    deck_id: uuid.UUID,
    session: DatabaseSession,
    owner: ResolvedOwner,
) -> list[ResponseDecklistLine]:
    deck = await _get_owned_personal_deck(session, deck_id, owner.id)
    latest_result = await session.execute(
        select(TSPersonalDecklistVersion)
        .where(TSPersonalDecklistVersion.personal_deck_id == deck.id)
        .order_by(TSPersonalDecklistVersion.version.desc())
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()
    if latest is None:
        return []

    tests_result = await session.execute(
        select(TSCardTest).where(
            TSCardTest.owner_id == owner.id, TSCardTest.personal_deck_id == deck_id
        )
    )
    card_tests = tests_result.scalars().all()
    colored_lines = color_decklist(latest.content, card_tests)
    return [ResponseDecklistLine(**line) for line in colored_lines]
