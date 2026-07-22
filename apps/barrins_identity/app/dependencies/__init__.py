"""Shared FastAPI dependencies.

Re-exports the most-used dependencies so routes can import from one place:

    from app.dependencies import DatabaseSession, CurrentUser
"""

from app.database.session import DatabaseSession
from app.dependencies.auth import (
    AdminUser,
    CurrentServiceAccount,
    CurrentUser,
    MLDevUser,
    ModeratorUser,
)

__all__ = [
    "AdminUser",
    "CurrentServiceAccount",
    "CurrentUser",
    "DatabaseSession",
    "MLDevUser",
    "ModeratorUser",
]
