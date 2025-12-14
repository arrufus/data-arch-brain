"""Add tag association tables (TAGGED_WITH edges) for property graph Phase 2.

Revision ID: 20241216_tag_edges
Revises: 20241214_data_products
Create Date: 2024-12-16

This migration implements Phase 2 of the property graph specification:
- Adds sensitivity_level column to tags table (G4 gap)
- Creates capsule_tags junction table (TAGGED_WITH edges)
- Creates column_tags junction table (TAGGED_WITH edges)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20241216_tag_edges"
down_revision: Union[str, None] = "20241214_data_products"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "dab"


def upgrade() -> None:
    """Add tag association tables and sensitivity_level column."""
    
    # Add sensitivity_level column to tags table (G4 gap)
    op.add_column(
        "tags",
        sa.Column(
            "sensitivity_level",
            sa.String(50),
            nullable=True,
            comment="Data sensitivity level: public, internal, confidential, restricted",
        ),
        schema=SCHEMA,
    )
    
    # Create capsule_tags junction table (TAGGED_WITH edges from Capsule to Tag)
    op.create_table(
        "capsule_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "capsule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.capsules.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "tag_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tags.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("added_by", sa.String(255), nullable=True, comment="User who added the tag"),
        sa.Column("added_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("meta", postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.UniqueConstraint("capsule_id", "tag_id", name="uq_capsule_tag"),
        schema=SCHEMA,
        comment="Junction table for Capsule-Tag associations (TAGGED_WITH edges)",
    )
    
    # Create column_tags junction table (TAGGED_WITH edges from Column to Tag)
    op.create_table(
        "column_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "column_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.columns.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "tag_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tags.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("added_by", sa.String(255), nullable=True, comment="User who added the tag"),
        sa.Column("added_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("meta", postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.UniqueConstraint("column_id", "tag_id", name="uq_column_tag"),
        schema=SCHEMA,
        comment="Junction table for Column-Tag associations (TAGGED_WITH edges)",
    )
    
    # Create indexes for efficient queries
    op.create_index(
        "ix_capsule_tags_composite",
        "capsule_tags",
        ["capsule_id", "tag_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_column_tags_composite",
        "column_tags",
        ["column_id", "tag_id"],
        schema=SCHEMA,
    )
    
    # Add index for sensitivity_level filtering
    op.create_index(
        "ix_tags_sensitivity_level",
        "tags",
        ["sensitivity_level"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Remove tag association tables and sensitivity_level column."""
    
    # Drop indexes
    op.drop_index("ix_tags_sensitivity_level", table_name="tags", schema=SCHEMA)
    op.drop_index("ix_column_tags_composite", table_name="column_tags", schema=SCHEMA)
    op.drop_index("ix_capsule_tags_composite", table_name="capsule_tags", schema=SCHEMA)
    
    # Drop junction tables
    op.drop_table("column_tags", schema=SCHEMA)
    op.drop_table("capsule_tags", schema=SCHEMA)
    
    # Drop sensitivity_level column
    op.drop_column("tags", "sensitivity_level", schema=SCHEMA)
