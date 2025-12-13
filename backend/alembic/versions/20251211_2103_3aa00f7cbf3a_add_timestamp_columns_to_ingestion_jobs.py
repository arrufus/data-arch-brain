"""add_timestamp_columns_to_ingestion_jobs

Revision ID: 3aa00f7cbf3a
Revises: 0001
Create Date: 2025-12-11 21:03:42.854875+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3aa00f7cbf3a"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Schema name
SCHEMA = "dab"


def upgrade() -> None:
    # Add missing created_at and updated_at columns to ingestion_jobs table
    op.add_column(
        "ingestion_jobs",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "ingestion_jobs",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("ingestion_jobs", "updated_at", schema=SCHEMA)
    op.drop_column("ingestion_jobs", "created_at", schema=SCHEMA)
