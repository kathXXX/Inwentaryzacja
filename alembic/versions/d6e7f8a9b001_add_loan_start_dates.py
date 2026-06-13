"""add loan start dates

Revision ID: d6e7f8a9b001
Revises: c4d5e6f7a890
Create Date: 2026-06-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d6e7f8a9b001"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a890"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("loans", sa.Column("starts_at", sa.DateTime(), nullable=True))
    op.add_column("loan_history", sa.Column("starts_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE loan_history SET starts_at = borrowed_at WHERE starts_at IS NULL")


def downgrade() -> None:
    op.drop_column("loan_history", "starts_at")
    op.drop_column("loans", "starts_at")
