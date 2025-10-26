"""add ml_models table

Revision ID: 2b7e3c8a9f4d
Revises: 13f6cc891629
Create Date: 2025-10-26 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2b7e3c8a9f4d"
down_revision: Union[str, Sequence[str], None] = "13f6cc891629"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ml_models",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("model_type", sa.String(length=20), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("endpoint", sa.Text(), nullable=True),
        sa.Column("threshold_ml", sa.Float(), nullable=True),
        sa.Column("features", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="validated"),
        sa.Column("hash", sa.String(length=64), nullable=True),
        sa.Column("size_mb", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_ml_models_name", "ml_models", ["name"], unique=False)
    op.create_index("ix_ml_models_status", "ml_models", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ml_models_status", table_name="ml_models")
    op.drop_index("ix_ml_models_name", table_name="ml_models")
    op.drop_table("ml_models")
