"""Pydantic schemas for per-app settings (platform.md §17)."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class AppSettingsRead(BaseModel):
    """Response of GET/PUT /users/me/settings/{app_key}.

    `data` is served verbatim — `barrins_identity` validates nothing
    about its internal shape beyond overall size (enforced in the route
    handler, platform.md §17.3). Typed `dict[str, Any]` rather than the
    recursive `JsonValue` alias (`app/models/_types.py`): that alias isn't
    safe to use as a Pydantic field (implicit recursive type aliases hit
    Pydantic's recursion limit — see
    https://docs.pydantic.dev/2.13/concepts/types/#named-recursive-types),
    and `Any` is arguably the more honest fit anyway for a blob this
    service deliberately validates nothing about.
    """

    model_config = ConfigDict(from_attributes=True)

    data: dict[str, Any]
