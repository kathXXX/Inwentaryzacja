"""add login codes

Revision ID: f3c7d8e9a102
Revises: e501a3b55e63
Create Date: 2026-05-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3c7d8e9a102"
down_revision: Union[str, Sequence[str], None] = "e501a3b55e63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "login_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("challenge_id", sa.String(length=80), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_login_codes_id", "login_codes", ["id"], unique=False)
    op.create_index("ix_login_codes_challenge_id", "login_codes", ["challenge_id"], unique=True)
    op.create_index("ix_login_codes_user_id", "login_codes", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_login_codes_user_id", table_name="login_codes")
    op.drop_index("ix_login_codes_challenge_id", table_name="login_codes")
    op.drop_index("ix_login_codes_id", table_name="login_codes")
    op.drop_table("login_codes")
