"""Default ts_user_settings.data_shared to true for new accounts (S1)

Revision ID: b6e4d18a5f3c
Revises: a9f27e6c1b34
Create Date: 2026-07-30 00:00:00.000000

New accounts default to sharing (opt-out); receiving stays opt-in
(receive_shared_data still defaults false). This only changes the
column's default for rows inserted from now on — existing rows keep
whatever value they already have, never retroactively opted in.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b6e4d18a5f3c"
down_revision: str | Sequence[str] | None = "a9f27e6c1b34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "ts_user_settings", "data_shared", server_default="true"
    )


def downgrade() -> None:
    op.alter_column(
        "ts_user_settings", "data_shared", server_default="false"
    )
