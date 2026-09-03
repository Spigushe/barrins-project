"""Bootstrap script — create (or rotate) a machine-to-machine service account.

Usage
-----
    python scripts/create_service_account.py \
        --client-id sa_local_dev_directory \
        --scope identity:users:read \
        --description "barrins_api user-directory lookups (local dev)"

Unlike ``create_admin.py`` this is safe to re-run: an existing account
with the same ``--client-id`` has its secret **rotated** (and its scopes /
active flag reset to the requested set), so a dev launcher can call it on
every start and always get working credentials. The plaintext secret is
printed once, on stdout, as two ``KEY=value`` lines a caller can parse:

    CLIENT_ID=sa_local_dev_directory
    CLIENT_SECRET=<generated>

Everything else (the "created" / "rotated" notice, errors) goes to stderr.

Refuses to run when ``ENVIRONMENT=production`` unless ``--force`` is given:
real service-account secrets there are provisioned deliberately, never
rotated by a helper script.

Exit codes
----------
    0 — success
    1 — error (production without --force, empty scope, DB error…)
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.config import settings
from app.core.security import (
    generate_client_id,
    generate_client_secret,
    hash_password,
)
from app.database.connection import AsyncSessionLocal
from app.models.service_account import ServiceAccount

_DEFAULT_SCOPE = "identity:users:read"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create or rotate a service account for machine-to-machine auth "
            "(POST /api/v1/service-token). Safe to re-run."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Re-running with an existing --client-id rotates that account's "
            "secret and resets its scopes. CLIENT_ID / CLIENT_SECRET are "
            "printed to stdout; notices go to stderr."
        ),
    )
    parser.add_argument(
        "--client-id",
        default=None,
        metavar="ID",
        help=(
            "Stable client_id to create or rotate. Omit to mint a fresh "
            "random one (sa_<hex>) — but then a re-run cannot find it again."
        ),
    )
    parser.add_argument(
        "--scope",
        action="append",
        dest="scopes",
        metavar="SCOPE",
        help=(
            f"Grant this scope (repeatable). Default: {_DEFAULT_SCOPE} — the "
            "scope barrins_api's user-directory lookup needs."
        ),
    )
    parser.add_argument(
        "--description",
        default="local dev service account",
        metavar="TEXT",
        help="Human description stored on the account.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow running when ENVIRONMENT=production.",
    )
    return parser.parse_args()


async def _upsert(
    client_id: str | None, scopes: list[str], description: str
) -> tuple[str, str]:
    """Create the account, or rotate an existing one's secret.

    Returns ``(client_id, plaintext_secret)``.
    """
    secret = generate_client_secret()
    hashed = hash_password(secret)

    async with AsyncSessionLocal() as session:
        account: ServiceAccount | None = None
        if client_id is not None:
            account = (
                await session.execute(
                    select(ServiceAccount).where(ServiceAccount.client_id == client_id)
                )
            ).scalar_one_or_none()

        if account is None:
            resolved_id = client_id or generate_client_id()
            session.add(
                ServiceAccount(
                    client_id=resolved_id,
                    hashed_client_secret=hashed,
                    description=description,
                    scopes=scopes,
                )
            )
            action = "created"
        else:
            resolved_id = account.client_id
            account.hashed_client_secret = hashed
            account.description = description
            account.scopes = scopes
            account.is_active = True
            # Bump token_version so tokens minted from the previous secret
            # stop verifying (same mechanism as a revoke).
            account.token_version += 1
            action = "rotated"

        await session.commit()

    print(f"service account {action}: {resolved_id} scopes={scopes}", file=sys.stderr)
    return resolved_id, secret


def main() -> None:
    args = _parse_args()

    if settings.base.environment == "production" and not args.force:
        print(
            "ERROR: refusing to run with ENVIRONMENT=production "
            "(pass --force if you really mean it).",
            file=sys.stderr,
        )
        sys.exit(1)

    scopes = [s.strip() for s in (args.scopes or [_DEFAULT_SCOPE]) if s.strip()]
    if not scopes:
        print("ERROR: at least one non-empty --scope is required.", file=sys.stderr)
        sys.exit(1)

    client_id, secret = asyncio.run(_upsert(args.client_id, scopes, args.description))
    print(f"CLIENT_ID={client_id}")
    print(f"CLIENT_SECRET={secret}")


if __name__ == "__main__":
    main()
