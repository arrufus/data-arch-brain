"""Initial schema for Data Architecture Brain.

Revision ID: 0001
Revises:
Create Date: 2024-12-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Schema name
SCHEMA = "dab"


def upgrade() -> None:
    # Create schema
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    # Create source_systems table
    op.create_table(
        "source_systems",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("connection_info", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema=SCHEMA,
    )

    # Create owners table
    op.create_table(
        "owners",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner_type", sa.String(50), server_default="team", nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("slack_channel", sa.String(100), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    # Create domains table
    op.create_table(
        "domains",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.ForeignKeyConstraint(["parent_id"], [f"{SCHEMA}.domains.id"]),
        sa.ForeignKeyConstraint(["owner_id"], [f"{SCHEMA}.owners.id"]),
        schema=SCHEMA,
    )

    # Create ingestion_jobs table
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), server_default="running", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stats", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("config", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    # Create capsules table
    op.create_table(
        "capsules",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("urn", sa.String(500), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("capsule_type", sa.String(50), nullable=False),
        sa.Column("source_system_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("database_name", sa.String(255), nullable=True),
        sa.Column("schema_name", sa.String(255), nullable=True),
        sa.Column("domain_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("layer", sa.String(50), nullable=True),
        sa.Column("materialization", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("tags", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("has_tests", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("test_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("doc_coverage", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("ingestion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("urn"),
        sa.ForeignKeyConstraint(["source_system_id"], [f"{SCHEMA}.source_systems.id"]),
        sa.ForeignKeyConstraint(["domain_id"], [f"{SCHEMA}.domains.id"]),
        sa.ForeignKeyConstraint(["owner_id"], [f"{SCHEMA}.owners.id"]),
        sa.ForeignKeyConstraint(["ingestion_id"], [f"{SCHEMA}.ingestion_jobs.id"]),
        schema=SCHEMA,
    )

    # Create columns table
    op.create_table(
        "columns",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("urn", sa.String(500), nullable=False),
        sa.Column("capsule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("data_type", sa.String(100), nullable=True),
        sa.Column("ordinal_position", sa.Integer(), nullable=True),
        sa.Column("is_nullable", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("semantic_type", sa.String(50), nullable=True),
        sa.Column("pii_type", sa.String(50), nullable=True),
        sa.Column("pii_detected_by", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("tags", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("stats", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("has_tests", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("test_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("urn"),
        sa.ForeignKeyConstraint(["capsule_id"], [f"{SCHEMA}.capsules.id"], ondelete="CASCADE"),
        schema=SCHEMA,
    )

    # Create capsule_lineage table
    op.create_table(
        "capsule_lineage",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_urn", sa.String(500), nullable=False),
        sa.Column("target_urn", sa.String(500), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_type", sa.String(50), server_default="flows_to", nullable=False),
        sa.Column("transformation", sa.String(50), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ingestion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_id"], [f"{SCHEMA}.capsules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], [f"{SCHEMA}.capsules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingestion_id"], [f"{SCHEMA}.ingestion_jobs.id"]),
        sa.UniqueConstraint("source_id", "target_id", "edge_type", name="uq_capsule_lineage_edge"),
        schema=SCHEMA,
    )

    # Create column_lineage table
    op.create_table(
        "column_lineage",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_urn", sa.String(500), nullable=False),
        sa.Column("target_urn", sa.String(500), nullable=False),
        sa.Column("source_column_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_column_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transformation_type", sa.String(50), nullable=True),
        sa.Column("transformation_expr", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ingestion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_column_id"], [f"{SCHEMA}.columns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_column_id"], [f"{SCHEMA}.columns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingestion_id"], [f"{SCHEMA}.ingestion_jobs.id"]),
        sa.UniqueConstraint("source_column_id", "target_column_id", name="uq_column_lineage_edge"),
        schema=SCHEMA,
    )

    # Create rules table
    op.create_table(
        "rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("rule_id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(20), server_default="warning", nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("rule_set", sa.String(50), nullable=True),
        sa.Column("scope", sa.String(50), nullable=False),
        sa.Column("definition", postgresql.JSONB(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id"),
        schema=SCHEMA,
    )

    # Create tags table
    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "category", name="uq_tag_name_category"),
        schema=SCHEMA,
    )

    # Create violations table
    op.create_table(
        "violations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("capsule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("column_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ingestion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["rule_id"], [f"{SCHEMA}.rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["capsule_id"], [f"{SCHEMA}.capsules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["column_id"], [f"{SCHEMA}.columns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingestion_id"], [f"{SCHEMA}.ingestion_jobs.id"]),
        schema=SCHEMA,
    )

    # Create indexes
    op.create_index("idx_capsules_urn", "capsules", ["urn"], unique=True, schema=SCHEMA)
    op.create_index("idx_capsules_layer", "capsules", ["layer"], schema=SCHEMA)
    op.create_index("idx_capsules_type", "capsules", ["capsule_type"], schema=SCHEMA)
    op.create_index("idx_capsules_domain", "capsules", ["domain_id"], schema=SCHEMA)
    op.create_index("idx_capsules_tags", "capsules", ["tags"], schema=SCHEMA, postgresql_using="gin")

    op.create_index("idx_columns_urn", "columns", ["urn"], unique=True, schema=SCHEMA)
    op.create_index("idx_columns_capsule", "columns", ["capsule_id"], schema=SCHEMA)
    op.create_index("idx_columns_semantic_type", "columns", ["semantic_type"], schema=SCHEMA)
    op.create_index("idx_columns_pii_type", "columns", ["pii_type"], schema=SCHEMA)

    op.create_index("idx_capsule_lineage_source", "capsule_lineage", ["source_id"], schema=SCHEMA)
    op.create_index("idx_capsule_lineage_target", "capsule_lineage", ["target_id"], schema=SCHEMA)

    op.create_index("idx_column_lineage_source", "column_lineage", ["source_column_id"], schema=SCHEMA)
    op.create_index("idx_column_lineage_target", "column_lineage", ["target_column_id"], schema=SCHEMA)

    op.create_index("idx_rules_category", "rules", ["category"], schema=SCHEMA)
    op.create_index("idx_rules_rule_set", "rules", ["rule_set"], schema=SCHEMA)
    op.create_index("idx_rules_enabled", "rules", ["enabled"], schema=SCHEMA)

    op.create_index("idx_violations_capsule", "violations", ["capsule_id"], schema=SCHEMA)
    op.create_index("idx_violations_rule", "violations", ["rule_id"], schema=SCHEMA)
    op.create_index("idx_violations_severity", "violations", ["severity"], schema=SCHEMA)
    op.create_index("idx_violations_status", "violations", ["status"], schema=SCHEMA)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("violations", schema=SCHEMA)
    op.drop_table("tags", schema=SCHEMA)
    op.drop_table("rules", schema=SCHEMA)
    op.drop_table("column_lineage", schema=SCHEMA)
    op.drop_table("capsule_lineage", schema=SCHEMA)
    op.drop_table("columns", schema=SCHEMA)
    op.drop_table("capsules", schema=SCHEMA)
    op.drop_table("ingestion_jobs", schema=SCHEMA)
    op.drop_table("domains", schema=SCHEMA)
    op.drop_table("owners", schema=SCHEMA)
    op.drop_table("source_systems", schema=SCHEMA)

    # Drop schema
    op.execute(f"DROP SCHEMA {SCHEMA}")
