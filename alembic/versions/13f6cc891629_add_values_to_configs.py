"""add values to configs

Revision ID: 13f6cc891629
Revises: d2450047169b
Create Date: 2025-10-26 02:46:25.839877

"""

from datetime import datetime
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import column, table
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "13f6cc891629"
down_revision: Union[str, Sequence[str], None] = "d2450047169b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Define the table structure for data insertion
    notification_channel_configs = table(
        "notification_channel_configs",
        column("id", PGUUID),
        sa.Column(
            "channel",
            postgresql.ENUM("EMAIL", "TELEGRAM", name="notificationchannel"),
        ),
        column("enabled", sa.Boolean),
        column("config", JSON),
        column("max_retries", sa.Integer),
        column("retry_delay_seconds", sa.Integer),
        column("rate_limit_per_minute", sa.Integer),
        column("description", sa.String),
        column("total_sent", sa.Integer),
        column("total_failed", sa.Integer),
        column("last_used_at", sa.DateTime),
        column("created_at", sa.DateTime),
        column("updated_at", sa.DateTime),
    )

    # Insert TELEGRAM channel config
    op.execute(
        notification_channel_configs.insert().values(
            id=uuid4(),
            channel="TELEGRAM",  # Use uppercase string directly
            enabled=True,
            config={"parse_mode": "HTML"},
            max_retries=3,
            retry_delay_seconds=60,
            rate_limit_per_minute=30,
            description="Telegram notification channel",
            total_sent=0,
            total_failed=0,
            last_used_at=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )

    # Insert EMAIL channel config
    op.execute(
        notification_channel_configs.insert().values(
            id=uuid4(),
            channel="EMAIL",  # Use uppercase string directly
            enabled=True,
            config={"smtp_host": "smtp.gmail.com", "smtp_port": 587},
            max_retries=3,
            retry_delay_seconds=60,
            rate_limit_per_minute=60,
            description="Email notification channel",
            total_sent=0,
            total_failed=0,
            last_used_at=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )


def downgrade() -> None:
    """Remove default channel configurations."""
    op.execute(
        "DELETE FROM notification_channel_configs WHERE channel IN ('TELEGRAM', 'EMAIL')"
    )
