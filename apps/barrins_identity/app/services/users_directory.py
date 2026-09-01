"""Batch user-label lookup for consumer backends (ADR-20).

`barrins_api` (and later other consumers) reference identity users on
their own domain rows but hold no copy of the `users` table. This service
answers "give me `{username, display_name}` for these ids" — active
accounts only, public label attributes only.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from app.database.session import DatabaseSession
from app.models.user import User
from app.schemas.users import UserLookupRead


async def lookup_users(
    session: DatabaseSession, ids: Sequence[UUID]
) -> list[UserLookupRead]:
    """Public label attributes for each *active* id in `ids`.

    Unknown ids and soft-deleted / deactivated accounts are simply absent
    from the result — the caller falls back to a generic placeholder.
    """
    unique_ids = list(dict.fromkeys(ids))
    if not unique_ids:
        return []
    result = await session.execute(
        select(User.id, User.username, User.display_name).where(
            User.id.in_(unique_ids), User.is_active.is_(True)
        )
    )
    return [
        UserLookupRead(id=row.id, username=row.username, display_name=row.display_name)
        for row in result
    ]
