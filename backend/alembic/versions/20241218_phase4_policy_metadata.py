"""Phase 4: Add policy metadata (data policies, masking rules)

Revision ID: 20241218_phase4
Revises: 20241218_phase3
Create Date: 2024-12-18 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20241218_phase4'
down_revision = '20241218_phase3'
branch_labels = None
depends_on = None


def get_schema():
    """Get schema name based on database type."""
    import os
    db_url = os.environ.get("DATABASE_URL", "")
    return None if "sqlite" in db_url else "dcs"


def upgrade() -> None:
    """Add Phase 4 policy metadata tables."""
    schema = get_schema()

    # 1. Create data_policies table
    op.create_table(
        'data_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  primary_key=True, server_default=sa.text('gen_random_uuid()') if schema else None),

        # Subject (one of these must be set)
        sa.Column('capsule_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=True),
        sa.Column('column_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=True),

        # Classification
        sa.Column('sensitivity_level', sa.String(50), nullable=False),
        sa.Column('classification_tags', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),

        # Retention policy
        sa.Column('retention_period', sa.Interval, nullable=True),
        sa.Column('retention_start', sa.String(50), nullable=True),
        sa.Column('deletion_action', sa.String(50), nullable=True),
        sa.Column('legal_hold', sa.Boolean, nullable=False,
                  server_default='false'),

        # Geographic restrictions
        sa.Column('allowed_regions', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),
        sa.Column('restricted_regions', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),
        sa.Column('data_residency', sa.String(50), nullable=True),
        sa.Column('cross_border_transfer', sa.Boolean, nullable=False,
                  server_default='true'),

        # Access control
        sa.Column('min_access_level', sa.String(50), nullable=True),
        sa.Column('allowed_roles', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),
        sa.Column('denied_roles', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),

        # Approved uses
        sa.Column('approved_purposes', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),
        sa.Column('prohibited_purposes', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),

        # Masking/anonymization
        sa.Column('requires_masking', sa.Boolean, nullable=False,
                  server_default='false'),
        sa.Column('masking_method', sa.String(50), nullable=True),
        sa.Column('masking_conditions', postgresql.JSONB if schema else sa.Text,
                  nullable=True),

        # Encryption
        sa.Column('encryption_required', sa.Boolean, nullable=False,
                  server_default='false'),
        sa.Column('encryption_method', sa.String(50), nullable=True),
        sa.Column('encryption_at_rest', sa.Boolean, nullable=False,
                  server_default='false'),
        sa.Column('encryption_in_transit', sa.Boolean, nullable=False,
                  server_default='true'),

        # Compliance tracking
        sa.Column('compliance_frameworks', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),
        sa.Column('consent_required', sa.Boolean, nullable=False,
                  server_default='false'),
        sa.Column('right_to_erasure', sa.Boolean, nullable=False,
                  server_default='false'),

        # Audit requirements
        sa.Column('audit_log_required', sa.Boolean, nullable=False,
                  server_default='false'),
        sa.Column('audit_retention_period', sa.Interval, nullable=True),

        # Governance
        sa.Column('policy_owner_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=True),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_frequency', sa.Interval, nullable=True),
        sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_review_date', sa.Date, nullable=True),

        # Status
        sa.Column('policy_status', sa.String(50), nullable=False,
                  server_default='active'),
        sa.Column('effective_from', sa.Date, nullable=True),
        sa.Column('effective_to', sa.Date, nullable=True),

        # Metadata
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
        sa.ForeignKeyConstraint(['policy_owner_id'],
                               [f'{schema}.owners.id' if schema else 'owners.id']),

        # Check constraints
        sa.CheckConstraint(
            "(capsule_id IS NOT NULL)::int + (column_id IS NOT NULL)::int = 1"
            if schema else
            "(CASE WHEN capsule_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN column_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name='data_policies_has_subject'
        ),
        sa.CheckConstraint(
            "sensitivity_level IN ('public', 'internal', 'confidential', 'restricted', 'secret')",
            name='sensitivity_level_valid'
        ),
        sa.CheckConstraint(
            "deletion_action IN ('hard_delete', 'anonymize', 'archive')",
            name='deletion_action_valid'
        ),
        sa.CheckConstraint(
            "policy_status IN ('draft', 'active', 'deprecated', 'suspended')",
            name='policy_status_valid'
        ),

        schema=schema
    )

    # Indexes for data_policies
    op.create_index('idx_data_policies_capsule', 'data_policies',
                    ['capsule_id'], schema=schema)
    op.create_index('idx_data_policies_column', 'data_policies',
                    ['column_id'], schema=schema)
    op.create_index('idx_data_policies_sensitivity', 'data_policies',
                    ['sensitivity_level'], schema=schema)
    op.create_index('idx_data_policies_review_date', 'data_policies',
                    ['next_review_date'], schema=schema)

    # 2. Create masking_rules table
    op.create_table(
        'masking_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  primary_key=True, server_default=sa.text('gen_random_uuid()') if schema else None),

        # Subject
        sa.Column('column_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=False),

        # Rule definition
        sa.Column('rule_name', sa.String(255), nullable=False),
        sa.Column('masking_method', sa.String(50), nullable=False),
        sa.Column('method_config', postgresql.JSONB if schema else sa.Text,
                  nullable=False),

        # Conditional masking
        sa.Column('apply_condition', sa.Text, nullable=True),
        sa.Column('applies_to_roles', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),
        sa.Column('exempt_roles', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),

        # Preservation options
        sa.Column('preserve_length', sa.Boolean, nullable=False,
                  server_default='false'),
        sa.Column('preserve_format', sa.Boolean, nullable=False,
                  server_default='false'),
        sa.Column('preserve_type', sa.Boolean, nullable=False,
                  server_default='true'),
        sa.Column('preserve_null', sa.Boolean, nullable=False,
                  server_default='true'),

        # Reversibility
        sa.Column('is_reversible', sa.Boolean, nullable=False,
                  server_default='false'),
        sa.Column('tokenization_vault', sa.String(255), nullable=True),

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
        sa.ForeignKeyConstraint(['column_id'],
                               [f'{schema}.columns.id' if schema else 'columns.id'],
                               ondelete='CASCADE'),

        # Check constraints
        sa.CheckConstraint(
            "masking_method IN ('redaction', 'partial_redaction', 'substitution', 'hashing', "
            "'tokenization', 'encryption', 'pseudonymization', 'generalization', "
            "'noise_addition', 'format_preserving_encryption', 'data_masking', 'custom')",
            name='masking_method_valid'
        ),

        schema=schema
    )

    # Indexes for masking_rules
    op.create_index('idx_masking_rules_column', 'masking_rules',
                    ['column_id'], schema=schema)
    op.create_index('idx_masking_rules_enabled', 'masking_rules',
                    ['is_enabled'], schema=schema)


def downgrade() -> None:
    """Remove Phase 4 policy metadata tables."""
    schema = get_schema()

    # Drop tables (in reverse order of creation)
    op.drop_table('masking_rules', schema=schema)
    op.drop_table('data_policies', schema=schema)
