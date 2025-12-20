"""Phase 3: Add quality expectations (quality rules, column profiles)

Revision ID: 20241218_phase3
Revises: 20241218_phase2
Create Date: 2024-12-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20241218_phase3'
down_revision = '20241218_phase2'
branch_labels = None
depends_on = None


def get_schema():
    """Get schema name based on database type."""
    import os
    db_url = os.environ.get("DATABASE_URL", "")
    return None if "sqlite" in db_url else "dcs"


def upgrade() -> None:
    """Add Phase 3 quality expectations tables."""
    schema = get_schema()

    # 1. Create quality_rules table
    op.create_table(
        'quality_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  primary_key=True, server_default=sa.text('gen_random_uuid()') if schema else None),

        # Subject (one of these must be set)
        sa.Column('capsule_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=True),
        sa.Column('column_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=True),

        # Rule definition
        sa.Column('rule_name', sa.String(255), nullable=False),
        sa.Column('rule_type', sa.String(50), nullable=False),
        sa.Column('rule_category', sa.String(50), nullable=True),
        sa.Column('rule_config', postgresql.JSONB if schema else sa.Text,
                  nullable=False),

        # Thresholds
        sa.Column('threshold_value', sa.Numeric, nullable=True),
        sa.Column('threshold_operator', sa.String(20), nullable=True),
        sa.Column('threshold_percent', sa.Numeric, nullable=True),

        # Expected values
        sa.Column('expected_value', sa.Text, nullable=True),
        sa.Column('expected_range_min', sa.Numeric, nullable=True),
        sa.Column('expected_range_max', sa.Numeric, nullable=True),
        sa.Column('expected_pattern', sa.Text, nullable=True),

        # Severity
        sa.Column('severity', sa.String(20), nullable=False,
                  server_default='warning'),
        sa.Column('blocking', sa.Boolean, nullable=False,
                  server_default='false'),

        # Status
        sa.Column('is_enabled', sa.Boolean, nullable=False,
                  server_default='true'),

        # Metadata
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('meta', postgresql.JSONB if schema else sa.Text,
                  server_default='{}', nullable=False),

        # Audit
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),

        # Foreign keys
        sa.ForeignKeyConstraint(['capsule_id'],
                               [f'{schema}.capsules.id' if schema else 'capsules.id'],
                               ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['column_id'],
                               [f'{schema}.columns.id' if schema else 'columns.id'],
                               ondelete='CASCADE'),

        # Check constraints
        sa.CheckConstraint(
            "(capsule_id IS NOT NULL)::int + (column_id IS NOT NULL)::int = 1"
            if schema else
            "(CASE WHEN capsule_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN column_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name='quality_rules_has_subject'
        ),
        sa.CheckConstraint(
            "rule_type IN ('not_null', 'no_empty_strings', 'completeness_threshold', "
            "'value_in_set', 'pattern_match', 'format_valid', 'type_valid', 'range_check', 'length_check', "
            "'unique', 'unique_combination', 'duplicate_threshold', "
            "'referential_integrity', 'cross_field_validation', "
            "'freshness', 'recency_check', "
            "'distribution_check', 'outlier_detection', 'statistical_threshold', "
            "'custom_sql', 'custom_function')",
            name='rule_type_valid'
        ),
        sa.CheckConstraint(
            "rule_category IN ('completeness', 'validity', 'consistency', 'timeliness', "
            "'accuracy', 'uniqueness', 'distribution')",
            name='rule_category_valid'
        ),
        sa.CheckConstraint(
            "severity IN ('info', 'warning', 'error', 'critical')",
            name='severity_valid'
        ),

        schema=schema
    )

    # Indexes for quality_rules
    op.create_index('idx_quality_rules_capsule', 'quality_rules',
                    ['capsule_id'], schema=schema)
    op.create_index('idx_quality_rules_column', 'quality_rules',
                    ['column_id'], schema=schema)
    op.create_index('idx_quality_rules_type', 'quality_rules',
                    ['rule_type'], schema=schema)

    # 2. Create column_profiles table
    op.create_table(
        'column_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  primary_key=True, server_default=sa.text('gen_random_uuid()') if schema else None),

        # Subject
        sa.Column('column_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=False),

        # Basic statistics
        sa.Column('total_count', sa.BigInteger, nullable=True),
        sa.Column('null_count', sa.BigInteger, nullable=True),
        sa.Column('null_percentage', sa.Numeric(5, 2), nullable=True),
        sa.Column('distinct_count', sa.BigInteger, nullable=True),
        sa.Column('unique_percentage', sa.Numeric(5, 2), nullable=True),

        # For numeric columns
        sa.Column('min_value', sa.Numeric, nullable=True),
        sa.Column('max_value', sa.Numeric, nullable=True),
        sa.Column('mean_value', sa.Numeric, nullable=True),
        sa.Column('median_value', sa.Numeric, nullable=True),
        sa.Column('std_dev', sa.Numeric, nullable=True),
        sa.Column('variance', sa.Numeric, nullable=True),
        sa.Column('percentile_25', sa.Numeric, nullable=True),
        sa.Column('percentile_75', sa.Numeric, nullable=True),

        # For string columns
        sa.Column('min_length', sa.Integer, nullable=True),
        sa.Column('max_length', sa.Integer, nullable=True),
        sa.Column('avg_length', sa.Numeric, nullable=True),

        # For all columns
        sa.Column('most_common_values', postgresql.JSONB if schema else sa.Text,
                  nullable=True),
        sa.Column('value_distribution', postgresql.JSONB if schema else sa.Text,
                  nullable=True),
        sa.Column('detected_patterns', postgresql.JSONB if schema else sa.Text,
                  nullable=True),

        # Temporal patterns
        sa.Column('earliest_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('latest_timestamp', sa.DateTime(timezone=True), nullable=True),

        # Data quality indicators (0-100 scores)
        sa.Column('completeness_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('validity_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('uniqueness_score', sa.Numeric(5, 2), nullable=True),

        # Profiling metadata
        sa.Column('profiled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('profiled_by', sa.String(255), nullable=True),
        sa.Column('sample_size', sa.BigInteger, nullable=True),
        sa.Column('sample_percentage', sa.Numeric(5, 2), nullable=True),

        # Metadata
        sa.Column('meta', postgresql.JSONB if schema else sa.Text,
                  server_default='{}', nullable=False),

        # Audit
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),

        # Foreign keys
        sa.ForeignKeyConstraint(['column_id'],
                               [f'{schema}.columns.id' if schema else 'columns.id'],
                               ondelete='CASCADE'),

        schema=schema
    )

    # Indexes for column_profiles
    op.create_index('idx_column_profiles_column', 'column_profiles',
                    ['column_id'], schema=schema)
    op.create_index('idx_column_profiles_profiled_at', 'column_profiles',
                    ['profiled_at'], schema=schema)


def downgrade() -> None:
    """Remove Phase 3 quality expectations tables."""
    schema = get_schema()

    # Drop tables (in reverse order of creation)
    op.drop_table('column_profiles', schema=schema)
    op.drop_table('quality_rules', schema=schema)
