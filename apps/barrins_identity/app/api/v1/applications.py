"""App-directory route — the role-aware Goblin Guide launcher (ADR-19).

`GET /api/v1/applications` is the only endpoint: it returns every active
application with a backend-computed `access` state for the caller.
Authentication is *optional* — an anonymous request gets `login_required`
on member-only apps.
"""

from fastapi import APIRouter

from app.database.session import DatabaseSession
from app.dependencies.auth import OptionalCurrentUser
from app.schemas.applications import ApplicationRead
from app.services.applications import list_applications

router = APIRouter()


@router.get("/applications", response_model=list[ApplicationRead])
async def get_applications(
    session: DatabaseSession,
    current_user: OptionalCurrentUser,
) -> list[ApplicationRead]:
    """List the Barrin's applications, each with the caller's `access` state.

    Ordered by `sort_order` then `name`. Inactive apps are omitted. The
    caller's *own* app is **not** filtered here — a host app drops its own
    `key` client-side.
    """
    return await list_applications(session, current_user)
