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
from app.models.tamiyo_scroll import TSReceiveOptIn, TSUserSettings
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
    `current_user` has opted in to receive that specific sharer's data
    (`ts_receive_opt_ins`) — 403 otherwise for either condition.
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

    opt_in_result = await session.execute(
        select(TSReceiveOptIn).where(
            TSReceiveOptIn.viewer_id == current_user.id,
            TSReceiveOptIn.sharer_id == owner_id,
        )
    )
    if opt_in_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have not opted in to receive this user's shared data.",
        )

    return target


ResolvedOwner = Annotated[User, Depends(resolve_owner)]
