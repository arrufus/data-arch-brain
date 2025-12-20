"""Phase 2: Add semantic metadata (business terms, value domains)

Revision ID: 20241218_phase2
Revises: 20241218_phase1
Create Date: 2024-12-18 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20241218_phase2'
down_revision = '20241218_phase1'
branch_labels = None
depends_on = None


def get_schema():
    """Get schema name based on database type."""
    import os
    db_url = os.environ.get("DATABASE_URL", "")
    return None if "sqlite" in db_url else "dcs"


def upgrade() -> None:
    """Add Phase 2 semantic metadata tables and fields."""
    schema = get_schema()

    # 1. Create business_terms table
    op.create_table(
        'business_terms',
        sa.Column('id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  primary_key=True, server_default=sa.text('gen_random_uuid()') if schema else None),

        # Term definition
        sa.Column('term_name', sa.String(255), nullable=False, unique=True),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('definition', sa.Text, nullable=False),
        sa.Column('abbreviation', sa.String(50), nullable=True),
        sa.Column('synonyms', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),

        # Categorization
        sa.Column('domain_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=True),
        sa.Column('category', sa.String(100), nullable=True),

        # Ownership
        sa.Column('owner_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=True),
        sa.Column('steward_email', sa.String(255), nullable=True),

        # Governance
        sa.Column('approval_status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),

        # Metadata
        sa.Column('meta', postgresql.JSONB if schema else sa.Text,
                  server_default='{}', nullable=False),
        sa.Column('tags', postgresql.JSONB if schema else sa.Text,
                  server_default='[]', nullable=False),

        # Audit
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),

        # Foreign keys
        sa.ForeignKeyConstraint(['domain_id'],
                               [f'{schema}.domains.id' if schema else 'domains.id']),
        sa.ForeignKeyConstraint(['owner_id'],
                               [f'{schema}.owners.id' if schema else 'owners.id']),

        # Check constraints
        sa.CheckConstraint(
            "approval_status IN ('draft', 'under_review', 'approved', 'deprecated')",
            name='approval_status_valid'
        ),

        schema=schema
    )

    # Indexes for business_terms
    op.create_index('idx_business_terms_name', 'business_terms',
                    ['term_name'], schema=schema)
    op.create_index('idx_business_terms_domain', 'business_terms',
                    ['domain_id'], schema=schema)
    op.create_index('idx_business_terms_category', 'business_terms',
                    ['category'], schema=schema)
    op.create_index('idx_business_terms_status', 'business_terms',
                    ['approval_status'], schema=schema)

    # 2. Create capsule_business_terms junction table
    op.create_table(
        'capsule_business_terms',
        sa.Column('id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  primary_key=True, server_default=sa.text('gen_random_uuid()') if schema else None),

        sa.Column('capsule_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=False),
        sa.Column('business_term_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=False),

        # Relationship type
        sa.Column('relationship_type', sa.String(50), nullable=False, server_default='implements'),

        # Context
        sa.Column('added_by', sa.String(255), nullable=True),
        sa.Column('added_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('meta', postgresql.JSONB if schema else sa.Text,
                  server_default='{}', nullable=False),

        # Foreign keys
        sa.ForeignKeyConstraint(['capsule_id'],
                               [f'{schema}.capsules.id' if schema else 'capsules.id'],
                               ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['business_term_id'],
                               [f'{schema}.business_terms.id' if schema else 'business_terms.id'],
                               ondelete='CASCADE'),

        schema=schema
    )

    # Indexes for capsule_business_terms
    op.create_index('idx_capsule_business_terms_capsule', 'capsule_business_terms',
                    ['capsule_id'], schema=schema)
    op.create_index('idx_capsule_business_terms_term', 'capsule_business_terms',
                    ['business_term_id'], schema=schema)

    # 3. Create column_business_terms junction table
    op.create_table(
        'column_business_terms',
        sa.Column('id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  primary_key=True, server_default=sa.text('gen_random_uuid()') if schema else None),

        sa.Column('column_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=False),
        sa.Column('business_term_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=False),

        # Relationship type
        sa.Column('relationship_type', sa.String(50), nullable=False, server_default='implements'),

        # Context
        sa.Column('added_by', sa.String(255), nullable=True),
        sa.Column('added_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('meta', postgresql.JSONB if schema else sa.Text,
                  server_default='{}', nullable=False),

        # Foreign keys
        sa.ForeignKeyConstraint(['column_id'],
                               [f'{schema}.columns.id' if schema else 'columns.id'],
                               ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['business_term_id'],
                               [f'{schema}.business_terms.id' if schema else 'business_terms.id'],
                               ondelete='CASCADE'),

        schema=schema
    )

    # Indexes for column_business_terms
    op.create_index('idx_column_business_terms_column', 'column_business_terms',
                    ['column_id'], schema=schema)
    op.create_index('idx_column_business_terms_term', 'column_business_terms',
                    ['business_term_id'], schema=schema)

    # 4. Create value_domains table
    op.create_table(
        'value_domains',
        sa.Column('id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  primary_key=True, server_default=sa.text('gen_random_uuid()') if schema else None),

        # Domain definition
        sa.Column('domain_name', sa.String(255), nullable=False, unique=True),
        sa.Column('domain_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text, nullable=True),

        # For enum domains
        sa.Column('allowed_values', postgresql.JSONB if schema else sa.Text, nullable=True),

        # For pattern domains
        sa.Column('pattern_regex', sa.Text, nullable=True),
        sa.Column('pattern_description', sa.Text, nullable=True),

        # For range domains
        sa.Column('min_value', sa.String(100), nullable=True),
        sa.Column('max_value', sa.String(100), nullable=True),

        # For reference data domains
        sa.Column('reference_table_urn', sa.String(500), nullable=True),
        sa.Column('reference_column_urn', sa.String(500), nullable=True),

        # Governance
        sa.Column('owner_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=True),
        sa.Column('is_extensible', sa.Boolean, server_default='false', nullable=False),

        # Metadata
        sa.Column('meta', postgresql.JSONB if schema else sa.Text,
                  server_default='{}', nullable=False),

        # Audit
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),

        # Foreign keys
        sa.ForeignKeyConstraint(['owner_id'],
                               [f'{schema}.owners.id' if schema else 'owners.id']),

        # Check constraints
        sa.CheckConstraint(
            "domain_type IN ('enum', 'pattern', 'range', 'reference_data')",
            name='domain_type_valid'
        ),

        schema=schema
    )

    # Indexes for value_domains
    op.create_index('idx_value_domains_name', 'value_domains',
                    ['domain_name'], schema=schema)
    op.create_index('idx_value_domains_type', 'value_domains',
                    ['domain_type'], schema=schema)

    # 5. Add semantic metadata columns to columns table
    op.add_column('columns',
                  sa.Column('unit_of_measure', sa.String(100), nullable=True,
                           comment='Physical unit or currency (ISO 4217, SI units)'),
                  schema=schema)
    op.add_column('columns',
                  sa.Column('value_domain', sa.String(100), nullable=True,
                           comment='Reference to controlled vocabulary or enum type'),
                  schema=schema)
    op.add_column('columns',
                  sa.Column('value_range_min', sa.Float, nullable=True,
                           comment='Minimum expected value'),
                  schema=schema)
    op.add_column('columns',
                  sa.Column('value_range_max', sa.Float, nullable=True,
                           comment='Maximum expected value'),
                  schema=schema)
    op.add_column('columns',
                  sa.Column('allowed_values', postgresql.JSONB if schema else sa.Text,
                           nullable=True, comment='Enumerated list of valid values'),
                  schema=schema)
    op.add_column('columns',
                  sa.Column('format_pattern', sa.String(255), nullable=True,
                           comment='Expected format (regex or pattern)'),
                  schema=schema)
    op.add_column('columns',
                  sa.Column('example_values', postgresql.JSONB if schema else sa.Text,
                           server_default='[]', nullable=False,
                           comment='Example values for documentation'),
                  schema=schema)


def downgrade() -> None:
    """Remove Phase 2 semantic metadata tables and fields."""
    schema = get_schema()

    # Remove columns columns
    op.drop_column('columns', 'example_values', schema=schema)
    op.drop_column('columns', 'format_pattern', schema=schema)
    op.drop_column('columns', 'allowed_values', schema=schema)
    op.drop_column('columns', 'value_range_max', schema=schema)
    op.drop_column('columns', 'value_range_min', schema=schema)
    op.drop_column('columns', 'value_domain', schema=schema)
    op.drop_column('columns', 'unit_of_measure', schema=schema)

    # Drop tables
    op.drop_table('value_domains', schema=schema)
    op.drop_table('column_business_terms', schema=schema)
    op.drop_table('capsule_business_terms', schema=schema)
    op.drop_table('business_terms', schema=schema)
