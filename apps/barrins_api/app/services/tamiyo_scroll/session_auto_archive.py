"""Auto-archive stale sessions (S14 item 9).

Event-triggered, not a periodic job: runs synchronously whenever a new
decklist version is created for a deck (Moxfield import or plain-text
import) — see `app.api.tamiyo_scroll.personal_decks._create_version`. This
sidesteps the doc's open scheduler question entirely (no in-process
scheduler, no periodic job, nothing to run on the VPS or in CI).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.database.session import DatabaseSession
from app.models.tamiyo_scroll import (
    TSMatch,
    TSPersonalDeck,
    TSPersonalDecklistVersion,
    TSSession,
    TSUserSettings,
)


def session_is_stale(
    latest_match_version: int | None, max_version: int, threshold: int
) -> bool:
    """A session with no matches yet has nothing to compare against — never
    auto-archived (returns `False`). Otherwise stale once the deck's
    current latest version has moved `threshold` versions (or more) ahead
    of the session's most recent match's decklist version.
    """
    if latest_match_version is None:
        return False
    return max_version - latest_match_version >= threshold


async def sweep_stale_sessions(
    db: DatabaseSession, deck: TSPersonalDeck, owner_id: uuid.UUID
) -> None:
    """Archives every non-archived session on `deck` whose most recent
    match has fallen too far behind the deck's current latest decklist
    version. No-op unless the owner opted in via
    `TSUserSettings.auto_archive_stale_sessions`.
    """
    settings_result = await db.execute(
        select(TSUserSettings).where(TSUserSettings.user_id == owner_id)
    )
    settings = settings_result.scalar_one_or_none()
    if settings is None or not settings.auto_archive_stale_sessions:
        return

    max_version_result = await db.execute(
        select(func.max(TSPersonalDecklistVersion.version)).where(
            TSPersonalDecklistVersion.personal_deck_id == deck.id
        )
    )
    max_version = max_version_result.scalar_one_or_none()
    if max_version is None:
        return

    sessions_result = await db.execute(
        select(TSSession).where(
            TSSession.personal_deck_id == deck.id,
            TSSession.archived_at.is_(None),
        )
    )
    sessions = list(sessions_result.scalars().all())
    if not sessions:
        return

    archived_any = False
    for ts_session in sessions:
        latest_match_result = await db.execute(
            select(TSMatch)
            .where(TSMatch.session_id == ts_session.id)
            .order_by(TSMatch.created_at.desc())
            .limit(1)
        )
        latest_match = latest_match_result.scalar_one_or_none()
        if latest_match is None or latest_match.decklist_version_id is None:
            continue

        version_result = await db.execute(
            select(TSPersonalDecklistVersion.version).where(
                TSPersonalDecklistVersion.id == latest_match.decklist_version_id
            )
        )
        latest_match_version = version_result.scalar_one_or_none()

        if session_is_stale(
            latest_match_version,
            max_version,
            settings.auto_archive_decklist_version_gap,
        ):
            ts_session.archived_at = datetime.now(UTC)
            db.add(ts_session)
            archived_any = True

    if archived_any:
        await db.commit()
