# Data Capsule Model Extension Design

**Version**: 1.0
**Status**: Draft
**Last Updated**: December 17, 2024
**Author**: Data Capsule Server Team

---

## Executive Summary

This document proposes extensions to the Data Capsule Server data model to fully implement the seven dimensions of Data Capsules as described in the theoretical framework. The goal is to make data and metadata an atomic, inseparable unit that can be versioned, deployed, and governed together.

### Current Coverage Analysis

| Dimension | Current Coverage | Gap |
|-----------|-----------------|-----|
| **1. Data Payload** | N/A (external data) | No changes needed |
| **2. Structural Metadata** | 60% - Basic schema | Missing: constraints, keys, indexes |
| **3. Semantic Metadata** | 40% - Basic semantics | Missing: units, vocabularies, business glossary |
| **4. Quality Expectations** | 30% - Test flags only | Missing: validation rules, thresholds, distributions |
| **5. Policy Metadata** | 40% - PII detection | Missing: retention, masking rules, geo-restrictions |
| **6. Provenance & Lineage** | 85% - Well covered | Minor: stable dataset versioning |
| **7. Operational Contract** | 50% - SLOs at product level | Missing: capsule-level SLAs, contracts |

---

## Table of Contents

1. [Architecture Principles](#1-architecture-principles)
2. [Dimension 2: Enhanced Structural Metadata](#2-dimension-2-enhanced-structural-metadata)
3. [Dimension 3: Semantic Metadata](#3-dimension-3-semantic-metadata)
4. [Dimension 4: Quality Expectations](#4-dimension-4-quality-expectations)
5. [Dimension 5: Policy Metadata](#5-dimension-5-policy-metadata)
6. [Dimension 6: Provenance Enhancements](#6-dimension-6-provenance-enhancements)
7. [Dimension 7: Operational Contracts](#7-dimension-7-operational-contracts)
8. [Cross-Cutting Concerns](#8-cross-cutting-concerns)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [Migration Strategy](#10-migration-strategy)

---

## 1. Architecture Principles

### 1.1 Design Philosophy

Following the Data Capsule theory, our extensions adhere to these principles:

1. **Strong Binding**: Metadata is bound to capsules via foreign keys and URNs
2. **Co-Versioning**: Capsule versions track metadata changes in tandem
3. **Atomic Deployment**: Capsule + metadata deployed as single logical unit
4. **Machine-Readable**: All metadata structured as JSONB or tables for automation
5. **Layered Access**: Support public vs. restricted metadata facets
6. **Backwards Compatible**: Extensions don't break existing functionality

### 1.2 Technology Stack

- **Database**: PostgreSQL 15+ (JSONB, recursive CTEs, row-level security)
- **Schema**: `dcs` namespace (renamed from `dab`)
- **ORM**: SQLAlchemy 2.0+ with type hints
- **Validation**: Pydantic models for schema validation
- **API**: FastAPI endpoints for CRUD operations

---

## 2. Dimension 2: Enhanced Structural Metadata

### 2.1 Current State

**Existing Coverage**:
- ✅ Column names, data types
- ✅ Ordinal positions, nullability
- ✅ Basic stats in JSONB

**Missing**:
- ❌ Primary key definitions
- ❌ Foreign key relationships
- ❌ Unique constraints
- ❌ Check constraints
- ❌ Index definitions
- ❌ Partitioning schemes

### 2.2 Proposed Extensions

#### 2.2.1 New Table: `column_constraints`

```sql
CREATE TABLE dcs.column_constraints (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    column_id           UUID NOT NULL REFERENCES dcs.columns(id) ON DELETE CASCADE,

    -- Constraint definition
    constraint_type     VARCHAR(50) NOT NULL,  -- 'primary_key', 'foreign_key', 'unique', 'check', 'not_null', 'default'
    constraint_name     VARCHAR(255),

    -- For foreign keys
    referenced_table_urn VARCHAR(500),
    referenced_column_urn VARCHAR(500),
    on_delete_action    VARCHAR(50),  -- 'CASCADE', 'SET NULL', 'RESTRICT', 'NO ACTION'
    on_update_action    VARCHAR(50),

    -- For check constraints
    check_expression    TEXT,

    -- For default constraints
    default_value       TEXT,
    default_expression  TEXT,

    -- Metadata
    is_enforced         BOOLEAN DEFAULT TRUE,
    is_deferrable       BOOLEAN DEFAULT FALSE,
    meta                JSONB DEFAULT '{}',

    -- Audit
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT constraint_type_valid CHECK (
        constraint_type IN (
            'primary_key', 'foreign_key', 'unique',
            'check', 'not_null', 'default'
        )
    )
);

CREATE INDEX idx_column_constraints_column ON dcs.column_constraints(column_id);
CREATE INDEX idx_column_constraints_type ON dcs.column_constraints(constraint_type);
CREATE INDEX idx_column_constraints_ref_table ON dcs.column_constraints(referenced_table_urn)
    WHERE referenced_table_urn IS NOT NULL;
```

**SQLAlchemy Model**:
```python
class ConstraintType(str, Enum):
    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"
    UNIQUE = "unique"
    CHECK = "check"
    NOT_NULL = "not_null"
    DEFAULT = "default"

class ColumnConstraint(DCSBase, URNMixin):
    __tablename__ = "column_constraints"

    column_id: Mapped[UUID] = mapped_column(
        ForeignKey("columns.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    constraint_type: Mapped[str] = mapped_column(String(50), nullable=False)
    constraint_name: Mapped[Optional[str]] = mapped_column(String(255))

    # Foreign key references
    referenced_table_urn: Mapped[Optional[str]] = mapped_column(String(500))
    referenced_column_urn: Mapped[Optional[str]] = mapped_column(String(500))
    on_delete_action: Mapped[Optional[str]] = mapped_column(String(50))
    on_update_action: Mapped[Optional[str]] = mapped_column(String(50))

    # Check constraints
    check_expression: Mapped[Optional[str]] = mapped_column(Text)

    # Default constraints
    default_value: Mapped[Optional[str]] = mapped_column(Text)
    default_expression: Mapped[Optional[str]] = mapped_column(Text)

    # Enforcement
    is_enforced: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deferrable: Mapped[bool] = mapped_column(Boolean, default=False)

    meta: Mapped[dict] = mapped_column(JSONType(), default=dict)

    # Relationships
    column: Mapped["Column"] = relationship(back_populates="constraints")
```

#### 2.2.2 New Table: `capsule_indexes`

```sql
CREATE TABLE dcs.capsule_indexes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capsule_id          UUID NOT NULL REFERENCES dcs.capsules(id) ON DELETE CASCADE,

    -- Index definition
    index_name          VARCHAR(255) NOT NULL,
    index_type          VARCHAR(50) DEFAULT 'btree',  -- 'btree', 'hash', 'gin', 'gist', 'brin'
    is_unique           BOOLEAN DEFAULT FALSE,
    is_primary          BOOLEAN DEFAULT FALSE,

    -- Columns in index (ordered)
    column_names        JSONB NOT NULL,  -- ["col1", "col2"]
    column_expressions  JSONB,           -- For expression indexes

    -- Index properties
    is_partial          BOOLEAN DEFAULT FALSE,
    partial_predicate   TEXT,            -- WHERE clause for partial index

    -- Storage
    tablespace          VARCHAR(255),
    fill_factor         INTEGER,

    -- Metadata
    meta                JSONB DEFAULT '{}',

    -- Audit
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT index_type_valid CHECK (
        index_type IN ('btree', 'hash', 'gin', 'gist', 'brin', 'spgist')
    )
);

CREATE INDEX idx_capsule_indexes_capsule ON dcs.capsule_indexes(capsule_id);
```

#### 2.2.3 Extensions to `capsules` Table

Add partitioning and physical storage metadata:

```sql
ALTER TABLE dcs.capsules
ADD COLUMN partition_strategy VARCHAR(50),  -- 'range', 'list', 'hash', 'none'
ADD COLUMN partition_key JSONB,             -- ["year", "month"]
ADD COLUMN partition_expression TEXT,       -- Partition expression
ADD COLUMN storage_format VARCHAR(50),      -- 'parquet', 'orc', 'avro', 'delta', 'iceberg'
ADD COLUMN compression VARCHAR(50),         -- 'gzip', 'snappy', 'zstd', 'lz4'
ADD COLUMN table_size_bytes BIGINT,
ADD COLUMN row_count BIGINT,
ADD COLUMN last_analyzed_at TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN dcs.capsules.partition_strategy IS 'Partitioning strategy for large tables';
COMMENT ON COLUMN dcs.capsules.storage_format IS 'Physical storage format (parquet, delta, iceberg)';
```

---

## 3. Dimension 3: Semantic Metadata

### 3.1 Current State

**Existing Coverage**:
- ✅ Basic semantic types (PII, business_key, metric, etc.)
- ✅ Descriptions
- ✅ Tags

**Missing**:
- ❌ Business glossary terms
- ❌ Units of measurement
- ❌ Controlled vocabularies
- ❌ Domain-specific classifications
- ❌ Cross-references to business concepts

### 3.2 Proposed Extensions

#### 3.2.1 New Table: `business_terms`

```sql
CREATE TABLE dcs.business_terms (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Term definition
    term_name           VARCHAR(255) NOT NULL UNIQUE,
    display_name        VARCHAR(255),
    definition          TEXT NOT NULL,
    abbreviation        VARCHAR(50),
    synonyms            JSONB DEFAULT '[]',  -- ["alt_name1", "alt_name2"]

    -- Categorization
    domain_id           UUID REFERENCES dcs.domains(id),
    category            VARCHAR(100),        -- 'financial', 'operational', 'customer'

    -- Ownership
    owner_id            UUID REFERENCES dcs.owners(id),
    steward_email       VARCHAR(255),

    -- Governance
    approval_status     VARCHAR(50) DEFAULT 'draft',  -- 'draft', 'approved', 'deprecated'
    approved_by         VARCHAR(255),
    approved_at         TIMESTAMP WITH TIME ZONE,

    -- Metadata
    meta                JSONB DEFAULT '{}',
    tags                JSONB DEFAULT '[]',

    -- Audit
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT approval_status_valid CHECK (
        approval_status IN ('draft', 'under_review', 'approved', 'deprecated')
    )
);

CREATE INDEX idx_business_terms_domain ON dcs.business_terms(domain_id);
CREATE INDEX idx_business_terms_category ON dcs.business_terms(category);
CREATE INDEX idx_business_terms_status ON dcs.business_terms(approval_status);
CREATE INDEX idx_business_terms_search ON dcs.business_terms
    USING GIN (to_tsvector('english', term_name || ' ' || definition));
```

#### 3.2.2 New Table: `capsule_business_terms`

Link capsules/columns to business terms:

```sql
CREATE TABLE dcs.capsule_business_terms (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Subject (one of these)
    capsule_id          UUID REFERENCES dcs.capsules(id) ON DELETE CASCADE,
    column_id           UUID REFERENCES dcs.columns(id) ON DELETE CASCADE,

    -- Business term
    term_id             UUID NOT NULL REFERENCES dcs.business_terms(id) ON DELETE CASCADE,

    -- Relationship type
    relationship_type   VARCHAR(50) DEFAULT 'implements',  -- 'implements', 'related_to', 'example_of'

    -- Context
    added_by            VARCHAR(255),
    added_at            TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    meta                JSONB DEFAULT '{}',

    CONSTRAINT has_subject CHECK (
        (capsule_id IS NOT NULL)::int + (column_id IS NOT NULL)::int = 1
    )
);

CREATE INDEX idx_capsule_business_terms_capsule ON dcs.capsule_business_terms(capsule_id)
    WHERE capsule_id IS NOT NULL;
CREATE INDEX idx_capsule_business_terms_column ON dcs.capsule_business_terms(column_id)
    WHERE column_id IS NOT NULL;
CREATE INDEX idx_capsule_business_terms_term ON dcs.capsule_business_terms(term_id);
```

#### 3.2.3 Extensions to `columns` Table

Add units and value domains:

```sql
ALTER TABLE dcs.columns
ADD COLUMN unit_of_measure VARCHAR(100),     -- 'USD', 'meters', 'seconds', 'percentage'
ADD COLUMN value_domain VARCHAR(100),        -- Reference to controlled vocabulary
ADD COLUMN value_range_min NUMERIC,
ADD COLUMN value_range_max NUMERIC,
ADD COLUMN allowed_values JSONB,             -- ["active", "inactive", "pending"]
ADD COLUMN format_pattern VARCHAR(255),      -- Regex or format string
ADD COLUMN example_values JSONB DEFAULT '[]';

COMMENT ON COLUMN dcs.columns.unit_of_measure IS 'Physical unit or currency (ISO 4217, SI units)';
COMMENT ON COLUMN dcs.columns.value_domain IS 'Reference to controlled vocabulary or enum type';
COMMENT ON COLUMN dcs.columns.allowed_values IS 'Enumerated list of valid values';
COMMENT ON COLUMN dcs.columns.format_pattern IS 'Expected format (e.g., "YYYY-MM-DD", "[A-Z]{3}-[0-9]{4}")';
```

#### 3.2.4 New Table: `value_domains`

Controlled vocabularies:

```sql
CREATE TABLE dcs.value_domains (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Domain definition
    domain_name         VARCHAR(255) NOT NULL UNIQUE,
    domain_type         VARCHAR(50) NOT NULL,  -- 'enum', 'pattern', 'range', 'reference_data'
    description         TEXT,

    -- For enum domains
    allowed_values      JSONB,  -- [{"code": "A", "label": "Active", "description": "..."}]

    -- For pattern domains
    pattern_regex       TEXT,
    pattern_description TEXT,

    -- For range domains
    min_value           NUMERIC,
    max_value           NUMERIC,

    -- For reference data domains
    reference_table_urn VARCHAR(500),
    reference_column_urn VARCHAR(500),

    -- Governance
    owner_id            UUID REFERENCES dcs.owners(id),
    is_extensible       BOOLEAN DEFAULT FALSE,  -- Can new values be added?

    -- Metadata
    meta                JSONB DEFAULT '{}',

    -- Audit
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_value_domains_type ON dcs.value_domains(domain_type);
```

---

## 4. Dimension 4: Quality Expectations

### 4.1 Current State

**Existing Coverage**:
- ✅ Test count flags (`has_tests`, `test_count`)
- ✅ Basic stats in JSONB
- ✅ Violation tracking

**Missing**:
- ❌ Detailed quality rules
- ❌ Expected distributions
- ❌ Thresholds and bounds
- ❌ Anomaly detection config
- ❌ Data profiling metadata

### 4.2 Proposed Extensions

#### 4.2.1 New Table: `quality_rules`

Detailed quality expectations at column level:

```sql
CREATE TABLE dcs.quality_rules (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Subject
    capsule_id          UUID REFERENCES dcs.capsules(id) ON DELETE CASCADE,
    column_id           UUID REFERENCES dcs.columns(id) ON DELETE CASCADE,

    -- Rule definition
    rule_name           VARCHAR(255) NOT NULL,
    rule_type           VARCHAR(50) NOT NULL,  -- See enum below
    rule_category       VARCHAR(50),           -- 'completeness', 'validity', 'consistency', 'timeliness', 'accuracy'

    -- Rule parameters (flexible)
    rule_config         JSONB NOT NULL,

    -- Thresholds
    threshold_value     NUMERIC,
    threshold_operator  VARCHAR(20),           -- '>', '>=', '<', '<=', '=', '!='
    threshold_percent   NUMERIC,               -- For percentage-based rules

    -- Expected values
    expected_value      TEXT,
    expected_range_min  NUMERIC,
    expected_range_max  NUMERIC,
    expected_pattern    TEXT,

    -- Severity
    severity            VARCHAR(20) DEFAULT 'warning',
    blocking            BOOLEAN DEFAULT FALSE,  -- Block pipeline if fails?

    -- Status
    is_enabled          BOOLEAN DEFAULT TRUE,

    -- Metadata
    description         TEXT,
    meta                JSONB DEFAULT '{}',

    -- Audit
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT has_subject CHECK (
        (capsule_id IS NOT NULL)::int + (column_id IS NOT NULL)::int = 1
    ),
    CONSTRAINT rule_type_valid CHECK (
        rule_type IN (
            -- Completeness
            'not_null', 'no_empty_strings', 'completeness_threshold',
            -- Validity
            'value_in_set', 'pattern_match', 'format_valid', 'type_valid',
            'range_check', 'length_check',
            -- Uniqueness
            'unique', 'unique_combination', 'duplicate_threshold',
            -- Consistency
            'referential_integrity', 'cross_field_validation',
            -- Timeliness
            'freshness', 'recency_check',
            -- Distribution
            'distribution_check', 'outlier_detection', 'statistical_threshold',
            -- Custom
            'custom_sql', 'custom_function'
        )
    )
);

CREATE INDEX idx_quality_rules_capsule ON dcs.quality_rules(capsule_id) WHERE capsule_id IS NOT NULL;
CREATE INDEX idx_quality_rules_column ON dcs.quality_rules(column_id) WHERE column_id IS NOT NULL;
CREATE INDEX idx_quality_rules_type ON dcs.quality_rules(rule_type);
CREATE INDEX idx_quality_rules_enabled ON dcs.quality_rules(is_enabled) WHERE is_enabled = TRUE;
```

**Example rule_config JSONB structures**:

```json
// Completeness rule
{
  "rule_type": "completeness_threshold",
  "threshold_percent": 95.0,
  "allow_null": false,
  "allow_empty": false
}

// Value in set
{
  "rule_type": "value_in_set",
  "allowed_values": ["active", "inactive", "pending"],
  "case_sensitive": false
}

// Pattern match
{
  "rule_type": "pattern_match",
  "pattern": "^[A-Z]{3}-[0-9]{4}$",
  "pattern_description": "Format: AAA-9999"
}

// Distribution check
{
  "rule_type": "distribution_check",
  "expected_distribution": "normal",
  "mean": 100.0,
  "std_dev": 15.0,
  "tolerance": 0.1
}

// Outlier detection
{
  "rule_type": "outlier_detection",
  "method": "iqr",  // 'iqr', 'z_score', 'isolation_forest'
  "sensitivity": 1.5,
  "max_outlier_percent": 5.0
}
```

#### 4.2.2 New Table: `column_profiles`

Statistical profiling metadata:

```sql
CREATE TABLE dcs.column_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    column_id           UUID NOT NULL REFERENCES dcs.columns(id) ON DELETE CASCADE,

    -- Basic statistics
    total_count         BIGINT,
    null_count          BIGINT,
    null_percentage     NUMERIC(5,2),
    distinct_count      BIGINT,
    unique_percentage   NUMERIC(5,2),

    -- For numeric columns
    min_value           NUMERIC,
    max_value           NUMERIC,
    mean_value          NUMERIC,
    median_value        NUMERIC,
    std_dev             NUMERIC,
    variance            NUMERIC,
    percentile_25       NUMERIC,
    percentile_75       NUMERIC,

    -- For string columns
    min_length          INTEGER,
    max_length          INTEGER,
    avg_length          NUMERIC,

    -- For all columns
    most_common_values  JSONB,  -- [{"value": "foo", "count": 100, "percentage": 10.5}]
    value_distribution  JSONB,  -- Histogram or frequency distribution

    -- Pattern analysis
    detected_patterns   JSONB,  -- [{"pattern": "^[A-Z]{3}$", "match_count": 50}]

    -- Temporal patterns (for timestamps)
    earliest_timestamp  TIMESTAMP WITH TIME ZONE,
    latest_timestamp    TIMESTAMP WITH TIME ZONE,

    -- Data quality indicators
    completeness_score  NUMERIC(5,2),  -- 0-100
    validity_score      NUMERIC(5,2),
    uniqueness_score    NUMERIC(5,2),

    -- Profiling metadata
    profiled_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    profiled_by         VARCHAR(255),  -- Job or tool name
    sample_size         BIGINT,
    sample_percentage   NUMERIC(5,2),

    -- Metadata
    meta                JSONB DEFAULT '{}',

    CONSTRAINT column_profiles_unique_latest UNIQUE (column_id, profiled_at)
);

CREATE INDEX idx_column_profiles_column ON dcs.column_profiles(column_id);
CREATE INDEX idx_column_profiles_profiled_at ON dcs.column_profiles(profiled_at DESC);
```

#### 4.2.3 New Table: `quality_checks`

Track quality check executions:

```sql
CREATE TABLE dcs.quality_checks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What was checked
    quality_rule_id     UUID NOT NULL REFERENCES dcs.quality_rules(id) ON DELETE CASCADE,
    capsule_id          UUID REFERENCES dcs.capsules(id),
    column_id           UUID REFERENCES dcs.columns(id),

    -- Check execution
    check_timestamp     TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    check_status        VARCHAR(20) NOT NULL,  -- 'passed', 'failed', 'warning', 'error', 'skipped'

    -- Results
    actual_value        TEXT,
    expected_value      TEXT,
    threshold_value     NUMERIC,
    measured_value      NUMERIC,

    -- Failure details
    failure_count       INTEGER,
    failure_percentage  NUMERIC(5,2),
    sample_failures     JSONB,  -- Sample of failing records

    -- Execution metadata
    execution_context   JSONB,  -- Pipeline run, job ID, etc.
    execution_duration_ms INTEGER,

    -- Metadata
    meta                JSONB DEFAULT '{}',

    CONSTRAINT check_status_valid CHECK (
        check_status IN ('passed', 'failed', 'warning', 'error', 'skipped')
    )
);

CREATE INDEX idx_quality_checks_rule ON dcs.quality_checks(quality_rule_id);
CREATE INDEX idx_quality_checks_timestamp ON dcs.quality_checks(check_timestamp DESC);
CREATE INDEX idx_quality_checks_status ON dcs.quality_checks(check_status);
```

---

## 5. Dimension 5: Policy Metadata

### 5.1 Current State

**Existing Coverage**:
- ✅ PII type classification
- ✅ Sensitivity levels in tags
- ✅ Owner tracking

**Missing**:
- ❌ Retention policies
- ❌ Masking/anonymization rules
- ❌ Geographic restrictions
- ❌ Access policies
- ❌ Approved use cases
- ❌ Compliance frameworks

### 5.2 Proposed Extensions

#### 5.2.1 New Table: `data_policies`

Comprehensive policy metadata:

```sql
CREATE TABLE dcs.data_policies (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Subject (one of these)
    capsule_id          UUID REFERENCES dcs.capsules(id) ON DELETE CASCADE,
    column_id           UUID REFERENCES dcs.columns(id) ON DELETE CASCADE,

    -- Classification
    sensitivity_level   VARCHAR(50) NOT NULL,  -- 'public', 'internal', 'confidential', 'restricted', 'secret'
    classification_tags JSONB DEFAULT '[]',    -- ['gdpr', 'pci', 'hipaa', 'ccpa']

    -- Retention policy
    retention_period    INTERVAL,              -- e.g., '7 years'
    retention_start     VARCHAR(50),           -- 'ingestion', 'last_modified', 'business_date'
    deletion_action     VARCHAR(50),           -- 'hard_delete', 'anonymize', 'archive'
    legal_hold          BOOLEAN DEFAULT FALSE,

    -- Geographic restrictions
    allowed_regions     JSONB DEFAULT '[]',    -- ['EU', 'US', 'CA']
    restricted_regions  JSONB DEFAULT '[]',    -- ['CN', 'RU']
    data_residency      VARCHAR(50),           -- 'EU', 'US', 'multi_region'
    cross_border_transfer BOOLEAN DEFAULT TRUE,

    -- Access control
    min_access_level    VARCHAR(50),           -- 'public', 'authenticated', 'privileged', 'admin'
    allowed_roles       JSONB DEFAULT '[]',    -- ['data_analyst', 'data_scientist']
    denied_roles        JSONB DEFAULT '[]',

    -- Approved uses
    approved_purposes   JSONB DEFAULT '[]',    -- ['analytics', 'ml_training', 'reporting']
    prohibited_purposes JSONB DEFAULT '[]',    -- ['marketing', 'profiling']

    -- Masking/anonymization
    requires_masking    BOOLEAN DEFAULT FALSE,
    masking_method      VARCHAR(50),           -- 'hash', 'tokenize', 'redact', 'encrypt', 'pseudonymize'
    masking_conditions  JSONB,                 -- Conditions when masking applies

    -- Encryption
    encryption_required BOOLEAN DEFAULT FALSE,
    encryption_method   VARCHAR(50),           -- 'aes256', 'rsa', 'field_level'
    encryption_at_rest  BOOLEAN DEFAULT FALSE,
    encryption_in_transit BOOLEAN DEFAULT TRUE,

    -- Compliance tracking
    compliance_frameworks JSONB DEFAULT '[]',  -- ['GDPR', 'CCPA', 'HIPAA', 'PCI-DSS']
    consent_required    BOOLEAN DEFAULT FALSE,
    right_to_erasure    BOOLEAN DEFAULT FALSE,  -- GDPR Article 17

    -- Audit requirements
    audit_log_required  BOOLEAN DEFAULT FALSE,
    audit_retention_period INTERVAL,

    -- Governance
    policy_owner_id     UUID REFERENCES dcs.owners(id),
    approved_by         VARCHAR(255),
    approved_at         TIMESTAMP WITH TIME ZONE,
    review_frequency    INTERVAL,              -- e.g., '1 year'
    last_reviewed_at    TIMESTAMP WITH TIME ZONE,
    next_review_date    DATE,

    -- Status
    policy_status       VARCHAR(50) DEFAULT 'active',
    effective_from      DATE,
    effective_to        DATE,

    -- Metadata
    meta                JSONB DEFAULT '{}',

    -- Audit
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT has_subject CHECK (
        (capsule_id IS NOT NULL)::int + (column_id IS NOT NULL)::int = 1
    ),
    CONSTRAINT sensitivity_level_valid CHECK (
        sensitivity_level IN ('public', 'internal', 'confidential', 'restricted', 'secret')
    ),
    CONSTRAINT policy_status_valid CHECK (
        policy_status IN ('draft', 'active', 'deprecated', 'suspended')
    )
);

CREATE INDEX idx_data_policies_capsule ON dcs.data_policies(capsule_id) WHERE capsule_id IS NOT NULL;
CREATE INDEX idx_data_policies_column ON dcs.data_policies(column_id) WHERE column_id IS NOT NULL;
CREATE INDEX idx_data_policies_sensitivity ON dcs.data_policies(sensitivity_level);
CREATE INDEX idx_data_policies_classification ON dcs.data_policies USING GIN (classification_tags);
CREATE INDEX idx_data_policies_review ON dcs.data_policies(next_review_date) WHERE policy_status = 'active';
```

#### 5.2.2 New Table: `masking_rules`

Detailed masking/anonymization rules:

```sql
CREATE TABLE dcs.masking_rules (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    column_id           UUID NOT NULL REFERENCES dcs.columns(id) ON DELETE CASCADE,

    -- Rule definition
    rule_name           VARCHAR(255) NOT NULL,
    masking_method      VARCHAR(50) NOT NULL,

    -- Method-specific configuration
    method_config       JSONB NOT NULL,

    -- Conditional masking
    apply_condition     TEXT,               -- SQL WHERE clause
    applies_to_roles    JSONB DEFAULT '[]', -- Roles that see masked data
    exempt_roles        JSONB DEFAULT '[]', -- Roles that see unmasked data

    -- Preservation options
    preserve_length     BOOLEAN DEFAULT FALSE,
    preserve_format     BOOLEAN DEFAULT FALSE,
    preserve_type       BOOLEAN DEFAULT TRUE,
    preserve_null       BOOLEAN DEFAULT TRUE,

    -- Reversibility
    is_reversible       BOOLEAN DEFAULT FALSE,
    tokenization_vault  VARCHAR(255),  -- Reference to token vault

    -- Status
    is_enabled          BOOLEAN DEFAULT TRUE,

    -- Metadata
    description         TEXT,
    meta                JSONB DEFAULT '{}',

    -- Audit
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT masking_method_valid CHECK (
        masking_method IN (
            'redaction', 'partial_redaction', 'substitution',
            'hashing', 'tokenization', 'encryption',
            'pseudonymization', 'generalization', 'noise_addition',
            'format_preserving_encryption', 'data_masking',
            'custom'
        )
    )
);

CREATE INDEX idx_masking_rules_column ON dcs.masking_rules(column_id);
CREATE INDEX idx_masking_rules_enabled ON dcs.masking_rules(is_enabled) WHERE is_enabled = TRUE;
```

**Example method_config structures**:

```json
// Redaction
{
  "masking_method": "redaction",
  "redaction_char": "*",
  "full_redaction": true
}

// Partial redaction (email)
{
  "masking_method": "partial_redaction",
  "preserve_prefix": 2,
  "preserve_suffix": 0,
  "preserve_domain": true,
  "redaction_char": "*"
}

// Hashing
{
  "masking_method": "hashing",
  "algorithm": "sha256",
  "salt": "use_system_salt",
  "pepper": true
}

// Tokenization
{
  "masking_method": "tokenization",
  "vault_id": "prod_vault_1",
  "preserve_format": true,
  "deterministic": true
}
```

---

## 6. Dimension 6: Provenance Enhancements

### 6.1 Current State

**Existing Coverage**:
- ✅ Capsule lineage (FLOWS_TO)
- ✅ Column lineage (DERIVED_FROM)
- ✅ Ingestion job tracking
- ✅ URN-based stable identifiers

**Missing**:
- ❌ Dataset versioning
- ❌ Schema evolution tracking
- ❌ Transformation code capture
- ❌ Data lineage at runtime (execution provenance)

### 6.2 Proposed Extensions

#### 6.2.1 New Table: `capsule_versions`

Track capsule evolution over time:

```sql
CREATE TABLE dcs.capsule_versions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capsule_id          UUID NOT NULL REFERENCES dcs.capsules(id) ON DELETE CASCADE,

    -- Version identification
    version_number      INTEGER NOT NULL,
    version_name        VARCHAR(100),  -- e.g., 'v1.2.0', 'SNAPSHOT'
    version_hash        VARCHAR(64),   -- Content hash

    -- Schema snapshot
    schema_snapshot     JSONB NOT NULL,  -- Full schema at this version

    -- Change tracking
    change_type         VARCHAR(50),     -- 'created', 'schema_change', 'deleted', 'metadata_change'
    change_summary      TEXT,
    breaking_change     BOOLEAN DEFAULT FALSE,

    -- Lineage snapshot
    upstream_capsule_urns JSONB DEFAULT '[]',
    downstream_capsule_urns JSONB DEFAULT '[]',

    -- Deployment
    deployed_at         TIMESTAMP WITH TIME ZONE,
    deployed_by         VARCHAR(255),
    deployment_context  JSONB,  -- CI/CD pipeline, git commit, etc.

    -- Git integration
    git_commit_sha      VARCHAR(40),
    git_branch          VARCHAR(255),
    git_tag             VARCHAR(255),
    git_repository      VARCHAR(500),

    -- Status
    is_current          BOOLEAN DEFAULT FALSE,  -- Latest version?

    -- Metadata
    meta                JSONB DEFAULT '{}',

    -- Audit
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT capsule_version_unique UNIQUE (capsule_id, version_number)
);

CREATE INDEX idx_capsule_versions_capsule ON dcs.capsule_versions(capsule_id);
CREATE INDEX idx_capsule_versions_current ON dcs.capsule_versions(capsule_id, is_current)
    WHERE is_current = TRUE;
CREATE INDEX idx_capsule_versions_created ON dcs.capsule_versions(created_at DESC);
```

#### 6.2.2 New Table: `transformation_code`

Capture transformation logic:

```sql
CREATE TABLE dcs.transformation_code (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What it transforms
    capsule_id          UUID REFERENCES dcs.capsules(id) ON DELETE CASCADE,
    lineage_edge_id     UUID REFERENCES dcs.capsule_lineage(id) ON DELETE CASCADE,

    -- Code
    language            VARCHAR(50) NOT NULL,  -- 'sql', 'python', 'spark_sql', 'dbt'
    code_text           TEXT NOT NULL,
    code_hash           VARCHAR(64),

    -- Code metadata
    function_name       VARCHAR(255),
    file_path           VARCHAR(500),
    line_start          INTEGER,
    line_end            INTEGER,

    -- Git context
    git_commit_sha      VARCHAR(40),
    git_repository      VARCHAR(500),

    -- Dependencies
    upstream_references JSONB DEFAULT '[]',  -- Tables/columns referenced
    function_calls      JSONB DEFAULT '[]',  -- UDFs called

    -- Metadata
    meta                JSONB DEFAULT '{}',

    -- Audit
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT has_subject CHECK (
        (capsule_id IS NOT NULL)::int + (lineage_edge_id IS NOT NULL)::int = 1
    )
);

CREATE INDEX idx_transformation_code_capsule ON dcs.transformation_code(capsule_id)
    WHERE capsule_id IS NOT NULL;
CREATE INDEX idx_transformation_code_edge ON dcs.transformation_code(lineage_edge_id)
    WHERE lineage_edge_id IS NOT NULL;
```

#### 6.2.3 Extensions to `ingestion_jobs` Table

Add runtime provenance:

```sql
ALTER TABLE dcs.ingestion_jobs
ADD COLUMN execution_environment JSONB,  -- {'platform': 'airflow', 'cluster': 'prod', ...}
ADD COLUMN execution_duration_ms BIGINT,
ADD COLUMN records_processed BIGINT,
ADD COLUMN bytes_processed BIGINT,
ADD COLUMN execution_logs_url TEXT,
ADD COLUMN triggered_by VARCHAR(255),    -- User, schedule, event
ADD COLUMN parent_job_id UUID REFERENCES dcs.ingestion_jobs(id);

COMMENT ON COLUMN dcs.ingestion_jobs.execution_environment IS 'Runtime environment metadata (Airflow, Spark, etc.)';
COMMENT ON COLUMN dcs.ingestion_jobs.parent_job_id IS 'Parent job if this is a sub-job or retry';
```

---

## 7. Dimension 7: Operational Contracts

### 7.1 Current State

**Existing Coverage**:
- ✅ SLOs at data product level (freshness, availability, quality)
- ✅ Owner tracking
- ✅ Domain organization

**Missing**:
- ❌ Capsule-level SLAs
- ❌ Completeness guarantees
- ❌ Update schedules
- ❌ Breaking change notification
- ❌ Deprecation policies

### 7.2 Proposed Extensions

#### 7.2.1 New Table: `capsule_contracts`

Service-level agreements for capsules:

```sql
CREATE TABLE dcs.capsule_contracts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capsule_id          UUID NOT NULL REFERENCES dcs.capsules(id) ON DELETE CASCADE,

    -- Contract metadata
    contract_version    VARCHAR(50) NOT NULL,
    contract_status     VARCHAR(50) DEFAULT 'active',

    -- Freshness SLA
    freshness_sla       INTERVAL,              -- e.g., '4 hours'
    freshness_schedule  VARCHAR(100),          -- 'hourly', 'daily_8am', 'cron:0 8 * * *'
    last_updated_at     TIMESTAMP WITH TIME ZONE,

    -- Completeness SLA
    completeness_sla    NUMERIC(5,2),          -- Expected % of records (e.g., 99.9)
    expected_row_count_min BIGINT,
    expected_row_count_max BIGINT,

    -- Availability SLA
    availability_sla    NUMERIC(5,2),          -- Uptime % (e.g., 99.9)
    max_downtime        INTERVAL,              -- e.g., '1 hour per month'

    -- Quality SLA
    quality_score_sla   NUMERIC(5,2),          -- Min quality score (0-100)
    critical_quality_rules JSONB DEFAULT '[]', -- Rules that must pass

    -- Latency SLA
    query_latency_p95   INTEGER,               -- P95 query latency in ms
    query_latency_p99   INTEGER,

    -- Schema stability
    schema_change_policy VARCHAR(50),          -- 'strict', 'backwards_compatible', 'flexible'
    breaking_change_notice_days INTEGER,       -- Days of notice before breaking change

    -- Support
    support_level       VARCHAR(50),           -- 'best_effort', 'business_hours', '24x7', 'critical'
    support_contact     VARCHAR(255),
    support_slack_channel VARCHAR(100),
    support_oncall      VARCHAR(255),

    -- Maintenance windows
    maintenance_windows JSONB DEFAULT '[]',    -- [{"day": "sunday", "start": "02:00", "end": "04:00"}]

    -- Deprecation
    deprecation_policy  VARCHAR(50),           -- 'immediate', '30_days', '90_days', 'never'
    deprecation_date    DATE,
    replacement_capsule_urn VARCHAR(500),

    -- Consumers
    known_consumers     JSONB DEFAULT '[]',    -- [{"team": "analytics", "contact": "..."}]
    consumer_notification_required BOOLEAN DEFAULT TRUE,

    -- Performance targets
    target_row_count    BIGINT,
    target_size_bytes   BIGINT,
    target_column_count INTEGER,

    -- Cost allocation
    cost_center         VARCHAR(100),
    billing_tags        JSONB DEFAULT '{}',

    -- Metadata
    meta                JSONB DEFAULT '{}',

    -- Governance
    contract_owner_id   UUID REFERENCES dcs.owners(id),
    approved_by         VARCHAR(255),
    approved_at         TIMESTAMP WITH TIME ZONE,

    -- Audit
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT contract_status_valid CHECK (
        contract_status IN ('draft', 'proposed', 'active', 'deprecated', 'breached')
    ),
    CONSTRAINT schema_change_policy_valid CHECK (
        schema_change_policy IN ('strict', 'backwards_compatible', 'flexible', 'unrestricted')
    ),
    CONSTRAINT support_level_valid CHECK (
        support_level IN ('none', 'best_effort', 'business_hours', '24x7', 'critical')
    )
);

CREATE INDEX idx_capsule_contracts_capsule ON dcs.capsule_contracts(capsule_id);
CREATE INDEX idx_capsule_contracts_status ON dcs.capsule_contracts(contract_status);
CREATE INDEX idx_capsule_contracts_deprecation ON dcs.capsule_contracts(deprecation_date)
    WHERE deprecation_date IS NOT NULL;
```

#### 7.2.2 New Table: `sla_incidents`

Track SLA violations:

```sql
CREATE TABLE dcs.sla_incidents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Contract reference
    contract_id         UUID NOT NULL REFERENCES dcs.capsule_contracts(id) ON DELETE CASCADE,
    capsule_id          UUID NOT NULL REFERENCES dcs.capsules(id) ON DELETE CASCADE,

    -- Incident details
    incident_type       VARCHAR(50) NOT NULL,  -- 'freshness', 'completeness', 'availability', 'quality'
    incident_severity   VARCHAR(20) DEFAULT 'medium',

    -- What was violated
    sla_target          NUMERIC,
    actual_value        NUMERIC,
    breach_magnitude    NUMERIC,  -- How much SLA was missed by

    -- Timeline
    detected_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    breach_started_at   TIMESTAMP WITH TIME ZONE,
    breach_ended_at     TIMESTAMP WITH TIME ZONE,
    breach_duration     INTERVAL,

    -- Impact
    affected_consumers  JSONB DEFAULT '[]',
    downstream_impact   TEXT,

    -- Resolution
    incident_status     VARCHAR(50) DEFAULT 'open',
    resolution          TEXT,
    resolved_by         VARCHAR(255),
    resolved_at         TIMESTAMP WITH TIME ZONE,

    -- Root cause
    root_cause          TEXT,
    root_cause_category VARCHAR(50),  -- 'pipeline_failure', 'data_quality', 'infrastructure', 'dependency'

    -- Metadata
    meta                JSONB DEFAULT '{}',

    CONSTRAINT incident_type_valid CHECK (
        incident_type IN ('freshness', 'completeness', 'availability', 'quality', 'latency', 'schema_change')
    ),
    CONSTRAINT incident_status_valid CHECK (
        incident_status IN ('open', 'investigating', 'mitigated', 'resolved', 'closed', 'false_positive')
    )
);

CREATE INDEX idx_sla_incidents_contract ON dcs.sla_incidents(contract_id);
CREATE INDEX idx_sla_incidents_capsule ON dcs.sla_incidents(capsule_id);
CREATE INDEX idx_sla_incidents_detected ON dcs.sla_incidents(detected_at DESC);
CREATE INDEX idx_sla_incidents_status ON dcs.sla_incidents(incident_status);
```

---

## 8. Cross-Cutting Concerns

### 8.1 Versioning Strategy

All metadata should be versioned alongside capsules:

```sql
-- Add version tracking to key tables
ALTER TABLE dcs.column_constraints ADD COLUMN capsule_version_id UUID
    REFERENCES dcs.capsule_versions(id);
ALTER TABLE dcs.quality_rules ADD COLUMN capsule_version_id UUID
    REFERENCES dcs.capsule_versions(id);
ALTER TABLE dcs.data_policies ADD COLUMN capsule_version_id UUID
    REFERENCES dcs.capsule_versions(id);
```

### 8.2 Change Data Capture (CDC)

Implement audit logging for all metadata changes:

```sql
CREATE TABLE dcs.metadata_audit_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What changed
    table_name          VARCHAR(100) NOT NULL,
    record_id           UUID NOT NULL,

    -- Change details
    operation           VARCHAR(20) NOT NULL,  -- 'INSERT', 'UPDATE', 'DELETE'
    old_values          JSONB,
    new_values          JSONB,
    changed_fields      JSONB DEFAULT '[]',

    -- Who and when
    changed_by          VARCHAR(255),
    changed_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    change_reason       TEXT,

    -- Context
    session_id          VARCHAR(100),
    application         VARCHAR(100),
    ip_address          INET,

    CONSTRAINT operation_valid CHECK (
        operation IN ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE')
    )
);

CREATE INDEX idx_metadata_audit_log_table ON dcs.metadata_audit_log(table_name, record_id);
CREATE INDEX idx_metadata_audit_log_changed_at ON dcs.metadata_audit_log(changed_at DESC);
```

### 8.3 Data Catalog Views

Create materialized views for catalog queries:

```sql
CREATE MATERIALIZED VIEW dcs.catalog_capsule_summary AS
SELECT
    c.id,
    c.urn,
    c.name,
    c.capsule_type,
    c.layer,
    c.description,

    -- Structural
    COUNT(DISTINCT col.id) as column_count,
    COUNT(DISTINCT idx.id) as index_count,
    COUNT(DISTINCT cc.id) FILTER (WHERE cc.constraint_type = 'primary_key') as pk_count,
    COUNT(DISTINCT cc.id) FILTER (WHERE cc.constraint_type = 'foreign_key') as fk_count,

    -- Semantic
    COUNT(DISTINCT cbt.term_id) as business_term_count,

    -- Quality
    COUNT(DISTINCT qr.id) as quality_rule_count,
    COUNT(DISTINCT qr.id) FILTER (WHERE qr.is_enabled = TRUE) as enabled_quality_rule_count,

    -- Policy
    MAX(dp.sensitivity_level) as highest_sensitivity,
    bool_or(dp.requires_masking) as has_masking,

    -- Contract
    cc.freshness_sla,
    cc.quality_score_sla,
    cc.contract_status,

    -- Lineage
    COUNT(DISTINCT clu.source_id) as upstream_count,
    COUNT(DISTINCT cld.target_id) as downstream_count,

    c.created_at,
    c.updated_at

FROM dcs.capsules c
LEFT JOIN dcs.columns col ON col.capsule_id = c.id
LEFT JOIN dcs.capsule_indexes idx ON idx.capsule_id = c.id
LEFT JOIN dcs.column_constraints cc ON cc.column_id = col.id
LEFT JOIN dcs.capsule_business_terms cbt ON cbt.capsule_id = c.id
LEFT JOIN dcs.quality_rules qr ON qr.capsule_id = c.id
LEFT JOIN dcs.data_policies dp ON dp.capsule_id = c.id
LEFT JOIN dcs.capsule_contracts cc ON cc.capsule_id = c.id
LEFT JOIN dcs.capsule_lineage clu ON clu.target_id = c.id
LEFT JOIN dcs.capsule_lineage cld ON cld.source_id = c.id

GROUP BY c.id, cc.freshness_sla, cc.quality_score_sla, cc.contract_status;

CREATE UNIQUE INDEX idx_catalog_capsule_summary_id ON dcs.catalog_capsule_summary(id);
CREATE INDEX idx_catalog_capsule_summary_layer ON dcs.catalog_capsule_summary(layer);
```

### 8.4 API Endpoints

New FastAPI endpoints needed:

```python
# Structural metadata
GET  /api/v1/capsules/{urn}/constraints
POST /api/v1/capsules/{urn}/constraints
GET  /api/v1/capsules/{urn}/indexes

# Semantic metadata
GET  /api/v1/business-terms
POST /api/v1/business-terms
GET  /api/v1/capsules/{urn}/business-terms
POST /api/v1/capsules/{urn}/business-terms/{term_id}

# Quality
GET  /api/v1/capsules/{urn}/quality-rules
POST /api/v1/capsules/{urn}/quality-rules
GET  /api/v1/columns/{urn}/profile
POST /api/v1/quality-checks  # Execute check

# Policies
GET  /api/v1/capsules/{urn}/policies
POST /api/v1/capsules/{urn}/policies
GET  /api/v1/columns/{urn}/masking-rules
POST /api/v1/columns/{urn}/masking-rules

# Provenance
GET  /api/v1/capsules/{urn}/versions
GET  /api/v1/capsules/{urn}/versions/{version}
GET  /api/v1/capsules/{urn}/transformation-code

# Contracts
GET  /api/v1/capsules/{urn}/contract
POST /api/v1/capsules/{urn}/contract
GET  /api/v1/capsules/{urn}/sla-incidents
POST /api/v1/sla-incidents  # Report incident
```

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- Create new tables for structural metadata (constraints, indexes)
- Extend `capsules` table with storage/partition metadata
- Update ingestion parsers to extract constraints from dbt/SQL

### Phase 2: Semantic Layer (Weeks 3-4)
- Implement business terms and value domains
- Add units and format patterns to columns
- Create business glossary UI

### Phase 3: Quality Framework (Weeks 5-7)
- Build quality rules engine
- Implement column profiling
- Create quality check execution framework
- Add quality dashboard to frontend

### Phase 4: Policy Engine (Weeks 8-10)
- Implement data policies and classifications
- Build masking rules engine
- Add policy compliance checks
- Create policy management UI

### Phase 5: Provenance & Versioning (Weeks 11-12)
- Implement capsule versioning
- Add transformation code capture
- Enhance lineage with code context
- Build version diff UI

### Phase 6: Contracts & SLAs (Weeks 13-14)
- Implement capsule contracts
- Build SLA monitoring
- Create incident tracking
- Add contract monitoring dashboard

### Phase 7: Integration & Polish (Weeks 15-16)
- Build materialized views
- Create comprehensive APIs
- Performance optimization
- Documentation and examples

---

## 10. Migration Strategy

### 10.1 Database Migrations

Use Alembic for schema migrations:

```bash
# Create migration
alembic revision -m "add_structural_metadata_tables"

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### 10.2 Data Backfill

For existing capsules, backfill metadata where possible:

```python
async def backfill_constraints_from_dbt():
    """Extract constraints from dbt manifest and populate column_constraints table."""
    # Parse manifest.json
    # For each model with primary key config
    # Create ColumnConstraint records
    pass

async def backfill_business_terms():
    """Extract business terms from descriptions using NLP."""
    # Identify key business terms in descriptions
    # Create BusinessTerm records
    # Link to capsules/columns
    pass
```

### 10.3 Backwards Compatibility

Ensure existing API endpoints continue to work:

- Add new fields as nullable
- Create views that maintain old structure
- Version API endpoints if breaking changes needed (`/api/v2/...`)

### 10.4 Testing Strategy

```python
# Unit tests for new models
def test_column_constraint_creation():
    constraint = ColumnConstraint(
        column_id=col_id,
        constraint_type="primary_key",
        is_enforced=True
    )
    assert constraint.constraint_type == ConstraintType.PRIMARY_KEY

# Integration tests for API
async def test_create_quality_rule(client):
    response = await client.post(
        f"/api/v1/capsules/{urn}/quality-rules",
        json={
            "rule_type": "not_null",
            "column_id": col_id,
            "severity": "error"
        }
    )
    assert response.status_code == 201
```

---

## Appendix A: Example Data Capsule Definition

Here's how a fully-populated data capsule would look with all 7 dimensions:

```yaml
# data_capsule_example.yml
data_capsule:
  # Identity
  urn: "urn:dcs:dbt:model:jaffle_shop.staging:stg_orders"
  name: "stg_orders"
  version: "2.1.0"

  # 1. Data Payload (external)
  location: "s3://data-lake/curated/orders/"
  format: "delta_lake"

  # 2. Structural Metadata
  schema:
    columns:
      - name: "order_id"
        data_type: "STRING"
        is_nullable: false
        constraints:
          - type: "primary_key"
          - type: "not_null"

      - name: "customer_id"
        data_type: "STRING"
        is_nullable: false
        constraints:
          - type: "foreign_key"
            references: "urn:dcs:dbt:model:jaffle_shop.staging:stg_customers.customer_id"
            on_delete: "RESTRICT"
          - type: "not_null"

      - name: "order_total"
        data_type: "DECIMAL(18,2)"
        is_nullable: false
        constraints:
          - type: "check"
            expression: "order_total >= 0"
          - type: "not_null"

    indexes:
      - name: "idx_orders_customer"
        columns: ["customer_id"]
        type: "btree"

      - name: "idx_orders_date"
        columns: ["order_date"]
        type: "btree"

  # 3. Semantic Metadata
  description: "Staged order transactions from source system"
  business_terms:
    - "revenue"
    - "transaction"
    - "customer_purchase"

  columns:
    order_total:
      unit_of_measure: "USD"
      business_definition: "Total order value including tax and shipping"
      value_domain: "currency_amount"

    order_status:
      allowed_values: ["pending", "confirmed", "shipped", "delivered", "cancelled"]
      value_domain: "order_status_enum"

  # 4. Quality Expectations
  quality_rules:
    - column: "order_id"
      rule: "unique"
      severity: "error"
      blocking: true

    - column: "order_total"
      rule: "range_check"
      min: 0
      max: 1000000
      severity: "warning"

    - capsule_level: true
      rule: "freshness"
      threshold: "4 hours"
      severity: "error"

    - column: "customer_id"
      rule: "referential_integrity"
      references: "stg_customers.customer_id"
      severity: "error"
      blocking: true

  # 5. Policy Metadata
  policies:
    classification: "internal"
    sensitivity_level: "confidential"

    retention:
      period: "7 years"
      start: "business_date"
      action: "archive"

    geographic:
      data_residency: "US"
      allowed_regions: ["US", "CA"]
      cross_border_transfer: false

    access:
      min_access_level: "authenticated"
      allowed_roles: ["data_analyst", "data_scientist", "finance_team"]

    compliance:
      frameworks: ["SOX", "GDPR"]
      audit_log_required: true
      audit_retention: "10 years"

  column_policies:
    customer_id:
      requires_masking: true
      masking_method: "tokenization"
      masking_applies_to: ["non_production", "analytics_readonly"]

  # 6. Provenance & Lineage
  lineage:
    upstream:
      - "urn:dcs:dbt:source:jaffle_shop.raw:raw_orders"
      - "urn:dcs:dbt:source:jaffle_shop.raw:raw_payments"

    transformation:
      language: "sql"
      file: "models/staging/stg_orders.sql"
      git_commit: "a1b2c3d4"
      git_repository: "github.com/org/jaffle_shop"

  version_history:
    - version: "2.1.0"
      date: "2024-12-01"
      changes: "Added order_total_usd column"
      breaking: false

    - version: "2.0.0"
      date: "2024-11-01"
      changes: "Changed order_status enum values"
      breaking: true

  # 7. Operational Contract
  contract:
    version: "1.0"

    slas:
      freshness:
        target: "4 hours"
        schedule: "hourly"

      completeness:
        target: 99.9  # percent
        min_rows: 1000
        max_rows: 1000000

      availability:
        target: 99.9  # percent
        max_downtime: "1 hour per month"

      quality:
        min_score: 95.0
        critical_rules: ["unique_order_id", "valid_customer_ref"]

    schema_changes:
      policy: "backwards_compatible"
      breaking_change_notice: 30  # days

    support:
      level: "business_hours"
      contact: "data-platform-team@company.com"
      slack: "#data-platform"

    deprecation:
      policy: "90_days"
      notice_required: true

    known_consumers:
      - team: "analytics"
        contact: "analytics@company.com"
        use_case: "Daily revenue reporting"

      - team: "ml_platform"
        contact: "ml@company.com"
        use_case: "Order prediction model"

  # Ownership
  owner:
    team: "data_platform"
    email: "data-platform@company.com"

  domain: "order_management"
  tags: ["production", "critical", "customer_facing"]
```

---

## Appendix B: SQL Examples

### Query 1: Get Full Capsule with All Metadata

```sql
WITH capsule_metadata AS (
    SELECT
        c.id,
        c.urn,
        c.name,
        c.description,

        -- Structural
        jsonb_agg(DISTINCT jsonb_build_object(
            'column', col.name,
            'type', col.data_type,
            'constraints', (
                SELECT jsonb_agg(cc.constraint_type)
                FROM dcs.column_constraints cc
                WHERE cc.column_id = col.id
            )
        )) FILTER (WHERE col.id IS NOT NULL) as schema_info,

        -- Semantic
        jsonb_agg(DISTINCT bt.term_name) FILTER (WHERE bt.id IS NOT NULL) as business_terms,

        -- Quality
        COUNT(DISTINCT qr.id) as quality_rule_count,
        AVG(qc.measured_value) as avg_quality_score,

        -- Policy
        MAX(dp.sensitivity_level) as sensitivity,
        bool_or(dp.requires_masking) as has_masking,

        -- Contract
        cont.freshness_sla,
        cont.quality_score_sla,
        cont.contract_status

    FROM dcs.capsules c
    LEFT JOIN dcs.columns col ON col.capsule_id = c.id
    LEFT JOIN dcs.capsule_business_terms cbt ON cbt.capsule_id = c.id
    LEFT JOIN dcs.business_terms bt ON bt.id = cbt.term_id
    LEFT JOIN dcs.quality_rules qr ON qr.capsule_id = c.id
    LEFT JOIN dcs.quality_checks qc ON qc.quality_rule_id = qr.id
    LEFT JOIN dcs.data_policies dp ON dp.capsule_id = c.id
    LEFT JOIN dcs.capsule_contracts cont ON cont.capsule_id = c.id

    WHERE c.urn = :capsule_urn
    GROUP BY c.id, cont.freshness_sla, cont.quality_score_sla, cont.contract_status
)
SELECT * FROM capsule_metadata;
```

### Query 2: Find Capsules with Incomplete Metadata

```sql
SELECT
    c.urn,
    c.name,

    -- Metadata completeness checks
    CASE WHEN c.description IS NULL THEN 'missing_description' END as issue_1,
    CASE WHEN col_count.total = 0 THEN 'no_columns' END as issue_2,
    CASE WHEN bt_count.total = 0 THEN 'no_business_terms' END as issue_3,
    CASE WHEN qr_count.total = 0 THEN 'no_quality_rules' END as issue_4,
    CASE WHEN dp_count.total = 0 THEN 'no_policies' END as issue_5,
    CASE WHEN cont_count.total = 0 THEN 'no_contract' END as issue_6,

    -- Completeness score
    (
        (CASE WHEN c.description IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN col_count.total > 0 THEN 1 ELSE 0 END) +
        (CASE WHEN bt_count.total > 0 THEN 1 ELSE 0 END) +
        (CASE WHEN qr_count.total > 0 THEN 1 ELSE 0 END) +
        (CASE WHEN dp_count.total > 0 THEN 1 ELSE 0 END) +
        (CASE WHEN cont_count.total > 0 THEN 1 ELSE 0 END)
    )::float / 6 * 100 as completeness_percent

FROM dcs.capsules c
LEFT JOIN (SELECT capsule_id, COUNT(*) as total FROM dcs.columns GROUP BY capsule_id) col_count
    ON col_count.capsule_id = c.id
LEFT JOIN (SELECT capsule_id, COUNT(*) as total FROM dcs.capsule_business_terms GROUP BY capsule_id) bt_count
    ON bt_count.capsule_id = c.id
LEFT JOIN (SELECT capsule_id, COUNT(*) as total FROM dcs.quality_rules GROUP BY capsule_id) qr_count
    ON qr_count.capsule_id = c.id
LEFT JOIN (SELECT capsule_id, COUNT(*) as total FROM dcs.data_policies GROUP BY capsule_id) dp_count
    ON dp_count.capsule_id = c.id
LEFT JOIN (SELECT capsule_id, COUNT(*) as total FROM dcs.capsule_contracts GROUP BY capsule_id) cont_count
    ON cont_count.capsule_id = c.id

WHERE c.layer = 'gold'  -- Focus on production assets
ORDER BY completeness_percent ASC;
```

---

## Appendix C: Pydantic Models

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class ConstraintTypeEnum(str, Enum):
    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"
    UNIQUE = "unique"
    CHECK = "check"
    NOT_NULL = "not_null"

class ColumnConstraintCreate(BaseModel):
    column_id: UUID
    constraint_type: ConstraintTypeEnum
    constraint_name: Optional[str] = None
    referenced_table_urn: Optional[str] = None
    referenced_column_urn: Optional[str] = None
    check_expression: Optional[str] = None
    is_enforced: bool = True

class BusinessTermCreate(BaseModel):
    term_name: str = Field(..., min_length=1, max_length=255)
    definition: str = Field(..., min_length=10)
    abbreviation: Optional[str] = None
    synonyms: List[str] = []
    domain_id: Optional[UUID] = None
    category: Optional[str] = None

class QualityRuleCreate(BaseModel):
    capsule_id: Optional[UUID] = None
    column_id: Optional[UUID] = None
    rule_name: str
    rule_type: str
    rule_config: dict
    severity: str = "warning"
    is_enabled: bool = True

class DataPolicyCreate(BaseModel):
    capsule_id: Optional[UUID] = None
    column_id: Optional[UUID] = None
    sensitivity_level: str
    classification_tags: List[str] = []
    retention_period: Optional[str] = None  # ISO 8601 duration
    requires_masking: bool = False
    compliance_frameworks: List[str] = []

class CapsuleContractCreate(BaseModel):
    capsule_id: UUID
    contract_version: str = "1.0"
    freshness_sla: Optional[str] = None  # ISO 8601 duration
    completeness_sla: Optional[float] = Field(None, ge=0, le=100)
    availability_sla: Optional[float] = Field(None, ge=0, le=100)
    quality_score_sla: Optional[float] = Field(None, ge=0, le=100)
    schema_change_policy: str = "backwards_compatible"
    support_level: str = "best_effort"
```

---

**End of Design Document**

