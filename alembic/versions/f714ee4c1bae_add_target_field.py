"""add target field

Revision ID: f714ee4c1bae
Revises: 13f6cc891629
Create Date: 2025-10-26 15:25:45.944126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f714ee4c1bae'
down_revision: Union[str, Sequence[str], None] = '13f6cc891629'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
    pass
