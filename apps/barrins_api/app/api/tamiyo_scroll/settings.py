"""Routes GET/PATCH /me/settings, GET /shared-users, receive opt-ins."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models.tamiyo_scroll import TSPersonalDeck, TSReceiveOptIn, TSUserSettings
from app.models.user import User
from app.schemas.responses_tamiyo_scroll import (
    ResponseAvailableSharer,
    ResponseSharedUser,
    ResponseUserSettings,
)
from app.schemas.tamiyo_scroll import ReceiveOptInCreate, UserSettingsUpdate

router = APIRouter()


async def _get_or_create_settings(
    session: DatabaseSession, user_id: uuid.UUID
) -> TSUserSettings:
    result = await session.execute(
        select(TSUserSettings).where(TSUserSettings.user_id == user_id)
    )
    user_settings = result.scalar_one_or_none()
    if user_settings is None:
        user_settings = TSUserSettings(user_id=user_id)
        session.add(user_settings)
        await session.commit()
        await session.refresh(user_settings)
    return user_settings


@router.get("/shared-users", response_model=list[ResponseSharedUser])
async def list_shared_users(
    session: DatabaseSession, current_user: CurrentUser
) -> list[ResponseSharedUser]:
    """Users viewable via the "View: {user}" selector.

    Requires both sides: the sharer has `data_shared = True`, and
    `current_user` has opted in to receive that specific sharer's data
    (`ts_receive_opt_ins`) — see S1.
    """
    result = await session.execute(
        select(User)
        .join(TSUserSettings, TSUserSettings.user_id == User.id)
        .join(TSReceiveOptIn, TSReceiveOptIn.sharer_id == User.id)
        .where(
            TSUserSettings.data_shared.is_(True),
            User.id != current_user.id,
            TSReceiveOptIn.viewer_id == current_user.id,
        )
        .order_by(User.email)
    )
    return [ResponseSharedUser.model_validate(u) for u in result.scalars().all()]


@router.get("/available-sharers", response_model=list[ResponseAvailableSharer])
async def list_available_sharers(
    session: DatabaseSession, current_user: CurrentUser
) -> list[ResponseAvailableSharer]:
    """Every user with sharing enabled, annotated with the viewer's opt-in state.

    Backs the "Receive shared data from" opt-in management UI — distinct
    from `/shared-users`, which only returns sharers already opted into.
    """
    result = await session.execute(
        select(User, TSReceiveOptIn.id)
        .join(TSUserSettings, TSUserSettings.user_id == User.id)
        .outerjoin(
            TSReceiveOptIn,
            (TSReceiveOptIn.sharer_id == User.id)
            & (TSReceiveOptIn.viewer_id == current_user.id),
        )
        .where(TSUserSettings.data_shared.is_(True), User.id != current_user.id)
        .order_by(User.email)
    )
    return [
        ResponseAvailableSharer(
            id=user.id,
            display_name=user.display_name,
            email=user.email,
            opted_in=opt_in_id is not None,
        )
        for user, opt_in_id in result.all()
    ]


@router.post(
    "/receive-opt-ins",
    response_model=ResponseAvailableSharer,
    status_code=status.HTTP_201_CREATED,
)
async def create_receive_opt_in(
    payload: ReceiveOptInCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseAvailableSharer:
    """Opt in to receive one specific sharer's data."""
    if payload.sharer_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot opt in to receive your own data.",
        )

    sharer_result = await session.execute(
        select(User)
        .join(TSUserSettings, TSUserSettings.user_id == User.id)
        .where(User.id == payload.sharer_id, TSUserSettings.data_shared.is_(True))
    )
    sharer = sharer_result.scalar_one_or_none()
    if sharer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user does not share their data.",
        )

    existing_result = await session.execute(
        select(TSReceiveOptIn).where(
            TSReceiveOptIn.viewer_id == current_user.id,
            TSReceiveOptIn.sharer_id == payload.sharer_id,
        )
    )
    if existing_result.scalar_one_or_none() is None:
        session.add(
            TSReceiveOptIn(viewer_id=current_user.id, sharer_id=payload.sharer_id)
        )
        await session.commit()

    return ResponseAvailableSharer(
        id=sharer.id,
        display_name=sharer.display_name,
        email=sharer.email,
        opted_in=True,
    )


@router.delete("/receive-opt-ins/{sharer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_receive_opt_in(
    sharer_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Opt out of receiving a specific sharer's data."""
    result = await session.execute(
        select(TSReceiveOptIn).where(
            TSReceiveOptIn.viewer_id == current_user.id,
            TSReceiveOptIn.sharer_id == sharer_id,
        )
    )
    opt_in = result.scalar_one_or_none()
    if opt_in is not None:
        await session.delete(opt_in)
        await session.commit()


@router.get("/me/settings", response_model=ResponseUserSettings)
async def get_my_settings(
    session: DatabaseSession, current_user: CurrentUser
) -> ResponseUserSettings:
    user_settings = await _get_or_create_settings(session, current_user.id)
    return ResponseUserSettings.model_validate(user_settings)


@router.patch("/me/settings", response_model=ResponseUserSettings)
async def update_my_settings(
    payload: UserSettingsUpdate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ResponseUserSettings:
    user_settings = await _get_or_create_settings(session, current_user.id)

    if payload.data_shared is not None:
        user_settings.data_shared = payload.data_shared

    if "active_personal_deck_id" in payload.model_fields_set:
        if payload.active_personal_deck_id is not None:
            deck_result = await session.execute(
                select(TSPersonalDeck.id).where(
                    TSPersonalDeck.id == payload.active_personal_deck_id,
                    TSPersonalDeck.owner_id == current_user.id,
                )
            )
            if deck_result.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Personal deck not found.",
                )
        user_settings.active_personal_deck_id = payload.active_personal_deck_id

    session.add(user_settings)
    await session.commit()
    await session.refresh(user_settings)
    return ResponseUserSettings.model_validate(user_settings)
