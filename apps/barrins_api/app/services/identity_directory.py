"""Resolve identity user display attributes for the teams / sharing UI.

Since the cutover (ADR-20) `barrins_api` has no local `users` table, but a
few read paths still need a *label* for other users — team rosters, team
chat authors, deck-owner names, the "shared with you" banner. `barrins_api`
asks `barrins_identity` for `{username, display_name}` in batches
(`POST /api/v1/users/lookup`), authenticating with its own service-account
token (`POST /api/v1/service-token`), and caches the answers in-process for
a few minutes.

Deliberately degrades to nothing: if no service-account credentials are
configured, or identity is unreachable, `lookup()` returns `{}` and callers
fall back to a generic placeholder. A missing display label is a cosmetic
regression, never a request failure.
"""

import asyncio
import time
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Annotated, Any

import httpx
from fastapi import Depends

from app.config import settings
from app.core.log_config import get_logger

logger = get_logger(__name__)

# How long a resolved (username, display_name) stays cached in-process.
_ENTRY_TTL_SECONDS = 300.0
# Renew the service token this many seconds before it actually expires.
_TOKEN_REFRESH_SKEW_SECONDS = 60.0
_HTTP_TIMEOUT_SECONDS = 5.0
# Matches the identity endpoint's own cap.
_MAX_IDS_PER_CALL = 200

ANONYMOUS_LABEL = "a kind user"


@dataclass(frozen=True, slots=True)
class UserRef:
    """The public label attributes for one identity user."""

    username: str
    display_name: str | None = None

    @property
    def label(self) -> str:
        """Display name if set, else the handle."""
        return self.display_name or self.username


class IdentityDirectory:
    """Batched, cached `{user_id: UserRef}` lookups against `barrins_identity`."""

    def __init__(
        self,
        *,
        service_url: str,
        client_id: str,
        client_secret: str,
        entry_ttl_seconds: float = _ENTRY_TTL_SECONDS,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base = service_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._entry_ttl = entry_ttl_seconds
        self._http_client = http_client
        self._enabled = bool(client_id and client_secret)
        self._cache: dict[uuid.UUID, tuple[float, UserRef]] = {}
        self._token: str | None = None
        self._token_expiry_monotonic = 0.0
        self._token_lock = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def lookup(self, ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, UserRef]:
        """Return the known `UserRef` for each id (unknown ids simply absent)."""
        wanted = set(ids)
        if not wanted or not self._enabled:
            return {}

        now = time.monotonic()
        resolved: dict[uuid.UUID, UserRef] = {}
        missing: set[uuid.UUID] = set()
        for user_id in wanted:
            entry = self._cache.get(user_id)
            if entry is not None and entry[0] > now:
                resolved[user_id] = entry[1]
            else:
                missing.add(user_id)

        for chunk in _chunked(sorted(missing), _MAX_IDS_PER_CALL):
            fetched = await self._fetch(chunk)
            expiry = time.monotonic() + self._entry_ttl
            for user_id, ref in fetched.items():
                self._cache[user_id] = (expiry, ref)
                resolved[user_id] = ref

        return resolved

    async def label(
        self, user_id: uuid.UUID, *, fallback: str = ANONYMOUS_LABEL
    ) -> str:
        """Best-effort display label for a single user."""
        ref = (await self.lookup([user_id])).get(user_id)
        return ref.label if ref is not None else fallback

    async def _fetch(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, UserRef]:
        try:
            token = await self._service_token()
            payload = await self._post_json(
                "/api/v1/users/lookup",
                {"ids": [str(i) for i in ids]},
                token=token,
            )
            rows: list[Any] = list(payload)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            logger.warning("identity directory lookup failed: %s", exc)
            return {}

        out: dict[uuid.UUID, UserRef] = {}
        for row in rows:
            try:
                out[uuid.UUID(row["id"])] = UserRef(
                    username=row["username"],
                    display_name=row.get("display_name"),
                )
            except KeyError, ValueError, TypeError:
                continue
        return out

    async def _service_token(self) -> str:
        now = time.monotonic()
        if self._token is not None and self._token_expiry_monotonic > now:
            return self._token
        async with self._token_lock:
            if (
                self._token is not None
                and self._token_expiry_monotonic > time.monotonic()
            ):
                return self._token
            payload = await self._post_json(
                "/api/v1/service-token",
                {
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                token=None,
            )
            data: dict[str, Any] = dict(payload)
            self._token = str(data["access_token"])
            expires_in = float(data.get("expires_in", 0))
            self._token_expiry_monotonic = time.monotonic() + max(
                0.0, expires_in - _TOKEN_REFRESH_SKEW_SECONDS
            )
            return self._token

    async def _post_json(
        self, path: str, body: dict[str, Any], *, token: str | None
    ) -> Any:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        client = self._http_client or httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS)
        try:
            response = await client.post(
                f"{self._base}{path}", json=body, headers=headers
            )
            response.raise_for_status()
            return response.json()
        finally:
            if self._http_client is None:
                await client.aclose()


def _chunked(items: list[uuid.UUID], size: int) -> Iterable[list[uuid.UUID]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


_directory = IdentityDirectory(
    service_url=settings.base.identity_service_url,
    client_id=settings.base.identity_service_client_id,
    client_secret=settings.base.identity_service_client_secret.get_secret_value(),
)


def get_identity_directory() -> IdentityDirectory:
    """FastAPI dependency — one process-wide `IdentityDirectory`."""
    return _directory


IdentityDirectoryDep = Annotated[IdentityDirectory, Depends(get_identity_directory)]
