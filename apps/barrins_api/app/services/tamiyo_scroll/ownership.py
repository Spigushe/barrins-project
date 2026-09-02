"""Resolution of the "owner" user targeted by a read request (sharing).

Cf. docs/tamiyo_scroll_tracker/00_plan_general.md, Option B: this parameter is
never accepted on write routes — only GET routes use it.

Since the identity cutover (ADR-20) `barrins_api` has no `users` table, so
`owner_id` is treated as an opaque key into `ts_user_settings` (the
sharing opt-in preference row). There is no "user not found" case — an
`owner_id` with no shared settings row is simply "does not share".
"""

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select

from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models.tamiyo_scroll import TSUserSettings


@dataclass(frozen=True, slots=True)
class OwnerRef:
    """The user whose data a read request targets — just the id."""

    id: uuid.UUID


async def resolve_owner(
    session: DatabaseSession,
    current_user: CurrentUser,
    owner_id: uuid.UUID | None = None,
) -> OwnerRef:
    """Resolve the user whose data must be read.

    `owner_id` missing or equal to `current_user.id` -> the caller.
    `owner_id` different -> requires that the target has enabled sharing
    (`ts_user_settings.data_shared = True`) and that `current_user` has
    enabled receiving shared data
    (`ts_user_settings.receive_shared_data = True`) — 403 otherwise for
    either condition. Single global toggles on both sides (account-settings
    popup handoff), not a per-sharer opt-in.
    """
    if owner_id is None or owner_id == current_user.id:
        return OwnerRef(id=current_user.id)

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

    return OwnerRef(id=owner_id)


ResolvedOwner = Annotated[OwnerRef, Depends(resolve_owner)]
