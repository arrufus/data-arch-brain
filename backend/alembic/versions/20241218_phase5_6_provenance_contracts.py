"""Phase 5-6: Add provenance enhancements and operational contracts

Revision ID: 20241218_phase5_6
Revises: 20241218_phase4
Create Date: 2024-12-18 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20241218_phase5_6'
down_revision = '20241218_phase4'
branch_labels = None
depends_on = None


def get_schema():
    """Get schema name based on database type."""
    import os
    db_url = os.environ.get("DATABASE_URL", "")
    return None if "sqlite" in db_url else "dcs"


def upgrade() -> None:
    """Add Phase 5-6 provenance and operational contract tables."""
    schema = get_schema()

    # 1. Create capsule_versions table
    op.create_table(
        'capsule_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  primary_key=True, server_default=sa.text('gen_random_uuid()') if schema else None),

        # Capsule reference
        sa.Column('capsule_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=False),

        # Version identification
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('version_name', sa.String(100), nullable=True),
        sa.Column('version_hash', sa.String(64), nullable=True),

        # Schema snapshot
        sa.Column('schema_snapshot', postgresql.JSONB if schema else sa.Text,
                  nullable=False),

        # Change tracking
        sa.Column('change_type', sa.String(50), nullable=True),
        sa.Column('change_summary', sa.Text, nullable=True),
        sa.Column('breaking_change', sa.Boolean, nullable=False,
                  server_default='false'),

        # Lineage snapshot
        sa.Column('upstream_capsule_urns', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),
        sa.Column('downstream_capsule_urns', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),

        # Deployment
        sa.Column('deployed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('deployed_by', sa.String(255), nullable=True),
        sa.Column('deployment_context', postgresql.JSONB if schema else sa.Text,
                  nullable=True),

        # Git integration
        sa.Column('git_commit_sha', sa.String(40), nullable=True),
        sa.Column('git_branch', sa.String(255), nullable=True),
        sa.Column('git_tag', sa.String(255), nullable=True),
        sa.Column('git_repository', sa.String(500), nullable=True),

        # Status
        sa.Column('is_current', sa.Boolean, nullable=False,
                  server_default='false'),

        # Metadata
        sa.Column('meta', postgresql.JSONB if schema else sa.Text,
                  server_default='{}', nullable=False),

        # Audit
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),

        # Foreign keys
        sa.ForeignKeyConstraint(['capsule_id'], [f'{schema}.capsules.id' if schema else 'capsules.id'],
                                ondelete='CASCADE'),

        # Constraints
        sa.UniqueConstraint('capsule_id', 'version_number',
                           name='capsule_version_unique'),

        schema=schema
    )

    # Indexes for capsule_versions
    op.create_index('idx_capsule_versions_capsule', 'capsule_versions',
                    ['capsule_id'], schema=schema)
    op.create_index('idx_capsule_versions_current', 'capsule_versions',
                    ['capsule_id', 'is_current'], schema=schema,
                    postgresql_where=sa.text('is_current = true') if schema else None)
    op.create_index('idx_capsule_versions_created', 'capsule_versions',
                    [sa.text('created_at DESC')], schema=schema)

    # 2. Create transformation_code table
    op.create_table(
        'transformation_code',
        sa.Column('id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  primary_key=True, server_default=sa.text('gen_random_uuid()') if schema else None),

        # Subject (one of these must be set)
        sa.Column('capsule_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=True),
        sa.Column('lineage_edge_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=True),

        # Code
        sa.Column('language', sa.String(50), nullable=False),
        sa.Column('code_text', sa.Text, nullable=False),
        sa.Column('code_hash', sa.String(64), nullable=True),

        # Code metadata
        sa.Column('function_name', sa.String(255), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('line_start', sa.Integer, nullable=True),
        sa.Column('line_end', sa.Integer, nullable=True),

        # Git context
        sa.Column('git_commit_sha', sa.String(40), nullable=True),
        sa.Column('git_repository', sa.String(500), nullable=True),

        # Dependencies
        sa.Column('upstream_references', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),
        sa.Column('function_calls', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),

        # Metadata
        sa.Column('meta', postgresql.JSONB if schema else sa.Text,
                  server_default='{}', nullable=False),

        # Audit
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),

        # Foreign keys
        sa.ForeignKeyConstraint(['capsule_id'], [f'{schema}.capsules.id' if schema else 'capsules.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lineage_edge_id'], [f'{schema}.capsule_lineage.id' if schema else 'capsule_lineage.id'],
                                ondelete='CASCADE'),

        # Constraints
        sa.CheckConstraint(
            "(CASE WHEN capsule_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN lineage_edge_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name='transformation_code_has_subject'
        ),

        schema=schema
    )

    # Indexes for transformation_code
    op.create_index('idx_transformation_code_capsule', 'transformation_code',
                    ['capsule_id'], schema=schema,
                    postgresql_where=sa.text('capsule_id IS NOT NULL') if schema else None)
    op.create_index('idx_transformation_code_edge', 'transformation_code',
                    ['lineage_edge_id'], schema=schema,
                    postgresql_where=sa.text('lineage_edge_id IS NOT NULL') if schema else None)

    # 3. Create capsule_contracts table
    op.create_table(
        'capsule_contracts',
        sa.Column('id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  primary_key=True, server_default=sa.text('gen_random_uuid()') if schema else None),

        # Capsule reference
        sa.Column('capsule_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=False),

        # Contract metadata
        sa.Column('contract_version', sa.String(50), nullable=False),
        sa.Column('contract_status', sa.String(50), nullable=False,
                  server_default='active'),

        # Freshness SLA
        sa.Column('freshness_sla', sa.Interval, nullable=True),
        sa.Column('freshness_schedule', sa.String(100), nullable=True),
        sa.Column('last_updated_at', sa.TIMESTAMP(timezone=True), nullable=True),

        # Completeness SLA
        sa.Column('completeness_sla', sa.Numeric(5, 2), nullable=True),
        sa.Column('expected_row_count_min', sa.BigInteger, nullable=True),
        sa.Column('expected_row_count_max', sa.BigInteger, nullable=True),

        # Availability SLA
        sa.Column('availability_sla', sa.Numeric(5, 2), nullable=True),
        sa.Column('max_downtime', sa.Interval, nullable=True),

        # Quality SLA
        sa.Column('quality_score_sla', sa.Numeric(5, 2), nullable=True),
        sa.Column('critical_quality_rules', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),

        # Latency SLA
        sa.Column('query_latency_p95', sa.Integer, nullable=True),
        sa.Column('query_latency_p99', sa.Integer, nullable=True),

        # Schema stability
        sa.Column('schema_change_policy', sa.String(50), nullable=True),
        sa.Column('breaking_change_notice_days', sa.Integer, nullable=True),

        # Support
        sa.Column('support_level', sa.String(50), nullable=True),
        sa.Column('support_contact', sa.String(255), nullable=True),
        sa.Column('support_slack_channel', sa.String(100), nullable=True),
        sa.Column('support_oncall', sa.String(255), nullable=True),

        # Maintenance windows
        sa.Column('maintenance_windows', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),

        # Deprecation
        sa.Column('deprecation_policy', sa.String(50), nullable=True),
        sa.Column('deprecation_date', sa.Date, nullable=True),
        sa.Column('replacement_capsule_urn', sa.String(500), nullable=True),

        # Consumers
        sa.Column('known_consumers', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),
        sa.Column('consumer_notification_required', sa.Boolean, nullable=False,
                  server_default='true'),

        # Performance targets
        sa.Column('target_row_count', sa.BigInteger, nullable=True),
        sa.Column('target_size_bytes', sa.BigInteger, nullable=True),
        sa.Column('target_column_count', sa.Integer, nullable=True),

        # Cost allocation
        sa.Column('cost_center', sa.String(100), nullable=True),
        sa.Column('billing_tags', postgresql.JSONB if schema else sa.Text,
                  server_default='{}', nullable=False),

        # Metadata
        sa.Column('meta', postgresql.JSONB if schema else sa.Text,
                  server_default='{}', nullable=False),

        # Governance
        sa.Column('contract_owner_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=True),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('approved_at', sa.TIMESTAMP(timezone=True), nullable=True),

        # Audit
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),

        # Foreign keys
        sa.ForeignKeyConstraint(['capsule_id'], [f'{schema}.capsules.id' if schema else 'capsules.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contract_owner_id'], [f'{schema}.owners.id' if schema else 'owners.id']),

        # Constraints
        sa.CheckConstraint(
            "contract_status IN ('draft', 'proposed', 'active', 'deprecated', 'breached')",
            name='contract_status_valid'
        ),
        sa.CheckConstraint(
            "schema_change_policy IN ('strict', 'backwards_compatible', 'flexible', 'unrestricted')",
            name='schema_change_policy_valid'
        ),
        sa.CheckConstraint(
            "support_level IN ('none', 'best_effort', 'business_hours', '24x7', 'critical')",
            name='support_level_valid'
        ),

        schema=schema
    )

    # Indexes for capsule_contracts
    op.create_index('idx_capsule_contracts_capsule', 'capsule_contracts',
                    ['capsule_id'], schema=schema)
    op.create_index('idx_capsule_contracts_status', 'capsule_contracts',
                    ['contract_status'], schema=schema)
    op.create_index('idx_capsule_contracts_deprecation', 'capsule_contracts',
                    ['deprecation_date'], schema=schema,
                    postgresql_where=sa.text('deprecation_date IS NOT NULL') if schema else None)

    # 4. Create sla_incidents table
    op.create_table(
        'sla_incidents',
        sa.Column('id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  primary_key=True, server_default=sa.text('gen_random_uuid()') if schema else None),

        # Contract reference
        sa.Column('contract_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=False),
        sa.Column('capsule_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=False),

        # Incident details
        sa.Column('incident_type', sa.String(50), nullable=False),
        sa.Column('incident_severity', sa.String(20), nullable=False,
                  server_default='medium'),

        # What was violated
        sa.Column('sla_target', sa.Numeric, nullable=True),
        sa.Column('actual_value', sa.Numeric, nullable=True),
        sa.Column('breach_magnitude', sa.Numeric, nullable=True),

        # Timeline
        sa.Column('detected_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('breach_started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('breach_ended_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('breach_duration', sa.Interval, nullable=True),

        # Impact
        sa.Column('affected_consumers', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),
        sa.Column('downstream_impact', sa.Text, nullable=True),

        # Resolution
        sa.Column('incident_status', sa.String(50), nullable=False,
                  server_default='open'),
        sa.Column('resolution', sa.Text, nullable=True),
        sa.Column('resolved_by', sa.String(255), nullable=True),
        sa.Column('resolved_at', sa.TIMESTAMP(timezone=True), nullable=True),

        # Root cause
        sa.Column('root_cause', sa.Text, nullable=True),
        sa.Column('root_cause_category', sa.String(50), nullable=True),

        # Metadata
        sa.Column('meta', postgresql.JSONB if schema else sa.Text,
                  server_default='{}', nullable=False),

        # Audit
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),

        # Foreign keys
        sa.ForeignKeyConstraint(['contract_id'], [f'{schema}.capsule_contracts.id' if schema else 'capsule_contracts.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['capsule_id'], [f'{schema}.capsules.id' if schema else 'capsules.id'],
                                ondelete='CASCADE'),

        # Constraints
        sa.CheckConstraint(
            "incident_type IN ('freshness', 'completeness', 'availability', 'quality', 'latency', 'schema_change')",
            name='incident_type_valid'
        ),
        sa.CheckConstraint(
            "incident_status IN ('open', 'investigating', 'mitigated', 'resolved', 'closed', 'false_positive')",
            name='incident_status_valid'
        ),

        schema=schema
    )

    # Indexes for sla_incidents
    op.create_index('idx_sla_incidents_contract', 'sla_incidents',
                    ['contract_id'], schema=schema)
    op.create_index('idx_sla_incidents_capsule', 'sla_incidents',
                    ['capsule_id'], schema=schema)
    op.create_index('idx_sla_incidents_detected', 'sla_incidents',
                    [sa.text('detected_at DESC')], schema=schema)
    op.create_index('idx_sla_incidents_status', 'sla_incidents',
                    ['incident_status'], schema=schema)


def downgrade() -> None:
    """Remove Phase 5-6 provenance and operational contract tables."""
    schema = get_schema()

    # Drop tables in reverse order (respect foreign key dependencies)
    op.drop_table('sla_incidents', schema=schema)
    op.drop_table('capsule_contracts', schema=schema)
    op.drop_table('transformation_code', schema=schema)
    op.drop_table('capsule_versions', schema=schema)
