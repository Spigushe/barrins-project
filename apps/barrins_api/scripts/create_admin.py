"""Bootstrap script — creation of the first administrator account.

Usage
-----
    python scripts/create_admin.py --email admin@example.com
    python scripts/create_admin.py --email admin@example.com --display-name "Alice"

The password is always entered interactively via a masked prompt
(getpass). It is never accepted as a command-line argument, to avoid
it showing up in shell history or process logs.

This script is designed to be run **only once** after the initial
migration, in a controlled environment (server or CI/CD).
See docs/auth_roles/10_deploiement.md §10.4.

Exit codes
----------
    0 — success
    1 — error (email already taken, invalid password, DB error...)
"""

import argparse
import asyncio
import getpass
import sys

# Ensures the `app` package is importable when the script is run from
# the project root (python scripts/create_admin.py).
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.security import hash_password
from app.database.connection import AsyncSessionLocal
from app.models.user import User, UserRole
from app.schemas.auth import PASSWORD_PATTERN, PASSWORD_RULE


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Creates the first administrator account for the API.",
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
        "--display-name",
        default=None,
        metavar="NAME",
        help="Display name (optional).",
    )
    return parser.parse_args()


def _prompt_password() -> str:
    """Enters and confirms the password via a masked prompt.

    Validates complexity before returning the value.
    Raises SystemExit(1) if the confirmation doesn't match or if the
    complexity is insufficient.
    """
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


async def _create_admin(email: str, password: str, display_name: str | None) -> None:
    """Inserts the admin account into the DB. Idempotent: fails if the email exists."""
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            print(
                f"ERROR: an account already exists for '{email}'.",
                file=sys.stderr,
            )
            sys.exit(1)

        admin = User(
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.admin,
            is_active=True,
            is_verified=True,
            display_name=display_name,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)

    print(f"✓ Admin account created: {email} (id={admin.id})")


def main() -> None:
    args = _parse_args()
    password = _prompt_password()
    asyncio.run(_create_admin(args.email, password, args.display_name))


if __name__ == "__main__":
    main()
