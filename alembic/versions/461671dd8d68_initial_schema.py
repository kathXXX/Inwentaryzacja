"""initial schema

Revision ID: 461671dd8d68
Revises:
Create Date: 2026-05-05 18:35:41.234665

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "461671dd8d68"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role_enum = sa.Enum(
    "student",
    "nauczyciel",
    "administrator",
    name="userrole",
)

item_status_enum = sa.Enum(
    "dostepny",
    "wypozyczony",
    "zarezerwowany",
    name="itemstatus",
)


def upgrade() -> None:
    """Create the full application schema."""
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nazwa", sa.String(length=100), nullable=False),
        sa.Column("kategoria", sa.String(length=100), nullable=False),
        sa.Column("lokalizacja", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_items_id", "items", ["id"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("field_of_study", sa.String(length=150), nullable=True),
        sa.Column("student_index", sa.String(length=30), nullable=True),
        sa.Column("department", sa.String(length=150), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)

    op.create_table(
        "loan_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("borrowed_at", sa.DateTime(), nullable=False),
        sa.Column("returned_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("returned_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["returned_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_loan_history_id", "loan_history", ["id"], unique=False)

    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("status", item_status_enum, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("item_id"),
    )
    op.create_index("ix_loans_id", "loans", ["id"], unique=False)


def downgrade() -> None:
    """Drop the full application schema."""
    op.drop_index("ix_loans_id", table_name="loans")
    op.drop_table("loans")

    op.drop_index("ix_loan_history_id", table_name="loan_history")
    op.drop_table("loan_history")

    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_items_id", table_name="items")
    op.drop_table("items")
