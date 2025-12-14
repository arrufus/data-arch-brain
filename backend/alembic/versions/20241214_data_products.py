"""Add data products and capsule associations tables.

Revision ID: 20241214_data_products
Revises: 20251211_2103_3aa00f7cbf3a_add_timestamp_columns_to_ingestion_jobs
Create Date: 2024-12-14 10:00:00.000000

Implements:
- data_products table (DataProduct node from property graph G1)
- capsule_data_products table (PART_OF edge from property graph G1)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "20241214_data_products"
down_revision: Union[str, None] = "20251211_2103_3aa00f7cbf3a_add_timestamp_columns_to_ingestion_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Schema name
SCHEMA = "dab"


def upgrade() -> None:
    """Create data_products and capsule_data_products tables."""

    # Create data_products table
    op.create_table(
        "data_products",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), server_default="draft", nullable=False),
        # Foreign keys
        sa.Column("domain_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        # SLO definitions
        sa.Column(
            "slo_freshness_hours",
            sa.Integer(),
            nullable=True,
            comment="Max hours since last data update",
        ),
        sa.Column(
            "slo_availability_percent",
            sa.Float(),
            nullable=True,
            comment="Target availability (e.g., 99.9)",
        ),
        sa.Column(
            "slo_quality_threshold",
            sa.Float(),
            nullable=True,
            comment="Min conformance score (0.0 to 1.0)",
        ),
        # Contract definitions
        sa.Column(
            "output_port_schema",
            postgresql.JSONB(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "input_sources",
            postgresql.JSONB(),
            server_default="[]",
            nullable=False,
        ),
        # Metadata
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("tags", postgresql.JSONB(), server_default="[]", nullable=False),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["domain_id"], [f"{SCHEMA}.domains.id"]),
        sa.ForeignKeyConstraint(["owner_id"], [f"{SCHEMA}.owners.id"]),
        schema=SCHEMA,
    )

    # Create indexes for data_products
    op.create_index(
        "idx_data_products_name",
        "data_products",
        ["name"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_data_products_status",
        "data_products",
        ["status"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_data_products_domain",
        "data_products",
        ["domain_id"],
        schema=SCHEMA,
    )

    # Create capsule_data_products junction table (PART_OF edge)
    op.create_table(
        "capsule_data_products",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "capsule_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "data_product_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("role", sa.String(50), server_default="member", nullable=False),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["capsule_id"],
            [f"{SCHEMA}.capsules.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["data_product_id"],
            [f"{SCHEMA}.data_products.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("capsule_id", "data_product_id", name="uq_capsule_data_product"),
        schema=SCHEMA,
    )

    # Create indexes for capsule_data_products
    op.create_index(
        "idx_cdp_capsule",
        "capsule_data_products",
        ["capsule_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_cdp_data_product",
        "capsule_data_products",
        ["data_product_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_cdp_role",
        "capsule_data_products",
        ["role"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Remove data_products and capsule_data_products tables."""

    # Drop indexes
    op.drop_index("idx_cdp_role", table_name="capsule_data_products", schema=SCHEMA)
    op.drop_index("idx_cdp_data_product", table_name="capsule_data_products", schema=SCHEMA)
    op.drop_index("idx_cdp_capsule", table_name="capsule_data_products", schema=SCHEMA)

    # Drop capsule_data_products table
    op.drop_table("capsule_data_products", schema=SCHEMA)

    # Drop data_products indexes
    op.drop_index("idx_data_products_domain", table_name="data_products", schema=SCHEMA)
    op.drop_index("idx_data_products_status", table_name="data_products", schema=SCHEMA)
    op.drop_index("idx_data_products_name", table_name="data_products", schema=SCHEMA)

    # Drop data_products table
    op.drop_table("data_products", schema=SCHEMA)
