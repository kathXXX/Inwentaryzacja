"""add qr_code to items

Revision ID: ba82881da590
Revises: 9f0e7a2c4b6d
Create Date: 2026-05-13 22:05:13.754131

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba82881da590'
down_revision: Union[str, Sequence[str], None] = '9f0e7a2c4b6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    pass


def downgrade():
    pass
