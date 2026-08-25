"""Routes /sets, /cards, /mtgjson (S8): MTGJSON reference data.

Public reads (`/sets/*`, `/cards/*`) plus an import trigger gated to
either an admin JWT or the scheduled-refresh service token
(`MTGJSONImportOrAdmin` -- see `app/dependencies/service_auth.py`),
matching `docs/content/back/barrins_api/auth_roles.md`'s already-
documented shape -- except `GET /cards/{id}/prices`, deliberately not
built here (2026-08-05 decision: price import/`AllPrices.json` is out of
this pass's scope, see F8's doc-correction task).

Registered under `/api/v1` (like `/api/v1/auth`), not BFF-namespaced
(`/api/v1/tamiyo-scroll/...`): this is shared, core reference data usable
by any future app, not a Tamiyo-Scroll-specific workflow.
"""

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select, union

from app.database.session import DatabaseSession
from app.dependencies.auth import AdminUser
from app.dependencies.service_auth import MTGJSONImportOrAdmin
from app.models.mtgjson import (
    CASTABLE_BOTH_FACES_LAYOUTS,
    Card,
    MTGJSONImportRun,
    MTGSet,
)
from app.schemas.responses_mtgjson import (
    ResponseCard,
    ResponseImportResult,
    ResponseImportRun,
    ResponseImportStatus,
    ResponseSet,
)
from app.services.mtgjson import MTGJSONClientDep, import_all_printings
from app.services.scripture.card_resolver import invalidate_name_cache
from app.services.scryfall.image_cache import clear_image_cache

router = APIRouter()


@router.post("/mtgjson/import", response_model=ResponseImportResult)
async def import_mtgjson(
    session: DatabaseSession,
    client: MTGJSONClientDep,
    _auth: MTGJSONImportOrAdmin,
) -> ResponseImportResult:
    """Download `AllPrintings.json` and upsert every set/card.

    Idempotent — safe to re-run (e.g. from the daily scheduled refresh)
    without duplicating rows.
    """
    result = await import_all_printings(session, client)
    # T3's card-name resolver caches "cards" name/face_name in-process; a
    # refreshed import must invalidate it or newly-added/renamed cards stay
    # unresolvable until the next restart.
    invalidate_name_cache()
    # scryfall_id can shift/disappear on a refresh too -- wipe the cached
    # images so a stale one is never served past this import.
    clear_image_cache()
    return ResponseImportResult(
        sets_upserted=result.sets_upserted, cards_upserted=result.cards_upserted
    )


@router.get("/mtgjson/status", response_model=ResponseImportStatus)
async def mtgjson_status(session: DatabaseSession) -> ResponseImportStatus:
    """Public: last import time + current row counts, for a quick sanity check."""
    last_imported_at = (
        await session.execute(select(func.max(MTGSet.updated_at)))
    ).scalar_one()
    total_sets = (
        await session.execute(select(func.count()).select_from(MTGSet))
    ).scalar_one()
    total_cards = (
        await session.execute(select(func.count()).select_from(Card))
    ).scalar_one()
    return ResponseImportStatus(
        last_imported_at=last_imported_at,
        total_sets=total_sets,
        total_cards=total_cards,
    )


@router.get("/mtgjson/import/status", response_model=ResponseImportRun)
async def mtgjson_import_status(
    session: DatabaseSession, _admin: AdminUser
) -> ResponseImportRun:
    """Admin: progress of the most recent import run.

    Distinct from `GET /mtgjson/status` above: that one reads final,
    committed `mj_sets`/`mj_cards` counts (public, stable regardless of
    whether an import is running); this one reads `mj_import_runs`, a
    separately-committed progress log that updates *during* a run --
    `status` is `"running"` | `"succeeded"` | `"failed"`, `error_message`
    is only set on failure. Admin-gated because a failure's
    `error_message` can include internal exception text.
    """
    run = (
        await session.execute(
            select(MTGJSONImportRun)
            .order_by(MTGJSONImportRun.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No import has run yet."
        )
    return ResponseImportRun.model_validate(run)


@router.get("/sets/", response_model=list[ResponseSet])
async def list_sets(session: DatabaseSession) -> list[ResponseSet]:
    result = await session.execute(select(MTGSet).order_by(MTGSet.release_date))
    return [ResponseSet.model_validate(s) for s in result.scalars().all()]


@router.get("/sets/{code}", response_model=ResponseSet)
async def get_set(code: str, session: DatabaseSession) -> ResponseSet:
    mtg_set = await session.get(MTGSet, code.upper())
    if mtg_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set not found."
        )
    return ResponseSet.model_validate(mtg_set)


@router.get("/sets/{code}/cards", response_model=list[ResponseCard])
async def get_set_cards(code: str, session: DatabaseSession) -> list[ResponseCard]:
    mtg_set = await session.get(MTGSet, code.upper())
    if mtg_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set not found."
        )
    result = await session.execute(
        select(Card).where(Card.set_code == code.upper()).order_by(Card.number)
    )
    return [ResponseCard.model_validate(c) for c in result.scalars().all()]


@router.get("/cards/by-name/{name:path}", response_model=ResponseCard)
async def get_card_by_name(name: str, session: DatabaseSession) -> ResponseCard:
    """Most recently released printing of a card with this exact name.

    A card is reprinted across many sets/printings; this returns one
    representative row (latest release) rather than every printing —
    callers wanting the full print history use `GET /sets/{code}/cards`
    per set instead.

    `name` uses the `:path` converter, not the default `str` one: every
    multi-face card (MDFC, split, adventure, ...) has a combined name
    containing a literal " // " (e.g. "Bonecrusher Giant // Stomp"), and
    Starlette's default path converter stops matching at the first "/",
    404ing on any of them. `:path` accepts embedded slashes so the full
    name reaches the query below.
    """
    result = await session.execute(
        select(Card)
        .join(MTGSet, Card.set_code == MTGSet.code)
        .where(Card.name == name)
        .order_by(MTGSet.release_date.desc())
        .limit(1)
    )
    card = result.scalar_one_or_none()
    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Card not found."
        )
    return ResponseCard.model_validate(card)


@router.get("/cards/search-by-name/{name:path}", response_model=list[ResponseCard])
async def search_cards_by_name(
    name: str, session: DatabaseSession
) -> list[ResponseCard]:
    """Every distinct card reachable by this name -- full name, or a face name.

    Unlike `GET /cards/by-name/{name}` (one card, exact full-name match
    only), this can return several *distinct* cards for the same query:
    a name can collide between an unrelated card's full name and another
    card's face name (e.g. "Ancestral Recall" is both its own classic
    card and the back face of "Emeritus of Ideation // Ancestral
    Recall"). One row (latest printing) is returned per distinct full
    card name.

    A face name only counts as a match when that face is independently
    castable — both faces for `CASTABLE_BOTH_FACES_LAYOUTS` (Adventure,
    modal DFC, split), front face only otherwise (Transform, Prepare,
    ...). A non-castable back face (e.g. "Insectile Aberration",
    "Ancestral Recall" as Emeritus's back) is deliberately *not* a search
    key at all — it's real card text, not a name you'd use to reference
    the card, so it never surfaces its card here; only the front face's
    name or the full combined name do (see
    `CASTABLE_BOTH_FACES_LAYOUTS`'s docstring).
    """
    candidate_names_stmt = union(
        select(Card.name).where(Card.name == name),
        select(Card.name).where(
            Card.face_name == name,
            or_(
                Card.layout.in_(CASTABLE_BOTH_FACES_LAYOUTS),
                Card.side.is_(None),
                Card.side == "a",
            ),
        ),
    )
    candidate_names = (await session.execute(candidate_names_stmt)).scalars().all()
    if not candidate_names:
        return []

    result = await session.execute(
        select(Card)
        .join(MTGSet, Card.set_code == MTGSet.code)
        .where(Card.name.in_(candidate_names))
        .order_by(Card.name, MTGSet.release_date.desc(), Card.side.asc().nulls_last())
        .distinct(Card.name)
    )
    return [ResponseCard.model_validate(c) for c in result.scalars().all()]


_SEARCH_BY_NAME_PREFIX_LIMIT = 20


@router.get("/cards/search-by-name-prefix", response_model=list[str])
async def search_cards_by_name_prefix(
    session: DatabaseSession, q: str = Query(min_length=1)
) -> list[str]:
    """Distinct card names containing `q` (case-insensitive, substring —
    not just prefix), for on-the-fly name dropdowns (S17 item 2). Unlike
    `GET /cards/search-by-name/{name}`, this is presentation-only: it
    returns names, not full card data, and callers decide their own
    minimum-length gate before querying (Tamiyo Scroll's dropdown uses
    3 characters) -- the actual enforcement of "does this name resolve to
    a real card" stays `TSUserSettings.validate_added_card_exists`
    (unchanged by this endpoint).
    """
    result = await session.execute(
        select(Card.name)
        .where(Card.name.ilike(f"%{q}%"))
        .distinct()
        .order_by(Card.name)
        .limit(_SEARCH_BY_NAME_PREFIX_LIMIT)
    )
    return list(result.scalars().all())


@router.get("/cards/{card_id}", response_model=ResponseCard)
async def get_card(card_id: uuid.UUID, session: DatabaseSession) -> ResponseCard:
    card = await session.get(Card, card_id)
    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Card not found."
        )
    return ResponseCard.model_validate(card)
