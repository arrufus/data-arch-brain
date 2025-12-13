# Data Architecture Brain - Database Schema

**Version**: 1.0
**Status**: Draft
**Last Updated**: December 2024

---

## Table of Contents

1. [Schema Overview](#1-schema-overview)
2. [Design Decisions](#2-design-decisions)
3. [Core Tables](#3-core-tables)
4. [Relationship Tables](#4-relationship-tables)
5. [Metadata Tables](#5-metadata-tables)
6. [Indexes](#6-indexes)
7. [Migrations](#7-migrations)
8. [Query Patterns](#8-query-patterns)

---

## 1. Schema Overview

### 1.1 Schema Namespace

All Data Architecture Brain tables reside in the `dab` schema to maintain separation from Easy Modeller tables.

```sql
CREATE SCHEMA IF NOT EXISTS dab;
```

### 1.2 Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATABASE SCHEMA                                    │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌───────────────┐       ┌───────────────┐       ┌───────────────┐
  │   domains     │       │ source_systems│       │    owners     │
  │───────────────│       │───────────────│       │───────────────│
  │ id            │       │ id            │       │ id            │
  │ name          │       │ name          │       │ name          │
  │ description   │       │ type          │       │ type          │
  └───────┬───────┘       │ connection_info       │ email         │
          │               └───────┬───────┘       └───────┬───────┘
          │                       │                       │
          │ BELONGS_TO            │ SOURCED_FROM          │ OWNED_BY
          │                       │                       │
          ▼                       ▼                       ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                          capsules                                │
  │─────────────────────────────────────────────────────────────────│
  │ id (PK)          │ urn (UNIQUE)      │ name                     │
  │ capsule_type     │ source_system_id  │ domain_id                │
  │ layer            │ schema_name       │ database_name            │
  │ description      │ materialization   │ owner_id                 │
  │ meta (JSONB)     │ tags (JSONB)      │ created_at, updated_at   │
  └──────────────────────────────┬──────────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              │ CONTAINS         │ FLOWS_TO         │ VIOLATES
              ▼                  ▼                  ▼
  ┌───────────────────┐  ┌───────────────┐  ┌───────────────┐
  │     columns       │  │capsule_lineage│  │  violations   │
  │───────────────────│  │───────────────│  │───────────────│
  │ id                │  │ id            │  │ id            │
  │ urn               │  │ source_urn    │  │ capsule_id    │
  │ capsule_id (FK)   │  │ target_urn    │  │ column_id     │
  │ name              │  │ source_id     │  │ rule_id       │
  │ data_type         │  │ target_id     │  │ severity      │
  │ ordinal_position  │  │ edge_type     │  │ message       │
  │ is_nullable       │  │ meta          │  │ details       │
  │ description       │  │               │  │               │
  │ semantic_type     │  └───────────────┘  └───────┬───────┘
  │ pii_type          │                             │
  │ meta (JSONB)      │                             │
  │ tags (JSONB)      │                     ┌───────▼───────┐
  └─────────┬─────────┘                     │    rules      │
            │                               │───────────────│
            │ DERIVED_FROM                  │ id            │
            ▼                               │ rule_id       │
  ┌───────────────────┐                     │ name          │
  │  column_lineage   │                     │ description   │
  │───────────────────│                     │ severity      │
  │ id                │                     │ category      │
  │ source_column_id  │                     │ rule_set      │
  │ target_column_id  │                     │ scope         │
  │ transformation    │                     │ definition    │
  └───────────────────┘                     │ enabled       │
                                            └───────────────┘

  ┌───────────────────┐       ┌───────────────────┐
  │      tags         │       │  ingestion_jobs   │
  │───────────────────│       │───────────────────│
  │ id                │       │ id                │
  │ name              │       │ source_type       │
  │ category          │       │ status            │
  │ description       │       │ started_at        │
  │                   │       │ completed_at      │
  └─────────┬─────────┘       │ stats (JSONB)     │
            │                 │ error_message     │
            │                 └───────────────────┘
            ▼
  ┌───────────────────┐
  │  capsule_tags     │       ┌───────────────────┐
  │───────────────────│       │   column_tags     │
  │ capsule_id (FK)   │       │───────────────────│
  │ tag_id (FK)       │       │ column_id (FK)    │
  └───────────────────┘       │ tag_id (FK)       │
                              └───────────────────┘
```

---

## 2. Design Decisions

### 2.1 Graph in PostgreSQL

We use PostgreSQL (rather than a dedicated graph database) for:

| Reason | Benefit |
|--------|---------|
| **Shared infrastructure** | Same DB as Easy Modeller |
| **JSONB flexibility** | Store arbitrary metadata |
| **Recursive CTEs** | Efficient lineage traversal |
| **Mature tooling** | SQLAlchemy, Alembic, pgAdmin |
| **Scale sufficient** | MVP scale (10K nodes) well within PostgreSQL limits |

### 2.2 URN as Business Key

- **URN** (Uniform Resource Name) serves as the immutable business key
- Internal **id** (UUID) used for foreign keys and joins
- Enables stable references across re-ingestion

### 2.3 JSONB for Extensibility

Properties that vary by source or may evolve:
- `meta` - Source-specific metadata
- `tags` - Flexible tagging array
- `definition` - Rule definitions (YAML stored as JSONB)
- `stats` - Ingestion statistics

### 2.4 Separate Lineage Tables

- **capsule_lineage** - Model-to-model relationships (FLOWS_TO)
- **column_lineage** - Column-to-column relationships (DERIVED_FROM)

This allows efficient traversal at both levels.

---

## 3. Core Tables

### 3.1 capsules

The primary table storing Data Capsules (data assets).

```sql
CREATE TABLE dab.capsules (
    -- Identity
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    urn             VARCHAR(500) NOT NULL UNIQUE,
    name            VARCHAR(255) NOT NULL,
    capsule_type    VARCHAR(50) NOT NULL,  -- 'model', 'source', 'seed', 'snapshot'

    -- Source context
    source_system_id UUID REFERENCES dab.source_systems(id),
    database_name   VARCHAR(255),
    schema_name     VARCHAR(255),

    -- Domain context
    domain_id       UUID REFERENCES dab.domains(id),
    owner_id        UUID REFERENCES dab.owners(id),

    -- Architecture context
    layer           VARCHAR(50),           -- 'bronze', 'silver', 'gold'
    materialization VARCHAR(50),           -- 'table', 'view', 'incremental', 'ephemeral'

    -- Documentation
    description     TEXT,

    -- Flexible metadata
    meta            JSONB DEFAULT '{}',
    tags            JSONB DEFAULT '[]',    -- Array of tag strings for quick filtering

    -- Quality indicators
    has_tests       BOOLEAN DEFAULT FALSE,
    test_count      INTEGER DEFAULT 0,
    doc_coverage    FLOAT DEFAULT 0.0,     -- % of columns with descriptions

    -- Audit
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ingestion_id    UUID REFERENCES dab.ingestion_jobs(id),

    -- Constraints
    CONSTRAINT capsule_type_valid CHECK (
        capsule_type IN ('model', 'source', 'seed', 'snapshot', 'analysis', 'test')
    ),
    CONSTRAINT layer_valid CHECK (
        layer IS NULL OR layer IN ('bronze', 'silver', 'gold', 'raw', 'staging', 'intermediate', 'marts')
    )
);

-- Comments
COMMENT ON TABLE dab.capsules IS 'Data Capsules - atomic units of the data architecture graph';
COMMENT ON COLUMN dab.capsules.urn IS 'Uniform Resource Name: urn:dab:{source}:{type}:{namespace}:{name}';
COMMENT ON COLUMN dab.capsules.meta IS 'Source-specific metadata (e.g., dbt config, freshness)';
COMMENT ON COLUMN dab.capsules.tags IS 'Array of tag strings for filtering: ["pii", "finance", "critical"]';
```

### 3.2 columns

Columns within Data Capsules.

```sql
CREATE TABLE dab.columns (
    -- Identity
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    urn             VARCHAR(500) NOT NULL UNIQUE,
    capsule_id      UUID NOT NULL REFERENCES dab.capsules(id) ON DELETE CASCADE,

    -- Column definition
    name            VARCHAR(255) NOT NULL,
    data_type       VARCHAR(100),
    ordinal_position INTEGER,
    is_nullable     BOOLEAN DEFAULT TRUE,

    -- Semantic classification
    semantic_type   VARCHAR(50),           -- 'pii', 'business_key', 'metric', 'timestamp'
    pii_type        VARCHAR(50),           -- 'email', 'ssn', 'phone', 'address', etc.
    pii_detected_by VARCHAR(50),           -- 'tag', 'pattern', 'manual'

    -- Documentation
    description     TEXT,

    -- Flexible metadata
    meta            JSONB DEFAULT '{}',
    tags            JSONB DEFAULT '[]',

    -- Statistics (from catalog)
    stats           JSONB DEFAULT '{}',    -- distinct_count, null_count, min, max

    -- Quality indicators
    has_tests       BOOLEAN DEFAULT FALSE,
    test_count      INTEGER DEFAULT 0,

    -- Audit
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT unique_column_per_capsule UNIQUE (capsule_id, name),
    CONSTRAINT semantic_type_valid CHECK (
        semantic_type IS NULL OR semantic_type IN (
            'pii', 'business_key', 'natural_key', 'surrogate_key',
            'foreign_key', 'metric', 'measure', 'dimension',
            'timestamp', 'event_time', 'processing_time'
        )
    ),
    CONSTRAINT pii_type_valid CHECK (
        pii_type IS NULL OR pii_type IN (
            'direct_identifier', 'email', 'phone', 'address', 'ssn',
            'credit_card', 'bank_account', 'health', 'biometric',
            'date_of_birth', 'name', 'ip_address', 'device_id'
        )
    )
);

COMMENT ON TABLE dab.columns IS 'Columns within Data Capsules with semantic classification';
COMMENT ON COLUMN dab.columns.semantic_type IS 'Business meaning of the column';
COMMENT ON COLUMN dab.columns.pii_type IS 'Specific type of PII if semantic_type is pii';
COMMENT ON COLUMN dab.columns.pii_detected_by IS 'How PII was detected: tag (from source), pattern (regex), manual';
```

### 3.3 domains

Business domains for organizing capsules.

```sql
CREATE TABLE dab.domains (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL UNIQUE,
    description     TEXT,
    parent_id       UUID REFERENCES dab.domains(id),  -- For sub-domains
    owner_id        UUID REFERENCES dab.owners(id),
    meta            JSONB DEFAULT '{}',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE dab.domains IS 'Business domains (e.g., Customer, Order, Product)';
```

### 3.4 source_systems

Metadata sources (dbt, Snowflake, etc.).

```sql
CREATE TABLE dab.source_systems (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL UNIQUE,
    source_type     VARCHAR(50) NOT NULL,  -- 'dbt', 'snowflake', 'bigquery', etc.
    description     TEXT,
    connection_info JSONB DEFAULT '{}',    -- Non-sensitive connection metadata
    meta            JSONB DEFAULT '{}',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT source_type_valid CHECK (
        source_type IN ('dbt', 'snowflake', 'bigquery', 'databricks', 'postgres', 'mysql', 'manual')
    )
);

COMMENT ON TABLE dab.source_systems IS 'Metadata sources from which capsules are ingested';
COMMENT ON COLUMN dab.source_systems.connection_info IS 'Non-sensitive info like project name, database, etc.';
```

### 3.5 owners

Teams or individuals owning data assets.

```sql
CREATE TABLE dab.owners (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    owner_type      VARCHAR(50) NOT NULL DEFAULT 'team',  -- 'team', 'individual'
    email           VARCHAR(255),
    slack_channel   VARCHAR(100),
    meta            JSONB DEFAULT '{}',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_owner_name_type UNIQUE (name, owner_type)
);

COMMENT ON TABLE dab.owners IS 'Teams or individuals responsible for data assets';
```

### 3.6 tags

Reusable tags for classification.

```sql
CREATE TABLE dab.tags (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    category        VARCHAR(50),           -- 'sensitivity', 'domain', 'quality', 'status'
    description     TEXT,
    color           VARCHAR(7),            -- Hex color for UI
    meta            JSONB DEFAULT '{}',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_tag_name_category UNIQUE (name, category)
);

COMMENT ON TABLE dab.tags IS 'Reusable tags for classifying capsules and columns';
```

### 3.7 rules

Conformance rules for architecture validation.

```sql
CREATE TABLE dab.rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id         VARCHAR(50) NOT NULL UNIQUE,  -- e.g., 'NAMING_001', 'PII_002'
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    severity        VARCHAR(20) NOT NULL DEFAULT 'warning',
    category        VARCHAR(50) NOT NULL,  -- 'naming', 'lineage', 'pii', 'documentation'
    rule_set        VARCHAR(50),           -- 'medallion', 'dbt_best_practices', 'pii_compliance'
    scope           VARCHAR(50) NOT NULL,  -- 'capsule', 'column', 'lineage'
    definition      JSONB NOT NULL,        -- Rule logic (type, pattern, condition)
    enabled         BOOLEAN DEFAULT TRUE,
    meta            JSONB DEFAULT '{}',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT severity_valid CHECK (
        severity IN ('info', 'warning', 'error', 'critical')
    ),
    CONSTRAINT scope_valid CHECK (
        scope IN ('capsule', 'column', 'lineage', 'global')
    )
);

COMMENT ON TABLE dab.rules IS 'Conformance rules for architecture validation';
COMMENT ON COLUMN dab.rules.definition IS 'Rule logic as JSONB: {type, pattern, condition, message}';
```

---

## 4. Relationship Tables

### 4.1 capsule_lineage

Model-to-model lineage relationships.

```sql
CREATE TABLE dab.capsule_lineage (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- URNs for reference (survive re-ingestion)
    source_urn      VARCHAR(500) NOT NULL,
    target_urn      VARCHAR(500) NOT NULL,

    -- Foreign keys for efficient joins
    source_id       UUID NOT NULL REFERENCES dab.capsules(id) ON DELETE CASCADE,
    target_id       UUID NOT NULL REFERENCES dab.capsules(id) ON DELETE CASCADE,

    -- Edge metadata
    edge_type       VARCHAR(50) NOT NULL DEFAULT 'flows_to',
    transformation  VARCHAR(50),           -- 'ref', 'source', 'external'
    meta            JSONB DEFAULT '{}',

    -- Audit
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ingestion_id    UUID REFERENCES dab.ingestion_jobs(id),

    -- Constraints
    CONSTRAINT unique_capsule_edge UNIQUE (source_id, target_id, edge_type),
    CONSTRAINT no_self_reference CHECK (source_id != target_id)
);

-- Index for traversal queries
CREATE INDEX idx_capsule_lineage_source ON dab.capsule_lineage(source_id);
CREATE INDEX idx_capsule_lineage_target ON dab.capsule_lineage(target_id);

COMMENT ON TABLE dab.capsule_lineage IS 'Model-to-model lineage (FLOWS_TO relationships)';
COMMENT ON COLUMN dab.capsule_lineage.transformation IS 'How the relationship was established: ref(), source(), etc.';
```

### 4.2 column_lineage

Column-to-column lineage relationships.

```sql
CREATE TABLE dab.column_lineage (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- URNs for reference
    source_urn      VARCHAR(500) NOT NULL,
    target_urn      VARCHAR(500) NOT NULL,

    -- Foreign keys
    source_column_id UUID NOT NULL REFERENCES dab.columns(id) ON DELETE CASCADE,
    target_column_id UUID NOT NULL REFERENCES dab.columns(id) ON DELETE CASCADE,

    -- Transformation details
    transformation_type VARCHAR(50),       -- 'direct', 'derived', 'aggregated', 'masked', 'hashed'
    transformation_expr TEXT,              -- SQL expression if available

    -- Audit
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ingestion_id    UUID REFERENCES dab.ingestion_jobs(id),

    -- Constraints
    CONSTRAINT unique_column_edge UNIQUE (source_column_id, target_column_id),
    CONSTRAINT no_self_reference CHECK (source_column_id != target_column_id)
);

CREATE INDEX idx_column_lineage_source ON dab.column_lineage(source_column_id);
CREATE INDEX idx_column_lineage_target ON dab.column_lineage(target_column_id);

COMMENT ON TABLE dab.column_lineage IS 'Column-to-column lineage (DERIVED_FROM relationships)';
COMMENT ON COLUMN dab.column_lineage.transformation_type IS 'Type of transformation applied';
```

### 4.3 capsule_tags (Junction Table)

```sql
CREATE TABLE dab.capsule_tags (
    capsule_id      UUID NOT NULL REFERENCES dab.capsules(id) ON DELETE CASCADE,
    tag_id          UUID NOT NULL REFERENCES dab.tags(id) ON DELETE CASCADE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    PRIMARY KEY (capsule_id, tag_id)
);
```

### 4.4 column_tags (Junction Table)

```sql
CREATE TABLE dab.column_tags (
    column_id       UUID NOT NULL REFERENCES dab.columns(id) ON DELETE CASCADE,
    tag_id          UUID NOT NULL REFERENCES dab.tags(id) ON DELETE CASCADE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    PRIMARY KEY (column_id, tag_id)
);
```

---

## 5. Metadata Tables

### 5.1 ingestion_jobs

Track ingestion runs for auditing and debugging.

```sql
CREATE TABLE dab.ingestion_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type     VARCHAR(50) NOT NULL,
    source_name     VARCHAR(255),
    status          VARCHAR(20) NOT NULL DEFAULT 'running',
    started_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at    TIMESTAMP WITH TIME ZONE,

    -- Statistics
    stats           JSONB DEFAULT '{}',    -- capsules_created, columns_created, etc.

    -- Configuration used
    config          JSONB DEFAULT '{}',

    -- Error handling
    error_message   TEXT,
    error_details   JSONB,

    CONSTRAINT status_valid CHECK (
        status IN ('pending', 'running', 'completed', 'failed', 'cancelled')
    )
);

COMMENT ON TABLE dab.ingestion_jobs IS 'Audit log of metadata ingestion runs';
```

### 5.2 violations

Conformance rule violations.

```sql
CREATE TABLE dab.violations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What was violated
    rule_id         UUID NOT NULL REFERENCES dab.rules(id) ON DELETE CASCADE,

    -- What violated it (one of these)
    capsule_id      UUID REFERENCES dab.capsules(id) ON DELETE CASCADE,
    column_id       UUID REFERENCES dab.columns(id) ON DELETE CASCADE,

    -- Violation details
    severity        VARCHAR(20) NOT NULL,
    message         TEXT NOT NULL,
    details         JSONB DEFAULT '{}',    -- Additional context

    -- Status
    status          VARCHAR(20) DEFAULT 'open',  -- 'open', 'acknowledged', 'resolved', 'false_positive'
    resolved_at     TIMESTAMP WITH TIME ZONE,
    resolved_by     VARCHAR(255),

    -- Audit
    detected_at     TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ingestion_id    UUID REFERENCES dab.ingestion_jobs(id),

    CONSTRAINT has_subject CHECK (
        capsule_id IS NOT NULL OR column_id IS NOT NULL
    )
);

CREATE INDEX idx_violations_capsule ON dab.violations(capsule_id) WHERE capsule_id IS NOT NULL;
CREATE INDEX idx_violations_rule ON dab.violations(rule_id);
CREATE INDEX idx_violations_severity ON dab.violations(severity);
CREATE INDEX idx_violations_status ON dab.violations(status);

COMMENT ON TABLE dab.violations IS 'Conformance rule violations detected during analysis';
```

### 5.3 conformance_scores

Pre-computed conformance scores for performance.

```sql
CREATE TABLE dab.conformance_scores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Scope (one of these)
    capsule_id      UUID REFERENCES dab.capsules(id) ON DELETE CASCADE,
    domain_id       UUID REFERENCES dab.domains(id) ON DELETE CASCADE,
    is_global       BOOLEAN DEFAULT FALSE,

    -- Scores
    score           FLOAT NOT NULL,        -- 0-100
    weighted_score  FLOAT NOT NULL,        -- Weighted by severity
    total_rules     INTEGER NOT NULL,
    passing_rules   INTEGER NOT NULL,
    failing_rules   INTEGER NOT NULL,

    -- Breakdown by severity
    critical_violations INTEGER DEFAULT 0,
    error_violations    INTEGER DEFAULT 0,
    warning_violations  INTEGER DEFAULT 0,
    info_violations     INTEGER DEFAULT 0,

    -- When computed
    computed_at     TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ingestion_id    UUID REFERENCES dab.ingestion_jobs(id),

    CONSTRAINT score_scope CHECK (
        (capsule_id IS NOT NULL)::int +
        (domain_id IS NOT NULL)::int +
        is_global::int = 1
    )
);

COMMENT ON TABLE dab.conformance_scores IS 'Pre-computed conformance scores at various levels';
```

---

## 6. Indexes

### 6.1 Primary Query Patterns

```sql
-- Capsule lookups by URN (most common)
CREATE UNIQUE INDEX idx_capsules_urn ON dab.capsules(urn);

-- Capsule filtering
CREATE INDEX idx_capsules_layer ON dab.capsules(layer);
CREATE INDEX idx_capsules_type ON dab.capsules(capsule_type);
CREATE INDEX idx_capsules_domain ON dab.capsules(domain_id);
CREATE INDEX idx_capsules_source ON dab.capsules(source_system_id);

-- Column lookups
CREATE UNIQUE INDEX idx_columns_urn ON dab.columns(urn);
CREATE INDEX idx_columns_capsule ON dab.columns(capsule_id);
CREATE INDEX idx_columns_semantic_type ON dab.columns(semantic_type);
CREATE INDEX idx_columns_pii_type ON dab.columns(pii_type) WHERE pii_type IS NOT NULL;

-- Tag-based filtering (GIN for JSONB array)
CREATE INDEX idx_capsules_tags ON dab.capsules USING GIN (tags);
CREATE INDEX idx_columns_tags ON dab.columns USING GIN (tags);

-- Full-text search on names/descriptions
CREATE INDEX idx_capsules_name_search ON dab.capsules USING GIN (to_tsvector('english', name || ' ' || COALESCE(description, '')));
CREATE INDEX idx_columns_name_search ON dab.columns USING GIN (to_tsvector('english', name || ' ' || COALESCE(description, '')));

-- Rule lookups
CREATE INDEX idx_rules_category ON dab.rules(category);
CREATE INDEX idx_rules_rule_set ON dab.rules(rule_set);
CREATE INDEX idx_rules_enabled ON dab.rules(enabled) WHERE enabled = TRUE;
```

---

## 7. Migrations

### 7.1 Initial Migration (V1)

```sql
-- migrations/versions/001_initial_schema.sql

BEGIN;

-- Create schema
CREATE SCHEMA IF NOT EXISTS dab;

-- Create tables in dependency order
-- 1. Independent tables
CREATE TABLE dab.owners (...);
CREATE TABLE dab.source_systems (...);
CREATE TABLE dab.domains (...);
CREATE TABLE dab.tags (...);
CREATE TABLE dab.rules (...);
CREATE TABLE dab.ingestion_jobs (...);

-- 2. Main entity tables
CREATE TABLE dab.capsules (...);
CREATE TABLE dab.columns (...);

-- 3. Relationship tables
CREATE TABLE dab.capsule_lineage (...);
CREATE TABLE dab.column_lineage (...);
CREATE TABLE dab.capsule_tags (...);
CREATE TABLE dab.column_tags (...);
CREATE TABLE dab.violations (...);
CREATE TABLE dab.conformance_scores (...);

-- 4. Create indexes
CREATE INDEX ...;

COMMIT;
```

### 7.2 Alembic Migration Template

```python
"""Initial schema for Data Architecture Brain

Revision ID: 001
Create Date: 2024-12-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create schema
    op.execute('CREATE SCHEMA IF NOT EXISTS dab')

    # Create source_systems table
    op.create_table(
        'source_systems',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('connection_info', postgresql.JSONB, default={}),
        sa.Column('meta', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema='dab'
    )

    # ... continue for all tables


def downgrade():
    op.drop_table('conformance_scores', schema='dab')
    op.drop_table('violations', schema='dab')
    # ... drop all tables in reverse order
    op.execute('DROP SCHEMA dab')
```

---

## 8. Query Patterns

### 8.1 Lineage Traversal (Recursive CTE)

```sql
-- Get all upstream capsules for a given URN (up to depth N)
WITH RECURSIVE upstream AS (
    -- Base case: the starting capsule
    SELECT
        c.id,
        c.urn,
        c.name,
        c.layer,
        0 as depth
    FROM dab.capsules c
    WHERE c.urn = :target_urn

    UNION ALL

    -- Recursive case: follow lineage edges backwards
    SELECT
        c.id,
        c.urn,
        c.name,
        c.layer,
        u.depth + 1
    FROM dab.capsules c
    INNER JOIN dab.capsule_lineage cl ON c.id = cl.source_id
    INNER JOIN upstream u ON cl.target_id = u.id
    WHERE u.depth < :max_depth
)
SELECT DISTINCT * FROM upstream ORDER BY depth;
```

### 8.2 PII Inventory

```sql
-- Get all PII columns grouped by type
SELECT
    c.pii_type,
    COUNT(*) as column_count,
    array_agg(DISTINCT cap.layer) as layers,
    array_agg(c.urn) as column_urns
FROM dab.columns c
INNER JOIN dab.capsules cap ON c.capsule_id = cap.id
WHERE c.semantic_type = 'pii'
GROUP BY c.pii_type
ORDER BY column_count DESC;
```

### 8.3 PII Exposure Detection

```sql
-- Find PII columns in Gold layer that don't have masking transformation
SELECT
    c.urn as column_urn,
    c.name as column_name,
    c.pii_type,
    cap.urn as capsule_urn,
    cap.name as capsule_name
FROM dab.columns c
INNER JOIN dab.capsules cap ON c.capsule_id = cap.id
WHERE
    c.semantic_type = 'pii'
    AND cap.layer = 'gold'
    AND NOT EXISTS (
        SELECT 1 FROM dab.column_lineage cl
        WHERE cl.target_column_id = c.id
        AND cl.transformation_type IN ('masked', 'hashed', 'encrypted', 'redacted')
    );
```

### 8.4 Conformance Score Calculation

```sql
-- Calculate conformance score for a domain
SELECT
    d.name as domain_name,
    COUNT(DISTINCT r.id) as total_rules,
    COUNT(DISTINCT r.id) - COUNT(DISTINCT v.rule_id) as passing_rules,
    ROUND(
        (COUNT(DISTINCT r.id) - COUNT(DISTINCT v.rule_id))::numeric /
        NULLIF(COUNT(DISTINCT r.id), 0) * 100,
        2
    ) as score
FROM dab.domains d
CROSS JOIN dab.rules r
LEFT JOIN dab.capsules cap ON cap.domain_id = d.id
LEFT JOIN dab.violations v ON v.capsule_id = cap.id AND v.rule_id = r.id AND v.status = 'open'
WHERE d.id = :domain_id
AND r.enabled = TRUE
GROUP BY d.id, d.name;
```

### 8.5 Find Capsules by Tag (JSONB)

```sql
-- Find all capsules tagged with 'pii' or 'sensitive'
SELECT *
FROM dab.capsules
WHERE tags ?| array['pii', 'sensitive'];

-- Find capsules with specific meta property
SELECT *
FROM dab.capsules
WHERE meta->>'materialized' = 'incremental';
```

---

## Appendix: Sample Data

### Sample Source System

```sql
INSERT INTO dab.source_systems (id, name, source_type, description, connection_info)
VALUES (
    gen_random_uuid(),
    'jaffle_shop_dbt',
    'dbt',
    'Jaffle Shop dbt project',
    '{"project_name": "jaffle_shop", "version": "1.0.0"}'::jsonb
);
```

### Sample Capsule

```sql
INSERT INTO dab.capsules (
    id, urn, name, capsule_type, layer, schema_name,
    description, materialization, meta, tags
)
VALUES (
    gen_random_uuid(),
    'urn:dab:dbt:model:jaffle_shop.staging:stg_customers',
    'stg_customers',
    'model',
    'silver',
    'staging',
    'Staged customer data from source',
    'view',
    '{"unique_id": "model.jaffle_shop.stg_customers"}'::jsonb,
    '["customer", "staging"]'::jsonb
);
```

### Sample Column with PII

```sql
INSERT INTO dab.columns (
    id, urn, capsule_id, name, data_type, ordinal_position,
    semantic_type, pii_type, pii_detected_by, description
)
VALUES (
    gen_random_uuid(),
    'urn:dab:dbt:column:jaffle_shop.staging:stg_customers.email',
    :capsule_id,
    'email',
    'VARCHAR',
    3,
    'pii',
    'email',
    'pattern',
    'Customer email address'
);
```

---

*End of Database Schema Document*
