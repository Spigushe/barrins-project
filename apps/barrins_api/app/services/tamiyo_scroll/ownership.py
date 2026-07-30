"""Resolution of the "owner" user targeted by a read request (sharing).

Cf. docs/tamiyo_scroll_tracker/00_plan_general.md, Option B: this parameter is
never accepted on write routes — only GET routes use it.
"""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models.tamiyo_scroll import TSUserSettings
from app.models.user import User


async def resolve_owner(
    session: DatabaseSession,
    current_user: CurrentUser,
    owner_id: uuid.UUID | None = None,
) -> User:
    """Resolve the user whose data must be read.

    `owner_id` missing or equal to `current_user.id` -> returns `current_user`.
    `owner_id` different -> requires that the target exists (404 otherwise), has
    enabled sharing (`ts_user_settings.data_shared = True`), and that
    `current_user` has enabled receiving shared data
    (`ts_user_settings.receive_shared_data = True`) — 403 otherwise for
    either condition. Single global toggles on both sides (account-settings
    popup handoff), not a per-sharer opt-in.
    """
    if owner_id is None or owner_id == current_user.id:
        return current_user

    result = await session.execute(select(User).where(User.id == owner_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    settings_result = await session.execute(
        select(TSUserSettings).where(TSUserSettings.user_id == owner_id)
    )
    owner_settings = settings_result.scalar_one_or_none()
    if owner_settings is None or not owner_settings.data_shared:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user does not share their data.",
        )

    viewer_settings_result = await session.execute(
        select(TSUserSettings).where(TSUserSettings.user_id == current_user.id)
    )
    viewer_settings = viewer_settings_result.scalar_one_or_none()
    if viewer_settings is None or not viewer_settings.receive_shared_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have not enabled receiving shared data.",
        )

    return target


ResolvedOwner = Annotated[User, Depends(resolve_owner)]
