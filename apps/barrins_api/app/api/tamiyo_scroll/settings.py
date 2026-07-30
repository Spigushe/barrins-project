"""Routes GET/PATCH /me/settings."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models.tamiyo_scroll import TSPersonalDeck, TSUserSettings
from app.schemas.responses_tamiyo_scroll import ResponseUserSettings
from app.schemas.tamiyo_scroll import UserSettingsUpdate

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

    if payload.receive_shared_data is not None:
        user_settings.receive_shared_data = payload.receive_shared_data

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
