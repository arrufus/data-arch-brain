# Snowflake Integration - Design Document

**Version**: 1.0
**Status**: Draft
**Last Updated**: December 2024
**Priority**: P1 (Post-MVP)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Integration Goals](#2-integration-goals)
3. [Snowflake Metadata Sources](#3-snowflake-metadata-sources)
4. [Architecture](#4-architecture)
5. [Data Mapping](#5-data-mapping)
6. [Implementation Design](#6-implementation-design)
7. [Authentication & Security](#7-authentication--security)
8. [Performance Considerations](#8-performance-considerations)
9. [Testing Strategy](#9-testing-strategy)
10. [Rollout Plan](#10-rollout-plan)

---

## 1. Executive Summary

### 1.1 Purpose

This document defines the design for integrating Snowflake as a metadata source for the Data Capsule Server (DCS). Snowflake integration will enable DCS to ingest metadata directly from Snowflake's `INFORMATION_SCHEMA` and `ACCOUNT_USAGE` views, providing visibility into:

- Tables, views, and materialized views
- Column-level metadata with data types and constraints
- Query-based lineage from `ACCESS_HISTORY`
- Usage statistics and performance metrics
- Security classifications and tags

### 1.2 Value Proposition

| Capability | Value |
|------------|-------|
| **Live Metadata** | Real-time visibility into Snowflake warehouse state |
| **Native Lineage** | Query-based lineage from Snowflake's ACCESS_HISTORY |
| **Cost Intelligence** | Track compute and storage costs by object |
| **Security Posture** | Understand data access patterns and security classifications |
| **Cross-Platform** | Bridge dbt transformations with underlying Snowflake objects |

### 1.3 Scope

**In Scope:**
- Read-only metadata extraction from Snowflake
- Tables, views, materialized views, external tables
- Column-level metadata and statistics
- Query-based lineage (table-to-table)
- Snowflake tags and classifications
- Basic usage statistics

**Out of Scope (Future Phases):**
- Stream and Task metadata
- Snowpipe and Stage definitions
- Dynamic tables
- Column-level lineage (requires SQL parsing)
- User/role permission analysis
- Cost optimization recommendations

---

## 2. Integration Goals

### 2.1 Primary Goals

1. **Unified Visibility**: Single graph combining dbt models and underlying Snowflake tables
2. **Lineage Completeness**: Capture lineage from native Snowflake queries (non-dbt)
3. **PII Discovery**: Leverage Snowflake's native tag propagation for PII tracking
4. **Conformance**: Apply architecture rules to Snowflake objects
5. **Incremental Sync**: Efficient updates without full re-ingestion

### 2.2 Success Metrics

| Metric | Target |
|--------|--------|
| Metadata completeness | >95% of accessible objects ingested |
| Ingestion time | <5 minutes for 10,000 objects |
| Lineage accuracy | >90% of direct dependencies captured |
| Incremental sync overhead | <30 seconds for detecting changes |
| Error rate | <1% of objects fail to parse |

---

## 3. Snowflake Metadata Sources

### 3.1 INFORMATION_SCHEMA

Primary source for structural metadata (fast, filtered by database/schema).

**Key Views:**

| View | Purpose | Key Columns |
|------|---------|-------------|
| `TABLES` | All tables and views | TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE |
| `COLUMNS` | Column definitions | COLUMN_NAME, DATA_TYPE, IS_NULLABLE, ORDINAL_POSITION |
| `TABLE_CONSTRAINTS` | Primary/foreign keys | CONSTRAINT_TYPE, CONSTRAINT_NAME |
| `VIEWS` | View definitions | VIEW_DEFINITION (SQL text) |

**Advantages:**
- Fast queries (scoped to database)
- Current state (no latency)
- Standard SQL interface

**Limitations:**
- No historical data
- No usage statistics
- No lineage information

### 3.2 ACCOUNT_USAGE Schema

Comprehensive account-level metadata with historical data and lineage.

**Key Views:**

| View | Purpose | Data Retention |
|------|---------|----------------|
| `TABLES` | Table metadata with stats | 1 year |
| `COLUMNS` | Column metadata | 1 year |
| `ACCESS_HISTORY` | Query-based lineage | 1 year |
| `TABLE_STORAGE_METRICS` | Storage costs | 1 year |
| `QUERY_HISTORY` | Query performance | 1 year |
| `TAG_REFERENCES` | Object tags | 1 year |
| `OBJECT_DEPENDENCIES` | View dependencies | 1 year |

**Advantages:**
- Query-based lineage via `ACCESS_HISTORY`
- Usage statistics
- Cost metrics
- Historical trends

**Limitations:**
- 45-minute to 3-hour latency
- Requires ACCOUNTADMIN or custom role
- Cross-database queries

### 3.3 Snowflake Tags

Native classification system for sensitive data.

```sql
-- Query tags applied to columns
SELECT
    TAG_DATABASE,
    TAG_SCHEMA,
    TAG_NAME,
    TAG_VALUE,
    OBJECT_DATABASE,
    OBJECT_SCHEMA,
    OBJECT_NAME,
    COLUMN_NAME
FROM SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES
WHERE OBJECT_DELETED IS NULL
  AND DOMAIN = 'COLUMN';
```

**Use Cases:**
- Map Snowflake tags → DCS semantic types
- PII propagation tracking
- Compliance reporting

---

## 4. Architecture

### 4.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SNOWFLAKE                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────┐        ┌─────────────────────┐            │
│  │ INFORMATION_SCHEMA  │        │  ACCOUNT_USAGE      │            │
│  │                     │        │                     │            │
│  │  • TABLES           │        │  • ACCESS_HISTORY   │            │
│  │  • COLUMNS          │        │  • TAG_REFERENCES   │            │
│  │  • VIEWS            │        │  • QUERY_HISTORY    │            │
│  │  • CONSTRAINTS      │        │  • STORAGE_METRICS  │            │
│  └──────────┬──────────┘        └──────────┬──────────┘            │
│             │                              │                        │
└─────────────┼──────────────────────────────┼────────────────────────┘
              │                              │
              │  SQL Queries                 │  SQL Queries
              │  (Snowflake Connector)       │
              ▼                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DATA CAPSULE SERVER                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │              SnowflakeParser (MetadataParser)                  │ │
│  │                                                                 │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐   │ │
│  │  │StructureExtractor│ │ LineageExtractor │ │TagExtractor │   │ │
│  │  │                  │  │                  │  │             │   │ │
│  │  │ • Query TABLES   │  │ • ACCESS_HISTORY │  │ • Tags →    │   │ │
│  │  │ • Query COLUMNS  │  │ • Object deps    │  │   Semantic  │   │ │
│  │  │ • Query VIEWS    │  │ • Build edges    │  │   types     │   │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘   │ │
│  │           │                    │                    │          │ │
│  │           └────────────────────┼────────────────────┘          │ │
│  │                                ▼                                │ │
│  │                        ParseResult                              │ │
│  │             (RawCapsule, RawColumn, RawEdge)                   │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                ▼                                    │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                      Transformer                               │ │
│  │  • URN generation (urn:dcs:snowflake:table:...)               │ │
│  │  • Layer inference (based on schema naming)                    │ │
│  │  • Domain extraction (from database/schema)                    │ │
│  │  • Merge with dbt metadata (if exists)                        │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                ▼                                    │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                      Graph Loader                              │ │
│  │  • Upsert Snowflake capsules                                  │ │
│  │  • Create/update lineage edges                                │ │
│  │  • Store Snowflake-specific metadata (storage, usage)         │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Parser Architecture

```python
# High-level structure
class SnowflakeParser(MetadataParser):
    @property
    def source_type(self) -> str:
        return "snowflake"

    async def parse(self, config: dict[str, Any]) -> ParseResult:
        # 1. Establish connection
        # 2. Extract structure (tables, columns)
        # 3. Extract lineage (ACCESS_HISTORY)
        # 4. Extract tags
        # 5. Enrich with statistics
        # 6. Return ParseResult
```

### 4.3 Integration with dbt Metadata

When both dbt and Snowflake metadata exist for the same object:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    METADATA RECONCILIATION                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  dbt Capsule:                         Snowflake Capsule:            │
│  urn:dcs:dbt:model:prod.marts:...     urn:dcs:snowflake:table:...   │
│                                                                      │
│         ┌─────────────────────────────────────┐                     │
│         │    Merge Strategy                    │                     │
│         │                                      │                     │
│         │  • URNs remain separate              │                     │
│         │  • Create MATERIALIZES edge          │                     │
│         │  • dbt: Logical (design-time)        │                     │
│         │  • Snowflake: Physical (runtime)     │                     │
│         │  • Prefer dbt for: description,      │                     │
│         │    tests, ownership                  │                     │
│         │  • Prefer Snowflake for: storage,    │                     │
│         │    usage, actual column types        │                     │
│         └─────────────────────────────────────┘                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. Data Mapping

### 5.1 Snowflake → Data Capsule Mapping

| Snowflake Object | Capsule Type | Layer Inference | URN Format |
|------------------|--------------|-----------------|------------|
| TABLE | `table` | From schema name | `urn:dcs:snowflake:table:{db}.{schema}:{name}` |
| VIEW | `view` | From schema name | `urn:dcs:snowflake:view:{db}.{schema}:{name}` |
| MATERIALIZED VIEW | `materialized_view` | From schema name | `urn:dcs:snowflake:materialized_view:{db}.{schema}:{name}` |
| EXTERNAL TABLE | `external_table` | `bronze` (default) | `urn:dcs:snowflake:external_table:{db}.{schema}:{name}` |

### 5.2 Layer Inference Rules

Since Snowflake doesn't have explicit layers, infer from schema naming conventions:

```python
LAYER_PATTERNS = {
    "bronze": [
        r"^(raw|landing|source|bronze|stage|l1)(_.*)?$",
        r".*_raw$"
    ],
    "silver": [
        r"^(staging|stg|silver|intermediate|int|l2)(_.*)?$",
        r".*_staging$"
    ],
    "gold": [
        r"^(mart|marts|gold|analytics|prod|l3|presentation)(_.*)?$",
        r".*_(mart|marts)$"
    ]
}
```

### 5.3 Snowflake Tags → Semantic Types

| Snowflake Tag | DCS Semantic Type | DCS PII Type |
|---------------|-------------------|--------------|
| `PII` | `pii` | (infer from name) |
| `PII:EMAIL` | `pii` | `email` |
| `PII:PHONE` | `pii` | `phone` |
| `PII:SSN` | `pii` | `ssn` |
| `SENSITIVE` | `pii` | `confidential` |
| `PRIMARY_KEY` | `business_key` | - |
| `FOREIGN_KEY` | `foreign_key` | - |

### 5.4 Column Data Type Mapping

| Snowflake Type | Normalized Type | Notes |
|----------------|-----------------|-------|
| `NUMBER(38,0)` | `INTEGER` | Snowflake's integer representation |
| `NUMBER(P,S)` | `DECIMAL(P,S)` | |
| `FLOAT`, `DOUBLE` | `FLOAT` | |
| `VARCHAR(N)` | `STRING` | |
| `TIMESTAMP_NTZ` | `TIMESTAMP` | No timezone |
| `TIMESTAMP_LTZ` | `TIMESTAMP_TZ` | With timezone |
| `VARIANT` | `JSON` | Semi-structured |
| `ARRAY` | `ARRAY` | Semi-structured |
| `OBJECT` | `STRUCT` | Semi-structured |

---

## 6. Implementation Design

### 6.1 Configuration Schema

```python
@dataclass
class SnowflakeParserConfig:
    """Configuration for Snowflake metadata parser."""

    # Connection
    account: str                          # e.g., "myorg-account123"
    user: str
    password: Optional[str] = None        # Prefer key-pair auth
    private_key_path: Optional[Path] = None
    role: str = "SYSADMIN"                # Role for querying
    warehouse: str = "COMPUTE_WH"         # Warehouse for queries

    # Scope
    databases: list[str] = field(default_factory=list)  # Empty = all accessible
    schemas: list[str] = field(default_factory=list)    # Patterns: "PROD.*"
    include_views: bool = True
    include_external_tables: bool = True

    # Lineage
    enable_lineage: bool = True
    lineage_lookback_days: int = 7        # How far to query ACCESS_HISTORY
    use_account_usage: bool = True        # Use ACCOUNT_USAGE (vs INFORMATION_SCHEMA only)

    # Tags
    enable_tag_extraction: bool = True
    tag_mappings: dict[str, dict[str, str]] = field(default_factory=dict)
    # Example: {"PII": {"semantic_type": "pii", "category": "sensitivity"}}

    # Layer inference
    layer_patterns: dict[str, list[str]] = field(default_factory=lambda: {
        "bronze": [r"^(raw|landing|bronze).*"],
        "silver": [r"^(staging|stg|silver).*"],
        "gold": [r"^(mart|gold|analytics).*"]
    })

    # Performance
    batch_size: int = 1000                # Rows per query batch
    max_workers: int = 4                  # Concurrent query workers
    query_timeout_seconds: int = 300

    # Incremental sync
    last_sync_timestamp: Optional[str] = None

    def validate(self) -> list[str]:
        """Validate configuration."""
        errors = []
        if not self.account:
            errors.append("account is required")
        if not self.user:
            errors.append("user is required")
        if not self.password and not self.private_key_path:
            errors.append("Either password or private_key_path must be provided")
        return errors
```

### 6.2 Core Extraction Queries

#### 6.2.1 Extract Tables and Views

```sql
-- Query INFORMATION_SCHEMA.TABLES (fast, scoped to database)
SELECT
    TABLE_CATALOG AS database_name,
    TABLE_SCHEMA AS schema_name,
    TABLE_NAME AS table_name,
    TABLE_TYPE,                          -- 'BASE TABLE', 'VIEW', 'MATERIALIZED VIEW'
    ROW_COUNT,
    BYTES,
    CREATED,
    LAST_ALTERED,
    COMMENT AS description
FROM {database}.INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA', 'ACCOUNT_USAGE')
  AND (TABLE_TYPE = 'BASE TABLE' OR TABLE_TYPE = 'VIEW' OR TABLE_TYPE = 'MATERIALIZED VIEW')
ORDER BY TABLE_SCHEMA, TABLE_NAME;
```

#### 6.2.2 Extract Columns

```sql
SELECT
    TABLE_CATALOG AS database_name,
    TABLE_SCHEMA AS schema_name,
    TABLE_NAME AS table_name,
    COLUMN_NAME,
    ORDINAL_POSITION,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    CHARACTER_MAXIMUM_LENGTH,
    NUMERIC_PRECISION,
    NUMERIC_SCALE,
    COMMENT AS description
FROM {database}.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA', 'ACCOUNT_USAGE')
ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION;
```

#### 6.2.3 Extract Lineage from ACCESS_HISTORY

```sql
-- Query ACCOUNT_USAGE.ACCESS_HISTORY for query-based lineage
WITH lineage_raw AS (
    SELECT DISTINCT
        ah.query_id,
        ah.query_start_time,
        base.value:objectName::STRING AS base_object_name,
        base.value:objectDomain::STRING AS base_object_domain,
        col.value:objectName::STRING AS referenced_object_name,
        col.value:objectDomain::STRING AS referenced_object_domain
    FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY ah,
        LATERAL FLATTEN(input => ah.base_objects_accessed) base,
        LATERAL FLATTEN(input => ah.objects_modified, OUTER => TRUE) col
    WHERE ah.query_start_time >= DATEADD(day, -:lookback_days, CURRENT_TIMESTAMP())
      AND base.value:objectDomain IN ('Table', 'View', 'Materialized view')
      AND (col.value:objectDomain IN ('Table', 'View', 'Materialized view')
           OR col.value IS NULL)
)
SELECT
    referenced_object_name AS source_object,
    base_object_name AS target_object,
    COUNT(DISTINCT query_id) AS query_count,
    MAX(query_start_time) AS last_query_time
FROM lineage_raw
WHERE referenced_object_name IS NOT NULL
GROUP BY source_object, target_object;
```

#### 6.2.4 Extract Tags

```sql
SELECT
    TAG_DATABASE,
    TAG_SCHEMA,
    TAG_NAME,
    TAG_VALUE,
    OBJECT_DATABASE,
    OBJECT_SCHEMA,
    OBJECT_NAME,
    COLUMN_NAME,
    DOMAIN                               -- 'TABLE', 'COLUMN', 'VIEW', etc.
FROM SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES
WHERE OBJECT_DELETED IS NULL
  AND TAG_DROPPED IS NULL
ORDER BY OBJECT_DATABASE, OBJECT_SCHEMA, OBJECT_NAME, COLUMN_NAME;
```

### 6.3 Parser Implementation Outline

```python
class SnowflakeParser(MetadataParser):
    """Parser for Snowflake INFORMATION_SCHEMA and ACCOUNT_USAGE."""

    def __init__(self):
        self.connector: Optional[snowflake.connector.SnowflakeConnection] = None

    @property
    def source_type(self) -> str:
        return "snowflake"

    async def parse(self, config: dict[str, Any]) -> ParseResult:
        """Main entry point for parsing Snowflake metadata."""
        result = ParseResult(source_type=self.source_type)

        # 1. Parse and validate config
        parser_config = SnowflakeParserConfig.from_dict(config)
        errors = parser_config.validate()
        if errors:
            for error in errors:
                result.add_error(error, severity=ParseErrorSeverity.ERROR)
            return result

        # 2. Establish connection
        try:
            await self._connect(parser_config)
        except Exception as e:
            result.add_error(
                f"Failed to connect to Snowflake: {e}",
                severity=ParseErrorSeverity.ERROR
            )
            return result

        try:
            # 3. Determine scope (databases to scan)
            databases = await self._get_databases(parser_config)
            result.source_name = ", ".join(databases)

            # 4. Extract structure for each database
            for database in databases:
                await self._extract_database_metadata(
                    database, parser_config, result
                )

            # 5. Extract lineage (if enabled)
            if parser_config.enable_lineage and parser_config.use_account_usage:
                await self._extract_lineage(parser_config, result)

            # 6. Extract tags (if enabled)
            if parser_config.enable_tag_extraction and parser_config.use_account_usage:
                await self._extract_tags(parser_config, result)

            # 7. Enrich with statistics
            await self._enrich_statistics(parser_config, result)

        finally:
            await self._disconnect()

        return result

    async def _connect(self, config: SnowflakeParserConfig):
        """Establish Snowflake connection."""
        connection_params = {
            "account": config.account,
            "user": config.user,
            "warehouse": config.warehouse,
            "role": config.role,
        }

        if config.private_key_path:
            # Key-pair authentication (preferred for production)
            private_key = self._load_private_key(config.private_key_path)
            connection_params["private_key"] = private_key
        else:
            connection_params["password"] = config.password

        self.connector = snowflake.connector.connect(**connection_params)

    async def _extract_database_metadata(
        self,
        database: str,
        config: SnowflakeParserConfig,
        result: ParseResult
    ):
        """Extract tables, columns, and constraints for a database."""

        # Extract tables
        tables = await self._query_tables(database, config)
        for table_row in tables:
            capsule = self._build_capsule(table_row, config)
            result.capsules.append(capsule)

            # Extract columns for this table
            columns = await self._query_columns(
                database,
                table_row["schema_name"],
                table_row["table_name"]
            )
            for col_row in columns:
                column = self._build_column(col_row, capsule.urn, config)
                result.columns.append(column)

    async def _extract_lineage(
        self,
        config: SnowflakeParserConfig,
        result: ParseResult
    ):
        """Extract lineage from ACCESS_HISTORY."""
        lineage_rows = await self._query_lineage(config)
        for row in lineage_rows:
            edge = RawEdge(
                source_urn=self._build_urn_from_fqn(row["source_object"]),
                target_urn=self._build_urn_from_fqn(row["target_object"]),
                edge_type="flows_to",
                transformation="query",
                meta={
                    "query_count": row["query_count"],
                    "last_query_time": row["last_query_time"]
                }
            )
            result.edges.append(edge)

    async def _extract_tags(
        self,
        config: SnowflakeParserConfig,
        result: ParseResult
    ):
        """Extract Snowflake tags and map to semantic types."""
        tag_rows = await self._query_tags(config)

        for row in tag_rows:
            if row["domain"] == "COLUMN":
                # Map tag to semantic type
                column_urn = self._build_column_urn(
                    row["object_database"],
                    row["object_schema"],
                    row["object_name"],
                    row["column_name"]
                )

                # Apply tag mapping
                semantic_info = self._map_tag_to_semantic_type(
                    row["tag_name"],
                    row["tag_value"],
                    config
                )

                # Update column in result
                self._apply_semantic_type_to_column(
                    result,
                    column_urn,
                    semantic_info
                )

    def _build_capsule(
        self,
        row: dict[str, Any],
        config: SnowflakeParserConfig
    ) -> RawCapsule:
        """Build RawCapsule from Snowflake table row."""
        fqn = f"{row['database_name']}.{row['schema_name']}.{row['table_name']}"
        urn = self._build_urn(
            row['table_type'],
            row['database_name'],
            row['schema_name'],
            row['table_name']
        )

        # Infer layer from schema name
        layer = self._infer_layer(row['schema_name'], config)

        return RawCapsule(
            urn=urn,
            name=row['table_name'],
            capsule_type=self._normalize_table_type(row['table_type']),
            unique_id=fqn,
            database_name=row['database_name'],
            schema_name=row['schema_name'],
            layer=layer,
            description=row.get('description'),
            materialization=row['table_type'].lower(),
            meta={
                "row_count": row.get('row_count'),
                "bytes": row.get('bytes'),
                "created": row.get('created'),
                "last_altered": row.get('last_altered')
            }
        )

    def _build_urn(
        self,
        object_type: str,
        database: str,
        schema: str,
        name: str
    ) -> str:
        """Build URN for Snowflake object."""
        normalized_type = self._normalize_table_type(object_type)
        namespace = f"{database}.{schema}"
        return f"urn:dcs:snowflake:{normalized_type}:{namespace}:{name}"

    def _infer_layer(
        self,
        schema_name: str,
        config: SnowflakeParserConfig
    ) -> Optional[str]:
        """Infer architecture layer from schema name."""
        import re
        for layer, patterns in config.layer_patterns.items():
            for pattern in patterns:
                if re.match(pattern, schema_name, re.IGNORECASE):
                    return layer
        return None

    def _map_tag_to_semantic_type(
        self,
        tag_name: str,
        tag_value: str,
        config: SnowflakeParserConfig
    ) -> dict[str, Any]:
        """Map Snowflake tag to DCS semantic type."""
        # Check custom mappings first
        if tag_name in config.tag_mappings:
            return config.tag_mappings[tag_name]

        # Default mappings
        tag_upper = tag_name.upper()
        if tag_upper == "PII" or tag_upper.startswith("PII:"):
            return {
                "semantic_type": "pii",
                "pii_type": self._extract_pii_type(tag_name, tag_value),
                "pii_detected_by": "tag"
            }
        elif tag_upper == "PRIMARY_KEY":
            return {"semantic_type": "business_key"}
        elif tag_upper == "FOREIGN_KEY":
            return {"semantic_type": "foreign_key"}

        return {}
```

---

## 7. Authentication & Security

### 7.1 Authentication Methods

**Option 1: Username/Password (Development)**
```python
connection_params = {
    "account": "myorg-account123",
    "user": "dcs_service_user",
    "password": os.environ["SNOWFLAKE_PASSWORD"],
    "warehouse": "METADATA_WH",
    "role": "METADATA_READER"
}
```

**Option 2: Key-Pair Authentication (Production)**
```python
# Generate key pair
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt
openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub

# Register public key in Snowflake
ALTER USER dcs_service_user SET RSA_PUBLIC_KEY='MIIBIjANBg...';

# Use in connection
with open("rsa_key.p8", "rb") as key_file:
    private_key = serialization.load_pem_private_key(
        key_file.read(),
        password=None,
        backend=default_backend()
    )

connection_params = {
    "account": "myorg-account123",
    "user": "dcs_service_user",
    "private_key": private_key,
    "warehouse": "METADATA_WH",
    "role": "METADATA_READER"
}
```

### 7.2 Required Snowflake Permissions

Create a custom role with minimal required permissions:

```sql
-- Create service user
CREATE USER dcs_service_user
  PASSWORD = '...'
  DEFAULT_ROLE = METADATA_READER
  DEFAULT_WAREHOUSE = METADATA_WH;

-- Create role with minimal permissions
CREATE ROLE METADATA_READER;

-- Grant USAGE on warehouse
GRANT USAGE ON WAREHOUSE METADATA_WH TO ROLE METADATA_READER;

-- Grant USAGE on databases to scan
GRANT USAGE ON DATABASE PROD TO ROLE METADATA_READER;
GRANT USAGE ON ALL SCHEMAS IN DATABASE PROD TO ROLE METADATA_READER;

-- Grant SELECT on INFORMATION_SCHEMA (implicit with USAGE)

-- Grant SELECT on ACCOUNT_USAGE (requires ACCOUNTADMIN delegation)
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE METADATA_READER;

-- Assign role to user
GRANT ROLE METADATA_READER TO USER dcs_service_user;
```

### 7.3 Security Best Practices

| Practice | Implementation |
|----------|----------------|
| Least privilege | Custom role with only required grants |
| Credential management | Store in environment variables or secret manager |
| Key-pair auth | Use for production (more secure than password) |
| Network policies | Restrict connection to DCS IP addresses |
| Query auditing | Monitor queries from service user |
| Secret rotation | Rotate keys/passwords every 90 days |

---

## 8. Performance Considerations

### 8.1 Query Optimization

| Strategy | Implementation |
|----------|----------------|
| Batch queries | Query INFORMATION_SCHEMA per database (not per table) |
| Parallel execution | Use asyncio to query multiple databases concurrently |
| Result caching | Cache table list, query incrementally by last_altered |
| Warehouse sizing | Use small warehouse for metadata queries (X-Small sufficient) |
| Query timeout | Set reasonable timeout (5 minutes) to avoid runaway queries |

### 8.2 Incremental Sync

Track `last_sync_timestamp` and filter by `LAST_ALTERED`:

```sql
SELECT * FROM {database}.INFORMATION_SCHEMA.TABLES
WHERE LAST_ALTERED > :last_sync_timestamp
ORDER BY LAST_ALTERED;
```

**Benefits:**
- Reduce query time from minutes to seconds
- Minimize warehouse costs
- Enable frequent syncs (hourly)

### 8.3 Estimated Performance

| Scenario | Objects | Query Time | Ingestion Time |
|----------|---------|------------|----------------|
| Small | 100 tables | <10s | <30s |
| Medium | 1,000 tables | <30s | <2m |
| Large | 10,000 tables | <3m | <10m |
| Incremental (100 changed) | 100 tables | <5s | <30s |

*Assumes X-Small warehouse, good network latency*

---

## 9. Testing Strategy

### 9.1 Unit Tests

```python
# tests/unit/parsers/test_snowflake_parser.py

@pytest.mark.asyncio
async def test_parse_tables():
    """Test table extraction from mock INFORMATION_SCHEMA."""
    parser = SnowflakeParser()
    # Mock Snowflake connector
    with mock_snowflake_connection():
        result = await parser.parse({
            "account": "test",
            "user": "test",
            "password": "test",
            "databases": ["TEST_DB"]
        })

    assert len(result.capsules) == 5
    assert result.capsules[0].capsule_type == "table"

@pytest.mark.asyncio
async def test_lineage_extraction():
    """Test lineage extraction from ACCESS_HISTORY."""
    # Test implementation
    pass

def test_layer_inference():
    """Test layer inference from schema names."""
    config = SnowflakeParserConfig(
        account="test",
        user="test",
        password="test"
    )
    parser = SnowflakeParser()

    assert parser._infer_layer("raw_data", config) == "bronze"
    assert parser._infer_layer("staging_customers", config) == "silver"
    assert parser._infer_layer("analytics_mart", config) == "gold"
    assert parser._infer_layer("other_schema", config) is None
```

### 9.2 Integration Tests

```python
# tests/integration/test_snowflake_integration.py

@pytest.mark.integration
@pytest.mark.skipif(not has_snowflake_credentials(), reason="No Snowflake creds")
async def test_real_snowflake_connection():
    """Test against real Snowflake account (CI/CD)."""
    parser = SnowflakeParser()
    config = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "password": os.environ["SNOWFLAKE_PASSWORD"],
        "databases": ["TEST_DB"],
        "enable_lineage": False  # Skip for speed
    }

    result = await parser.parse(config)

    assert not result.has_errors
    assert len(result.capsules) > 0
    assert len(result.columns) > 0
```

### 9.3 Test Data Setup

Create test Snowflake database with sample data:

```sql
-- Setup script for integration tests
CREATE DATABASE IF NOT EXISTS TEST_DCS_INTEGRATION;

USE DATABASE TEST_DCS_INTEGRATION;

CREATE SCHEMA IF NOT EXISTS raw_data;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Create sample tables
CREATE TABLE raw_data.customers (
    id INTEGER,
    email VARCHAR,
    phone VARCHAR,
    created_at TIMESTAMP
);

CREATE TABLE staging.stg_customers (
    customer_id INTEGER,
    email_hash VARCHAR,
    created_at TIMESTAMP
);

CREATE VIEW analytics.customer_summary AS
SELECT customer_id, COUNT(*) AS order_count
FROM staging.stg_customers
GROUP BY customer_id;

-- Apply tags
CREATE TAG IF NOT EXISTS PII_EMAIL;
ALTER TABLE raw_data.customers MODIFY COLUMN email SET TAG PII_EMAIL = 'true';
```

---

## 10. Rollout Plan

### 10.1 Phase 1: MVP (Weeks 1-3)

**Deliverables:**
- SnowflakeParser with INFORMATION_SCHEMA extraction
- Basic table and column metadata
- Configuration and validation
- Unit tests

**Acceptance Criteria:**
- [ ] Can connect to Snowflake with key-pair auth
- [ ] Extract tables, views, columns from INFORMATION_SCHEMA
- [ ] Generate correct URNs
- [ ] Infer layers from schema names
- [ ] Pass unit tests

### 10.2 Phase 2: Lineage (Week 4)

**Deliverables:**
- ACCESS_HISTORY lineage extraction
- Query-based lineage edges
- Lineage integration tests

**Acceptance Criteria:**
- [ ] Extract lineage from last 7 days of ACCESS_HISTORY
- [ ] Create FLOWS_TO edges
- [ ] Handle missing objects gracefully
- [ ] Performance < 2 minutes for 10K objects

### 10.3 Phase 3: Tags & Enrichment (Week 5)

**Deliverables:**
- Tag extraction from TAG_REFERENCES
- Tag → semantic type mapping
- Statistics enrichment

**Acceptance Criteria:**
- [ ] Extract and apply Snowflake tags
- [ ] Map tags to PII types
- [ ] Include storage and usage metrics
- [ ] Configurable tag mappings

### 10.4 Phase 4: Incremental Sync (Week 6)

**Deliverables:**
- Incremental sync by LAST_ALTERED
- Change detection
- Merge strategy with existing data

**Acceptance Criteria:**
- [ ] Track last sync timestamp
- [ ] Only query changed objects
- [ ] Incremental sync < 30 seconds
- [ ] No data loss on re-sync

### 10.5 Phase 5: Production Hardening (Week 7-8)

**Deliverables:**
- Error handling and retry logic
- Connection pooling
- Comprehensive logging
- Documentation

**Acceptance Criteria:**
- [ ] Graceful handling of connection failures
- [ ] Retry on transient errors
- [ ] Structured logging for debugging
- [ ] User documentation complete

---

## Appendices

### Appendix A: Sample Configuration

```yaml
# snowflake_config.yaml
source_type: snowflake
account: myorg-account123
user: dcs_service_user
private_key_path: /path/to/rsa_key.p8
role: METADATA_READER
warehouse: METADATA_WH

# Scope
databases:
  - PROD
  - ANALYTICS
schemas:
  - "PROD.RAW_*"
  - "PROD.STAGING_*"
  - "ANALYTICS.*"

# Features
enable_lineage: true
lineage_lookback_days: 7
enable_tag_extraction: true

# Tag mappings
tag_mappings:
  PII:
    semantic_type: pii
    category: sensitivity
  PII:EMAIL:
    semantic_type: pii
    pii_type: email
  SENSITIVE:
    semantic_type: pii
    pii_type: confidential

# Layer inference
layer_patterns:
  bronze:
    - "^raw_.*"
    - "^landing_.*"
  silver:
    - "^staging_.*"
    - "^stg_.*"
  gold:
    - "^analytics_.*"
    - "^marts_.*"
```

### Appendix B: Snowflake Connector Setup

```bash
# Install Snowflake connector
pip install snowflake-connector-python[pandas]

# For key-pair authentication
pip install cryptography
```

### Appendix C: URN Examples

```
# Table
urn:dcs:snowflake:table:prod.raw_data:customers

# View
urn:dcs:snowflake:view:prod.analytics:customer_summary

# Materialized View
urn:dcs:snowflake:materialized_view:prod.marts:daily_sales

# External Table
urn:dcs:snowflake:external_table:prod.landing:s3_events

# Column
urn:dcs:snowflake:column:prod.raw_data:customers.email
```

---

*End of Snowflake Integration Design Document*
