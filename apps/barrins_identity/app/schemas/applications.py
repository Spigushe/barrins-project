"""Pydantic schemas for the Goblin Guide app directory (ADR-19)."""

import enum

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class AccessState(enum.StrEnum):
    """Per-caller access to an application, computed by the backend.

    - ``open`` — the caller can open it now.
    - ``login_required`` — a public-to-members app the caller must sign in
      for.
    - ``role_denied`` — the caller is signed in but their role is below
      ``min_role``.
    """

    open = "open"
    login_required = "login_required"
    role_denied = "role_denied"


class ApplicationRead(BaseModel):
    """One card in `GET /api/v1/applications`.

    `min_role` is echoed (null unless role-restricted) so the client can
    label a "réservé" group without a second lookup — it is policy
    metadata, not a secret.
    """

    model_config = ConfigDict(from_attributes=True)

    key: str
    name: str
    description: str
    url: str
    logo_svg: str
    access: AccessState
    min_role: UserRole | None = None
