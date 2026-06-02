"""add locations inventory due dates

Revision ID: c4d5e6f7a890
Revises: f3c7d8e9a102
Create Date: 2026-06-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a890"
down_revision: Union[str, Sequence[str], None] = "f3c7d8e9a102"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_locations_id", "locations", ["id"], unique=False)
    op.create_index("ix_locations_name", "locations", ["name"], unique=True)

    op.add_column("items", sa.Column("location_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_items_location_id_locations",
        "items",
        "locations",
        ["location_id"],
        ["id"],
    )

    op.execute(
        """
        INSERT INTO locations (name, created_at)
        SELECT DISTINCT lokalizacja, CURRENT_TIMESTAMP
        FROM items
        WHERE lokalizacja IS NOT NULL AND lokalizacja <> ''
        """
    )
    op.execute(
        """
        UPDATE items
        SET location_id = (
            SELECT locations.id
            FROM locations
            WHERE locations.name = items.lokalizacja
        )
        WHERE location_id IS NULL
        """
    )

    op.add_column("loans", sa.Column("due_at", sa.DateTime(), nullable=True))
    op.add_column("loans", sa.Column("due_reminder_sent_at", sa.DateTime(), nullable=True))
    op.add_column("loan_history", sa.Column("due_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("loan_history", "due_at")
    op.drop_column("loans", "due_reminder_sent_at")
    op.drop_column("loans", "due_at")
    op.drop_constraint("fk_items_location_id_locations", "items", type_="foreignkey")
    op.drop_column("items", "location_id")
    op.drop_index("ix_locations_name", table_name="locations")
    op.drop_index("ix_locations_id", table_name="locations")
    op.drop_table("locations")
