"""add item qr code

Revision ID: 9f0e7a2c4b6d
Revises: 461671dd8d68
Create Date: 2026-05-10 00:00:00.000000

"""
from typing import Sequence, Union

import secrets

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f0e7a2c4b6d"
down_revision: Union[str, Sequence[str], None] = "461671dd8d68"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _generate_qr_code() -> str:
    return secrets.token_urlsafe(18)


def upgrade() -> None:
    with op.batch_alter_table("items") as batch_op:
        batch_op.add_column(sa.Column("qr_code", sa.String(length=64), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id FROM items WHERE qr_code IS NULL")).fetchall()
    used_codes = {
        row[0]
        for row in bind.execute(
            sa.text("SELECT qr_code FROM items WHERE qr_code IS NOT NULL")
        ).fetchall()
    }

    for row in rows:
        item_id = row[0]
        qr_code = _generate_qr_code()
        while qr_code in used_codes:
            qr_code = _generate_qr_code()
        used_codes.add(qr_code)

        bind.execute(
            sa.text("UPDATE items SET qr_code = :qr_code WHERE id = :item_id"),
            {"qr_code": qr_code, "item_id": item_id},
        )

    with op.batch_alter_table("items") as batch_op:
        batch_op.alter_column(
            "qr_code",
            existing_type=sa.String(length=64),
            nullable=False,
        )
        batch_op.create_index("ix_items_qr_code", ["qr_code"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("items") as batch_op:
        batch_op.drop_index("ix_items_qr_code")
        batch_op.drop_column("qr_code")
