"""Phase 7: Integration and polish - materialized views and performance.

Revision ID: 20241218_phase7
Revises: 20241218_phase5_6
Create Date: 2024-12-18 15:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20241218_phase7"
down_revision = "20241218_phase5_6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create materialized views and performance optimizations."""

    # Create materialized view for catalog summary
    op.execute("""
        CREATE MATERIALIZED VIEW dcs.catalog_capsule_summary AS
        SELECT
            c.id,
            c.urn,
            c.name,
            c.capsule_type,
            c.layer,
            c.description,

            -- Structural metadata (Dimension 2)
            COUNT(DISTINCT col.id) as column_count,
            COUNT(DISTINCT idx.id) as index_count,
            COUNT(DISTINCT cons.id) FILTER (WHERE cons.constraint_type = 'primary_key') as pk_count,
            COUNT(DISTINCT cons.id) FILTER (WHERE cons.constraint_type = 'foreign_key') as fk_count,

            -- Semantic metadata (Dimension 3)
            COUNT(DISTINCT cbt.business_term_id) as business_term_count,

            -- Quality expectations (Dimension 4)
            COUNT(DISTINCT qr.id) as quality_rule_count,
            COUNT(DISTINCT qr.id) FILTER (WHERE qr.is_enabled = TRUE) as enabled_quality_rule_count,
            AVG((cp.completeness_score + cp.validity_score + cp.uniqueness_score) / 3.0) as avg_column_quality_score,

            -- Policy metadata (Dimension 5)
            MAX(dp.sensitivity_level) as highest_sensitivity,
            bool_or(dp.requires_masking) as has_masking_rules,
            COUNT(DISTINCT mr.id) as masking_rule_count,

            -- Provenance (Dimension 6)
            COUNT(DISTINCT cv.id) as version_count,
            COUNT(DISTINCT tc.id) as transformation_code_count,

            -- Operational contracts (Dimension 7)
            MAX(cc.freshness_sla) as freshness_sla,
            MAX(cc.quality_score_sla) as quality_score_sla,
            MAX(cc.contract_status) as contract_status,

            -- Lineage
            COUNT(DISTINCT clu.source_id) as upstream_count,
            COUNT(DISTINCT cld.target_id) as downstream_count,

            -- Timestamps
            c.created_at,
            c.updated_at

        FROM dcs.capsules c
        LEFT JOIN dcs.columns col ON col.capsule_id = c.id
        LEFT JOIN dcs.capsule_indexes idx ON idx.capsule_id = c.id
        LEFT JOIN dcs.column_constraints cons ON cons.column_id = col.id
        LEFT JOIN dcs.capsule_business_terms cbt ON cbt.capsule_id = c.id
        LEFT JOIN dcs.quality_rules qr ON qr.capsule_id = c.id
        LEFT JOIN dcs.column_profiles cp ON cp.column_id = col.id
        LEFT JOIN dcs.data_policies dp ON dp.capsule_id = c.id
        LEFT JOIN dcs.masking_rules mr ON mr.column_id = col.id
        LEFT JOIN dcs.capsule_versions cv ON cv.capsule_id = c.id
        LEFT JOIN dcs.transformation_code tc ON tc.capsule_id = c.id
        LEFT JOIN dcs.capsule_contracts cc ON cc.capsule_id = c.id
        LEFT JOIN dcs.capsule_lineage clu ON clu.target_id = c.id
        LEFT JOIN dcs.capsule_lineage cld ON cld.source_id = c.id

        GROUP BY c.id, c.urn, c.name, c.capsule_type, c.layer, c.description, c.created_at, c.updated_at
    """)

    # Create unique index on the materialized view
    op.execute("""
        CREATE UNIQUE INDEX idx_catalog_capsule_summary_id
        ON dcs.catalog_capsule_summary(id)
    """)

    # Create additional indexes for common query patterns
    op.execute("""
        CREATE INDEX idx_catalog_capsule_summary_layer
        ON dcs.catalog_capsule_summary(layer)
    """)

    op.execute("""
        CREATE INDEX idx_catalog_capsule_summary_capsule_type
        ON dcs.catalog_capsule_summary(capsule_type)
    """)

    op.execute("""
        CREATE INDEX idx_catalog_capsule_summary_contract_status
        ON dcs.catalog_capsule_summary(contract_status)
    """)

    # Create materialized view for column-level summary
    op.execute("""
        CREATE MATERIALIZED VIEW dcs.catalog_column_summary AS
        SELECT
            col.id,
            col.urn,
            col.name,
            col.data_type,
            col.capsule_id,
            c.urn as capsule_urn,
            c.name as capsule_name,

            -- Constraints
            COUNT(DISTINCT cons.id) FILTER (WHERE cons.constraint_type = 'primary_key') as is_primary_key,
            COUNT(DISTINCT cons.id) FILTER (WHERE cons.constraint_type = 'foreign_key') as is_foreign_key,
            COUNT(DISTINCT cons.id) FILTER (WHERE cons.constraint_type = 'unique') as is_unique,
            COUNT(DISTINCT cons.id) FILTER (WHERE cons.constraint_type = 'not_null') as is_not_null,

            -- Business terms
            COUNT(DISTINCT cbt.business_term_id) as business_term_count,

            -- Quality
            (cp.completeness_score + cp.validity_score + cp.uniqueness_score) / 3.0 as overall_quality_score,
            cp.completeness_score,
            cp.validity_score,
            cp.uniqueness_score,
            cp.null_percentage,
            cp.unique_percentage,

            -- Policy
            MAX(dp.sensitivity_level) as sensitivity_level,
            bool_or(dp.requires_masking) as requires_masking,
            COUNT(DISTINCT mr.id) as masking_rule_count,

            -- Timestamps
            col.created_at,
            col.updated_at

        FROM dcs.columns col
        INNER JOIN dcs.capsules c ON c.id = col.capsule_id
        LEFT JOIN dcs.column_constraints cons ON cons.column_id = col.id
        LEFT JOIN dcs.column_business_terms cbt ON cbt.column_id = col.id
        LEFT JOIN dcs.column_profiles cp ON cp.column_id = col.id
        LEFT JOIN dcs.data_policies dp ON dp.column_id = col.id
        LEFT JOIN dcs.masking_rules mr ON mr.column_id = col.id

        GROUP BY col.id, col.urn, col.name, col.data_type, col.capsule_id,
                 c.urn, c.name, cp.completeness_score, cp.validity_score,
                 cp.uniqueness_score, cp.null_percentage, cp.unique_percentage,
                 col.created_at, col.updated_at
    """)

    # Create indexes on column summary
    op.execute("""
        CREATE UNIQUE INDEX idx_catalog_column_summary_id
        ON dcs.catalog_column_summary(id)
    """)

    op.execute("""
        CREATE INDEX idx_catalog_column_summary_capsule_id
        ON dcs.catalog_column_summary(capsule_id)
    """)

    op.execute("""
        CREATE INDEX idx_catalog_column_summary_data_type
        ON dcs.catalog_column_summary(data_type)
    """)

    # Add performance indexes on existing tables for common join patterns

    # Index for capsule lineage queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_capsule_lineage_composite
        ON dcs.capsule_lineage(source_id, target_id, edge_type)
    """)

    # Index for quality rule queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_quality_rules_enabled
        ON dcs.quality_rules(capsule_id, is_enabled)
    """)

    # Index for capsule version queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_capsule_versions_current
        ON dcs.capsule_versions(capsule_id, is_current)
    """)

    # Index for SLA incident queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sla_incidents_status
        ON dcs.sla_incidents(contract_id, incident_status, incident_severity)
    """)

    # Index for transformation code queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_transformation_code_git
        ON dcs.transformation_code(git_repository, git_commit_sha)
    """)


def downgrade() -> None:
    """Drop materialized views and performance optimizations."""

    # Drop performance indexes
    op.execute("DROP INDEX IF EXISTS dcs.idx_transformation_code_git")
    op.execute("DROP INDEX IF EXISTS dcs.idx_sla_incidents_status")
    op.execute("DROP INDEX IF EXISTS dcs.idx_capsule_versions_current")
    op.execute("DROP INDEX IF EXISTS dcs.idx_quality_rules_enabled")
    op.execute("DROP INDEX IF EXISTS dcs.idx_capsule_lineage_composite")

    # Drop column summary materialized view
    op.execute("DROP INDEX IF EXISTS dcs.idx_catalog_column_summary_data_type")
    op.execute("DROP INDEX IF EXISTS dcs.idx_catalog_column_summary_capsule_id")
    op.execute("DROP INDEX IF EXISTS dcs.idx_catalog_column_summary_id")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS dcs.catalog_column_summary")

    # Drop capsule summary materialized view
    op.execute("DROP INDEX IF EXISTS dcs.idx_catalog_capsule_summary_contract_status")
    op.execute("DROP INDEX IF EXISTS dcs.idx_catalog_capsule_summary_capsule_type")
    op.execute("DROP INDEX IF EXISTS dcs.idx_catalog_capsule_summary_layer")
    op.execute("DROP INDEX IF EXISTS dcs.idx_catalog_capsule_summary_id")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS dcs.catalog_capsule_summary")
