"""App-directory service — turns `applications` rows + the caller into the
per-card `access` state the SPA renders (ADR-19, constitution §4.1)."""

from sqlalchemy import select

from app.database.session import DatabaseSession
from app.models.application import Application
from app.models.user import User
from app.schemas.applications import AccessState, ApplicationRead


def compute_access(app: Application, user: User | None) -> AccessState:
    """Resolve one application's access state for `user` (None = anonymous).

    - not `needs_authentication` → always ``open``
    - needs auth, not role-restricted → ``open`` if signed in, else
      ``login_required``
    - role-restricted → ``open`` if signed in and
      ``user.role.level >= min_role.level``; ``role_denied`` if signed in
      and below; ``login_required`` if anonymous
    """
    if not app.needs_authentication:
        return AccessState.open
    if user is None:
        return AccessState.login_required
    if not app.is_role_restricted:
        return AccessState.open
    # is_role_restricted ⇒ min_role is not None (DB CHECK constraint).
    assert app.min_role is not None
    if user.role.level >= app.min_role.level:
        return AccessState.open
    return AccessState.role_denied


async def list_applications(
    session: DatabaseSession, user: User | None
) -> list[ApplicationRead]:
    """Every active application, ordered by `sort_order` then `name`, each
    with its `access` state for `user`.

    Does *not* drop the caller's current app — that's a client concern
    (a host app filters its own `key`).
    """
    result = await session.execute(
        select(Application)
        .where(Application.is_active.is_(True))
        .order_by(Application.sort_order, Application.name)
    )
    return [
        ApplicationRead(
            key=app.key,
            name=app.name,
            description=app.description,
            url=app.url,
            logo_svg=app.logo_svg,
            access=compute_access(app, user),
            min_role=app.min_role,
        )
        for app in result.scalars()
    ]
