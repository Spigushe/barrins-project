"""Bootstrap script — creation of the first administrator account.

Usage
-----
    python scripts/create_admin.py --email admin@example.com --username admin
    python scripts/create_admin.py --email admin@example.com --username admin \
        --display-name "Alice"

The password is always entered interactively via a masked prompt
(getpass) — never accepted as a command-line argument.

This script is designed to be run **only once** after the initial
migration, in a controlled environment (server or CI/CD).

Exit codes
----------
    0 — success
    1 — error (email already taken, invalid password, DB error...)
"""

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import or_, select

from app.core.security import hash_password
from app.database.connection import AsyncSessionLocal
from app.models.user import User, UserRole
from app.schemas.auth import (
    PASSWORD_PATTERN,
    PASSWORD_RULE,
    USERNAME_PATTERN,
    USERNAME_RULE,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Creates the first administrator account for barrins-identity.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "The password is entered interactively — never as an argument.\n"
            "Run this script only once after the initial migration."
        ),
    )
    parser.add_argument(
        "--email",
        required=True,
        metavar="EMAIL",
        help="Email address of the administrator account.",
    )
    parser.add_argument(
        "--username",
        required=True,
        metavar="NAME",
        help=f"Unique handle for the administrator account. {USERNAME_RULE}",
    )
    parser.add_argument(
        "--display-name",
        default=None,
        metavar="NAME",
        help="Display name (optional).",
    )
    return parser.parse_args()


def _prompt_password() -> str:
    """Enters and confirms the password via a masked prompt."""
    print(f"Rule: {PASSWORD_RULE}")
    password = getpass.getpass("Admin password: ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        print("ERROR: passwords do not match.", file=sys.stderr)
        sys.exit(1)

    if not PASSWORD_PATTERN.fullmatch(password):
        print(f"ERROR: {PASSWORD_RULE}", file=sys.stderr)
        sys.exit(1)

    return password


async def _create_admin(
    email: str, username: str, password: str, display_name: str | None
) -> None:
    """Inserts the admin account into the DB. Fails if the email or username exists."""
    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(User).where(or_(User.email == email, User.username == username))
        )
        for row in existing.scalars():
            field = "email" if row.email == email else "username"
            value = email if field == "email" else username
            print(
                f"ERROR: an account already exists with that {field} ('{value}').",
                file=sys.stderr,
            )
            sys.exit(1)

        admin = User(
            email=email,
            username=username,
            hashed_password=hash_password(password),
            role=UserRole.admin,
            is_active=True,
            is_verified=True,
            display_name=display_name,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)

    print(f"Admin account created: {email} (username={username}, id={admin.id})")


def main() -> None:
    args = _parse_args()
    if not USERNAME_PATTERN.fullmatch(args.username):
        print(f"ERROR: {USERNAME_RULE}", file=sys.stderr)
        sys.exit(1)
    password = _prompt_password()
    asyncio.run(_create_admin(args.email, args.username, password, args.display_name))


if __name__ == "__main__":
    main()
