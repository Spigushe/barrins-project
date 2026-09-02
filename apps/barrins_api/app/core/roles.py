"""Role ordering for authorization checks.

`barrins_api` owns Tamiyo Scroll domain data and per-user preferences, not
users — since the identity cutover (ADR-20) it no longer has a `users`
table or a `UserRole` ORM enum. The role of the caller comes from the
verified identity access token (`role` claim); this module only provides
the hierarchical ordering `require_role()` compares against.

Names mirror `apps/barrins_identity/app/models/user.py::UserRole`
(`user` < `moderator` < `ml_developer` < `admin`).
"""

import enum


class Role(enum.StrEnum):
    """Identity roles, ranked by increasing access level.

    Use `Role.<name>.level` for comparisons — never compare names directly.
    """

    user = "user"  # level 1
    moderator = "moderator"  # level 2
    ml_developer = "ml_developer"  # level 3
    admin = "admin"  # level 4

    @property
    def level(self) -> int:
        """Ordinal level of the role (1 = user, 4 = admin)."""
        return {
            Role.user: 1,
            Role.moderator: 2,
            Role.ml_developer: 3,
            Role.admin: 4,
        }[self]


def role_level(role: str | None) -> int:
    """Level of a role name from a token claim.

    An unknown or missing role is treated as the lowest level (`0`) rather
    than raising — an attacker cannot gain access by sending a garbage
    `role`, and a legitimately new role name simply fails closed until this
    map is updated.
    """
    try:
        return Role(role).level
    except ValueError:
        return 0
