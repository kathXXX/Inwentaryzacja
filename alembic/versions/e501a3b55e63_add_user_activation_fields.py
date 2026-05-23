"""add user activation fields

Revision ID: e501a3b55e63
Revises: ba82881da590
Create Date: 2026-05-23 17:57:02.540910

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e501a3b55e63'
down_revision: Union[str, Sequence[str], None] = 'ba82881da590'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "users",
        sa.Column("activation_token", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("activation_token_expires_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "activation_token_expires_at")
    op.drop_column("users", "activation_token")
    op.drop_column("users", "is_active")
