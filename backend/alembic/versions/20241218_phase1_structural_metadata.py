"""Phase 1: Add structural metadata (constraints, indexes, storage)

Revision ID: 20241218_phase1
Revises: 20241216_tag_edges
Create Date: 2024-12-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20241218_phase1'
down_revision = '20241216_tag_edges'
branch_labels = None
depends_on = None


def get_schema():
    """Get schema name based on database type."""
    import os
    db_url = os.environ.get("DATABASE_URL", "")
    return None if "sqlite" in db_url else "dcs"


def upgrade() -> None:
    """Add Phase 1 structural metadata tables and fields."""
    schema = get_schema()

    # 1. Create column_constraints table
    op.create_table(
        'column_constraints',
        sa.Column('id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  primary_key=True, server_default=sa.text('gen_random_uuid()') if schema else None),
        sa.Column('column_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=False),
        sa.Column('constraint_type', sa.String(50), nullable=False),
        sa.Column('constraint_name', sa.String(255), nullable=True),

        # Foreign key references
        sa.Column('referenced_table_urn', sa.String(500), nullable=True),
        sa.Column('referenced_column_urn', sa.String(500), nullable=True),
        sa.Column('on_delete_action', sa.String(50), nullable=True),
        sa.Column('on_update_action', sa.String(50), nullable=True),

        # Check constraints
        sa.Column('check_expression', sa.Text, nullable=True),

        # Default constraints
        sa.Column('default_value', sa.Text, nullable=True),
        sa.Column('default_expression', sa.Text, nullable=True),

        # Enforcement
        sa.Column('is_enforced', sa.Boolean, server_default='true', nullable=False),
        sa.Column('is_deferrable', sa.Boolean, server_default='false', nullable=False),

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

        # Check constraints
        sa.CheckConstraint(
            "constraint_type IN ('primary_key', 'foreign_key', 'unique', 'check', 'not_null', 'default')",
            name='constraint_type_valid'
        ),

        schema=schema
    )

    # Indexes for column_constraints
    op.create_index('idx_column_constraints_column', 'column_constraints',
                    ['column_id'], schema=schema)
    op.create_index('idx_column_constraints_type', 'column_constraints',
                    ['constraint_type'], schema=schema)
    op.create_index('idx_column_constraints_ref_table', 'column_constraints',
                    ['referenced_table_urn'], schema=schema,
                    postgresql_where=sa.text('referenced_table_urn IS NOT NULL'))

    # 2. Create capsule_indexes table
    op.create_table(
        'capsule_indexes',
        sa.Column('id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  primary_key=True, server_default=sa.text('gen_random_uuid()') if schema else None),
        sa.Column('capsule_id', postgresql.UUID(as_uuid=True) if schema else sa.String(36),
                  nullable=False),

        # Index definition
        sa.Column('index_name', sa.String(255), nullable=False),
        sa.Column('index_type', sa.String(50), nullable=False, server_default='btree'),
        sa.Column('is_unique', sa.Boolean, server_default='false', nullable=False),
        sa.Column('is_primary', sa.Boolean, server_default='false', nullable=False),

        # Columns in index
        sa.Column('column_names', postgresql.JSONB if schema else sa.Text, nullable=False),
        sa.Column('column_expressions', postgresql.JSONB if schema else sa.Text, nullable=True),

        # Index properties
        sa.Column('is_partial', sa.Boolean, server_default='false', nullable=False),
        sa.Column('partial_predicate', sa.Text, nullable=True),

        # Storage
        sa.Column('tablespace', sa.String(255), nullable=True),
        sa.Column('fill_factor', sa.Integer, nullable=True),

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

        # Check constraints
        sa.CheckConstraint(
            "index_type IN ('btree', 'hash', 'gin', 'gist', 'brin', 'spgist')",
            name='index_type_valid'
        ),

        schema=schema
    )

    # Indexes for capsule_indexes
    op.create_index('idx_capsule_indexes_capsule', 'capsule_indexes',
                    ['capsule_id'], schema=schema)

    # 3. Add storage and partition metadata columns to capsules table
    op.add_column('capsules',
                  sa.Column('partition_strategy', sa.String(50), nullable=True,
                           comment='Partitioning strategy: range, list, hash, none'),
                  schema=schema)
    op.add_column('capsules',
                  sa.Column('partition_key', postgresql.JSONB if schema else sa.Text, nullable=True,
                           comment='Partition key columns as JSON array'),
                  schema=schema)
    op.add_column('capsules',
                  sa.Column('partition_expression', sa.Text, nullable=True,
                           comment='Partition expression or definition'),
                  schema=schema)
    op.add_column('capsules',
                  sa.Column('storage_format', sa.String(50), nullable=True,
                           comment='Storage format: parquet, orc, avro, delta, iceberg'),
                  schema=schema)
    op.add_column('capsules',
                  sa.Column('compression', sa.String(50), nullable=True,
                           comment='Compression: gzip, snappy, zstd, lz4'),
                  schema=schema)
    op.add_column('capsules',
                  sa.Column('table_size_bytes', sa.BigInteger, nullable=True,
                           comment='Physical size in bytes'),
                  schema=schema)
    op.add_column('capsules',
                  sa.Column('row_count', sa.BigInteger, nullable=True,
                           comment='Approximate row count'),
                  schema=schema)
    op.add_column('capsules',
                  sa.Column('last_analyzed_at', sa.DateTime(timezone=True), nullable=True,
                           comment='Last statistics update'),
                  schema=schema)


def downgrade() -> None:
    """Remove Phase 1 structural metadata tables and fields."""
    schema = get_schema()

    # Remove capsules columns
    op.drop_column('capsules', 'last_analyzed_at', schema=schema)
    op.drop_column('capsules', 'row_count', schema=schema)
    op.drop_column('capsules', 'table_size_bytes', schema=schema)
    op.drop_column('capsules', 'compression', schema=schema)
    op.drop_column('capsules', 'storage_format', schema=schema)
    op.drop_column('capsules', 'partition_expression', schema=schema)
    op.drop_column('capsules', 'partition_key', schema=schema)
    op.drop_column('capsules', 'partition_strategy', schema=schema)

    # Drop tables
    op.drop_table('capsule_indexes', schema=schema)
    op.drop_table('column_constraints', schema=schema)
