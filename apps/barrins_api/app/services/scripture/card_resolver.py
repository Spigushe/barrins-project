"""Resolves a scraped deck-card name against S8's `cards` reference data (T3).

`bs_deck_cards.card_name` (T2) is a plain string, not a `cards.id` FK, so
"validate against S8's data" (T3's design decision) means normalizing a
raw scraped name to whichever known `cards.name`/`cards.face_name` string
it matches — fixing accents/formatting/case drift, not resolving a
surrogate key. A name with no match at all is reported as unresolved; the
caller (`app/services/scripture/ingester.py`) skips that card line rather
than storing an unvalidated string (2026-08-07 decision, T3 doc).

Adapted from a card-name resolver prototype in a pre-rewrite `barrins_api`
branch (github.com/barrins-archive/barrins_api,
`app/services/decklist/resolver.py`) — same normalization strategy
(Unicode compatibility folding, NFKD/ASCII accent stripping, "/"-joined
double-face alternates), simplified for this schema: no `cards.uuid`
resolution, no `unaccent` Postgres extension (avoided as a new dependency
— the same accent-stripping the old code did in SQL via `unaccent()` is
done here in Python via NFKD, so the in-memory cache alone is enough), no
`is_token`/`availability` filtering (this schema has neither column).
"""

import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mtgjson import Card

# U+A789 MODIFIER LETTER COLON (real MTG card names use it, e.g.
# "Ratonhnhake:ton" with the special colon in place of ":") -> ASCII colon.
# The one Unicode-compatibility substitution the prototype above found
# necessary in practice; NFKD alone doesn't fold it.
_COMPAT_MAP = str.maketrans({"꞉": ":"})  # noqa: RUF001

#: Process-local cache: {normalized_name: canonical "cards" name/face_name}.
#: Rebuilt lazily on first use per process, invalidated after every MTGJSON
#: import (`app/api/general/mtgjson.py::import_mtgjson`) so a reference-data
#: refresh is reflected without a restart.
#:
#: Process-local only: if `barrins_api` is ever run with multiple worker
#: processes, an import handled by one worker won't invalidate this cache
#: in the others until they restart. Not a problem today (the current
#: deploy runs a single uvicorn process, see
#: ops/my-server/roles/fastapi_backend), but a real gap to close (a
#: shared/external cache, or a `cards`-table version check) before that
#: ever changes.
_name_cache: dict[str, str] = {}
#: Whether `_name_cache` reflects the current `cards` contents. Separate
#: from `_name_cache`'s own truthiness because an empty dict is
#: ambiguous — "not built yet" and "built, `cards` is genuinely empty"
#: (e.g. before the very first MTGJSON import) are otherwise
#: indistinguishable, and without this flag the latter re-runs the full
#: `cards` scan on every single `resolve_card_name` call instead of once.
_cache_built = False


def invalidate_name_cache() -> None:
    """Clears the cache — call after an MTGJSON import changes `cards`."""
    global _cache_built
    _name_cache.clear()
    _cache_built = False


def normalize_name(name: str) -> str:
    """Compat-fold -> NFKD -> ASCII-only -> lowercase -> strip.

    Two differently-accented/formatted spellings of the same card name
    normalize to the same key (e.g. "Ratonhnhaké:ton" variants).
    """
    return (
        unicodedata.normalize("NFKD", name.translate(_COMPAT_MAP))
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )


def _double_face_alt(name: str) -> str | None:
    """Normalized "A // B" form if `name` uses a "/"-joined shorthand.

    Some scrapers/exports write double-faced/split cards as "A/B" instead
    of the canonical "A // B". Returns None when no such substitution
    applies.
    """
    if "/" in name and " // " not in name:
        return normalize_name(name.replace("/", " // "))
    return None


async def _build_name_cache(session: AsyncSession) -> None:
    global _cache_built
    if _cache_built:
        return
    rows = (await session.execute(select(Card.name, Card.face_name))).all()
    for name, face_name in rows:
        _name_cache.setdefault(normalize_name(name), name)
        if face_name:
            _name_cache.setdefault(normalize_name(face_name), face_name)
    _cache_built = True


async def resolve_card_name(session: AsyncSession, raw_name: str) -> str | None:
    """Canonical `cards` name/face_name matching `raw_name`, or None.

    Preserves whichever form matched (a full combined name or a single
    face's name) rather than always collapsing to the full name — a
    scraped line naming just one face of an adventure/split card is left
    naming that face, only its spelling is canonicalized.
    """
    await _build_name_cache(session)
    normalized = normalize_name(raw_name)
    if (canonical := _name_cache.get(normalized)) is not None:
        return canonical
    if (alt := _double_face_alt(raw_name)) is not None:
        if (canonical := _name_cache.get(alt)) is not None:
            return canonical
    return None


async def resolve_card_name_or_raw(session: AsyncSession, raw_name: str) -> str:
    """`resolve_card_name`'s result, or `raw_name` itself when
    unresolved -- for callers comparing two free-text names for equality
    where an unresolvable-but-identical string should still count as a
    match (S16)."""
    return await resolve_card_name(session, raw_name) or raw_name


def is_attraction(canonical_name: str) -> bool:
    """True if `canonical_name` (a `resolve_card_name` result) is an Attraction.

    Requires the name cache to already be built — only meaningful to call
    after a `resolve_card_name` call on the same session succeeded.
    """
    return canonical_name in _attraction_names
