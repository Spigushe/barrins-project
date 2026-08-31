"""Unit tests for `compute_access` — the app-directory access rule (ADR-19)."""

import pytest

from app.models.application import Application
from app.models.user import User, UserRole
from app.schemas.applications import AccessState
from app.services.applications import compute_access


def _app(**overrides: object) -> Application:
    defaults: dict[str, object] = {
        "key": "x",
        "name": "X",
        "description": "d",
        "url": "https://x.test",
        "logo_svg": "<svg/>",
        "needs_authentication": True,
        "is_role_restricted": False,
        "min_role": None,
        "sort_order": 0,
        "is_active": True,
    }
    defaults.update(overrides)
    return Application(**defaults)


def _user(role: UserRole) -> User:
    return User(
        email=f"{role.value}@test.com",
        username=role.value,
        hashed_password="x",
        role=role,
    )


class TestPublicApp:
    def test_open_for_anonymous(self):
        assert (
            compute_access(_app(needs_authentication=False), None) == AccessState.open
        )

    def test_open_for_authenticated(self):
        app = _app(needs_authentication=False)
        assert compute_access(app, _user(UserRole.user)) == AccessState.open


class TestMemberApp:
    def test_login_required_for_anonymous(self):
        assert compute_access(_app(), None) == AccessState.login_required

    @pytest.mark.parametrize("role", list(UserRole))
    def test_open_for_any_authenticated_role(self, role: UserRole):
        assert compute_access(_app(), _user(role)) == AccessState.open


class TestRoleRestrictedApp:
    def test_login_required_for_anonymous(self):
        app = _app(is_role_restricted=True, min_role=UserRole.ml_developer)
        assert compute_access(app, None) == AccessState.login_required

    def test_role_denied_below_min_role(self):
        app = _app(is_role_restricted=True, min_role=UserRole.ml_developer)
        assert compute_access(app, _user(UserRole.moderator)) == AccessState.role_denied

    def test_open_at_min_role(self):
        app = _app(is_role_restricted=True, min_role=UserRole.ml_developer)
        assert compute_access(app, _user(UserRole.ml_developer)) == AccessState.open

    def test_open_above_min_role(self):
        app = _app(is_role_restricted=True, min_role=UserRole.ml_developer)
        assert compute_access(app, _user(UserRole.admin)) == AccessState.open
