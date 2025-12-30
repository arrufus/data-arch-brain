"""airflow_column_lineage

Phase 6: Column-Level Lineage Integration

Revision ID: 20241229_airflow_column_lineage
Revises: 20241228_airflow_orchestration
Create Date: 2024-12-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20241229_airflow_column_lineage"
down_revision: Union[str, None] = "20241228_airflow_orchestration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add column-level lineage enhancements."""

    # ===================================================================
    # 1. Enhance Column Lineage Table (Phase 6)
    # ===================================================================
    # Rename existing columns to match Phase 6 schema
    op.alter_column(
        "column_lineage",
        "source_urn",
        new_column_name="source_column_urn",
        schema="dcs",
    )
    op.alter_column(
        "column_lineage",
        "target_urn",
        new_column_name="target_column_urn",
        schema="dcs",
    )
    op.alter_column(
        "column_lineage",
        "transformation_expr",
        new_column_name="transformation_logic",
        schema="dcs",
    )

    # Add new Phase 6 columns
    op.add_column(
        "column_lineage",
        sa.Column(
            "edge_type",
            sa.String(50),
            nullable=False,
            server_default="derives_from",
            comment="derives_from, same_as, transforms_to"
        ),
        schema="dcs",
    )
    op.add_column(
        "column_lineage",
        sa.Column(
            "confidence",
            sa.Numeric(3, 2),
            nullable=False,
            server_default="1.0",
            comment="0.0 to 1.0 confidence score"
        ),
        schema="dcs",
    )
    op.add_column(
        "column_lineage",
        sa.Column(
            "detected_by",
            sa.String(50),
            nullable=False,
            server_default="manual",
            comment="sql_parser, dbt_metadata, manual"
        ),
        schema="dcs",
    )
    op.add_column(
        "column_lineage",
        sa.Column(
            "detection_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb")
        ),
        schema="dcs",
    )
    op.add_column(
        "column_lineage",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now()
        ),
        schema="dcs",
    )

    # Drop old unique constraint and create new one with edge_type
    op.drop_constraint("uq_column_lineage_edge", "column_lineage", schema="dcs")
    op.create_unique_constraint(
        "uq_column_lineage_source_target_type",
        "column_lineage",
        ["source_column_urn", "target_column_urn", "edge_type"],
        schema="dcs",
    )

    # Add new indexes
    op.create_index(
        "idx_column_lineage_source_urn",
        "column_lineage",
        ["source_column_urn"],
        schema="dcs",
    )
    op.create_index(
        "idx_column_lineage_target_urn",
        "column_lineage",
        ["target_column_urn"],
        schema="dcs",
    )
    op.create_index(
        "idx_column_lineage_edge_type",
        "column_lineage",
        ["edge_type"],
        schema="dcs",
    )

    # ===================================================================
    # 2. Task-Column Edge Table (dcs schema)
    # ===================================================================
    op.create_table(
        "task_column_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        # Task reference
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_urn", sa.String(500), nullable=False),
        # Column reference
        sa.Column("column_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("column_urn", sa.String(500), nullable=False),
        # Edge metadata
        sa.Column("edge_type", sa.String(50), nullable=False, comment="reads, writes, transforms"),
        # Transformation details
        sa.Column("transformation_type", sa.String(50), nullable=True, comment="select, insert, update, aggregate, etc."),
        sa.Column("transformation_logic", sa.Text, nullable=True),
        sa.Column("operation", sa.String(50), nullable=True, comment="select, insert, update, aggregate, etc."),
        # Audit
        sa.Column("ingestion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # Constraints
        sa.ForeignKeyConstraint(["task_id"], ["dcs.pipeline_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["column_id"], ["dcs.columns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingestion_id"], ["dcs.ingestion_jobs.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("task_urn", "column_urn", "edge_type", name="uq_task_column_edge_task_column_type"),
        schema="dcs",
    )

    # Indexes for task_column_edges
    op.create_index(
        "idx_task_column_edges_task",
        "task_column_edges",
        ["task_id"],
        schema="dcs",
    )
    op.create_index(
        "idx_task_column_edges_column",
        "task_column_edges",
        ["column_id"],
        schema="dcs",
    )
    op.create_index(
        "idx_task_column_edges_task_urn",
        "task_column_edges",
        ["task_urn"],
        schema="dcs",
    )
    op.create_index(
        "idx_task_column_edges_column_urn",
        "task_column_edges",
        ["column_urn"],
        schema="dcs",
    )
    op.create_index(
        "idx_task_column_edges_edge_type",
        "task_column_edges",
        ["edge_type"],
        schema="dcs",
    )

    # ===================================================================
    # 3. Column Version Table (dcs schema)
    # ===================================================================
    op.create_table(
        "column_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        # Column reference
        sa.Column("column_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("column_urn", sa.String(500), nullable=False),
        # Version info
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        # Schema snapshot
        sa.Column("data_type", sa.String(100), nullable=False),
        sa.Column("is_nullable", sa.Boolean, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        # Change metadata
        sa.Column("change_type", sa.String(50), nullable=False, comment="created, modified, deleted, renamed"),
        sa.Column("change_reason", sa.String(500), nullable=True),
        sa.Column("breaking_change", sa.Boolean, server_default=sa.text("false"), nullable=False),
        # Audit
        sa.Column("changed_by", sa.String(255), nullable=True),
        sa.Column("ingestion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # Constraints
        sa.ForeignKeyConstraint(["column_id"], ["dcs.columns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingestion_id"], ["dcs.ingestion_jobs.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("column_id", "version", name="uq_column_version_column_version"),
        schema="dcs",
    )

    # Indexes for column_versions
    op.create_index(
        "idx_column_versions_column",
        "column_versions",
        ["column_id"],
        schema="dcs",
    )
    op.create_index(
        "idx_column_versions_valid_from",
        "column_versions",
        ["valid_from"],
        schema="dcs",
        postgresql_using="btree",
        postgresql_ops={"valid_from": "DESC"},
    )
    op.create_index(
        "idx_column_versions_breaking_change",
        "column_versions",
        ["breaking_change"],
        schema="dcs",
    )
    op.create_index(
        "idx_column_versions_change_type",
        "column_versions",
        ["change_type"],
        schema="dcs",
    )


def downgrade() -> None:
    """Revert column-level lineage enhancements."""

    # Drop new tables
    op.drop_table("column_versions", schema="dcs")
    op.drop_table("task_column_edges", schema="dcs")

    # Revert column_lineage changes
    # Drop new indexes
    op.drop_index("idx_column_lineage_edge_type", "column_lineage", schema="dcs")
    op.drop_index("idx_column_lineage_target_urn", "column_lineage", schema="dcs")
    op.drop_index("idx_column_lineage_source_urn", "column_lineage", schema="dcs")

    # Drop new unique constraint and restore old one
    op.drop_constraint("uq_column_lineage_source_target_type", "column_lineage", schema="dcs")
    op.create_unique_constraint(
        "uq_column_lineage_edge",
        "column_lineage",
        ["source_column_id", "target_column_id"],
        schema="dcs",
    )

    # Drop new columns
    op.drop_column("column_lineage", "updated_at", schema="dcs")
    op.drop_column("column_lineage", "detection_metadata", schema="dcs")
    op.drop_column("column_lineage", "detected_by", schema="dcs")
    op.drop_column("column_lineage", "confidence", schema="dcs")
    op.drop_column("column_lineage", "edge_type", schema="dcs")

    # Rename columns back
    op.alter_column(
        "column_lineage",
        "transformation_logic",
        new_column_name="transformation_expr",
        schema="dcs",
    )
    op.alter_column(
        "column_lineage",
        "target_column_urn",
        new_column_name="target_urn",
        schema="dcs",
    )
    op.alter_column(
        "column_lineage",
        "source_column_urn",
        new_column_name="source_urn",
        schema="dcs",
    )
