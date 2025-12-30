# Snowflake Integration - Implementation Plan

**Version**: 1.0
**Status**: Draft
**Last Updated**: December 2024
**Estimated Duration**: 8 weeks
**Prerequisites**: Phase 1 (dbt integration) complete

---

## Table of Contents

1. [Implementation Overview](#1-implementation-overview)
2. [Sprint Breakdown](#2-sprint-breakdown)
3. [File Structure](#3-file-structure)
4. [Dependencies](#4-dependencies)
5. [Implementation Steps](#5-implementation-steps)
6. [Testing Plan](#6-testing-plan)
7. [Deployment Strategy](#7-deployment-strategy)
8. [Success Criteria](#8-success-criteria)

---

## 1. Implementation Overview

### 1.1 Goals

Implement Snowflake as a metadata source for Data Capsule Server, enabling ingestion of:
- Table and view metadata from INFORMATION_SCHEMA
- Column-level metadata with data types
- Query-based lineage from ACCESS_HISTORY
- Snowflake tags and classifications
- Usage and storage statistics

### 1.2 Approach

**Incremental Development:**
1. Sprint 1-2: Core parser (INFORMATION_SCHEMA)
2. Sprint 3: Lineage extraction (ACCOUNT_USAGE)
3. Sprint 4: Tags and enrichment
4. Sprint 5: Incremental sync
5. Sprint 6-7: Production hardening
6. Sprint 8: Documentation and rollout

**Quality Gates:**
- Unit tests for all components
- Integration tests against real Snowflake
- Performance benchmarks
- Security review
- Documentation review

---

## 2. Sprint Breakdown

### Sprint 1: Foundation & Basic Extraction (Week 1-2)

**Goal:** Establish Snowflake connection and extract basic table/column metadata.

**User Stories:**
1. As a developer, I can configure Snowflake connection with key-pair auth
2. As a data architect, I can ingest tables and views from Snowflake INFORMATION_SCHEMA
3. As a data architect, I can see Snowflake objects as capsules in the graph

**Tasks:**
- [ ] Create `SnowflakeParserConfig` dataclass with validation
- [ ] Implement `SnowflakeParser` base structure
- [ ] Add Snowflake connector dependency
- [ ] Implement connection management (connect/disconnect)
- [ ] Implement key-pair authentication
- [ ] Query INFORMATION_SCHEMA.TABLES
- [ ] Query INFORMATION_SCHEMA.COLUMNS
- [ ] Build RawCapsule from table rows
- [ ] Build RawColumn from column rows
- [ ] Generate Snowflake URNs
- [ ] Implement layer inference from schema names
- [ ] Register parser in ParserRegistry
- [ ] Write unit tests for parser
- [ ] Write unit tests for URN generation
- [ ] Write unit tests for layer inference

**Deliverables:**
- `backend/src/parsers/snowflake_config.py`
- `backend/src/parsers/snowflake_parser.py`
- `backend/tests/unit/parsers/test_snowflake_parser.py`
- Updated `requirements.txt` with snowflake-connector-python

**Acceptance Criteria:**
- ✓ Parser can connect to Snowflake with key-pair auth
- ✓ Parser extracts tables, views, and columns
- ✓ URNs follow format: `urn:dcs:snowflake:table:{db}.{schema}:{name}`
- ✓ Layer inference works for common schema patterns
- ✓ Unit test coverage > 80%
- ✓ No errors on sample Snowflake database

---

### Sprint 2: API Integration & CLI (Week 3)

**Goal:** Expose Snowflake ingestion via API and CLI.

**User Stories:**
1. As an API user, I can trigger Snowflake ingestion via POST /api/v1/ingest/snowflake
2. As a CLI user, I can run `dcs ingest snowflake --config snowflake.yaml`
3. As a user, I can see ingestion progress and errors

**Tasks:**
- [ ] Add Snowflake ingestion endpoint to IngestRouter
- [ ] Implement request validation (Pydantic schema)
- [ ] Add CLI command for Snowflake ingestion
- [ ] Support config file (YAML/JSON)
- [ ] Support environment variables for credentials
- [ ] Add progress logging
- [ ] Store ingestion job metadata
- [ ] Return structured ingestion result
- [ ] Write API integration tests
- [ ] Write CLI integration tests
- [ ] Update API documentation (OpenAPI)

**Deliverables:**
- `backend/src/api/routers/ingest.py` (updated)
- `backend/src/cli/commands/ingest.py` (updated)
- `backend/tests/integration/test_snowflake_ingest_api.py`
- Updated OpenAPI spec

**Acceptance Criteria:**
- ✓ API endpoint accepts Snowflake config and triggers ingestion
- ✓ CLI command works: `dcs ingest snowflake --config config.yaml`
- ✓ Credentials can be provided via env vars: SNOWFLAKE_PASSWORD
- ✓ Ingestion job tracked in `ingestion_jobs` table
- ✓ API returns 201 on success with ingestion_id
- ✓ Error messages are clear and actionable

---

### Sprint 3: Lineage Extraction (Week 4)

**Goal:** Extract query-based lineage from ACCOUNT_USAGE.ACCESS_HISTORY.

**User Stories:**
1. As a data architect, I can see lineage between Snowflake tables based on actual queries
2. As a platform engineer, I can trace data flow through Snowflake transformations
3. As a user, I can configure lineage lookback period

**Tasks:**
- [ ] Implement ACCESS_HISTORY query
- [ ] Parse ACCESS_HISTORY JSON columns (base_objects_accessed, objects_modified)
- [ ] Build RawEdge from lineage data
- [ ] Handle missing or deleted objects
- [ ] De-duplicate lineage edges
- [ ] Add query count and last_query_time metadata
- [ ] Implement configurable lookback period
- [ ] Handle ACCOUNTADMIN permission requirements
- [ ] Write unit tests for lineage parsing
- [ ] Write integration tests with sample queries
- [ ] Performance test with 1M ACCESS_HISTORY rows

**Deliverables:**
- `backend/src/parsers/snowflake_parser.py` (updated with lineage)
- `backend/tests/unit/parsers/test_snowflake_lineage.py`
- `backend/tests/integration/test_snowflake_lineage_integration.py`

**Acceptance Criteria:**
- ✓ Lineage extracted from ACCESS_HISTORY
- ✓ FLOWS_TO edges created between tables
- ✓ Configurable lookback period (default 7 days)
- ✓ Handles missing objects gracefully
- ✓ Performance < 2 minutes for 10K objects
- ✓ Lineage accuracy > 90% (validated manually)

---

### Sprint 4: Tags & Enrichment (Week 5)

**Goal:** Extract Snowflake tags and enrich with statistics.

**User Stories:**
1. As a compliance officer, I can see PII tags from Snowflake on columns
2. As a data architect, I can map custom Snowflake tags to semantic types
3. As a platform engineer, I can see storage and usage metrics

**Tasks:**
- [ ] Implement TAG_REFERENCES query
- [ ] Map Snowflake tags to semantic types
- [ ] Support custom tag mappings (config)
- [ ] Apply tags to columns in ParseResult
- [ ] Extract storage metrics (BYTES, ROW_COUNT)
- [ ] Extract usage statistics (optional)
- [ ] Implement PII type inference from tag names
- [ ] Write unit tests for tag mapping
- [ ] Write integration tests with tagged objects
- [ ] Document tag mapping configuration

**Deliverables:**
- `backend/src/parsers/snowflake_parser.py` (updated with tags)
- `backend/tests/unit/parsers/test_snowflake_tags.py`
- Updated documentation for tag mappings

**Acceptance Criteria:**
- ✓ Tags extracted from TAG_REFERENCES
- ✓ Default tag mappings work (PII, PII:EMAIL, etc.)
- ✓ Custom tag mappings configurable
- ✓ PII types correctly inferred
- ✓ Storage metrics included in capsule metadata
- ✓ Tag extraction < 30 seconds for 10K objects

---

### Sprint 5: Incremental Sync (Week 6)

**Goal:** Support efficient incremental updates.

**User Stories:**
1. As a user, I can run incremental sync to only update changed objects
2. As a platform engineer, I can schedule hourly syncs without full re-ingestion
3. As a developer, I can track sync state

**Tasks:**
- [ ] Add last_sync_timestamp to config
- [ ] Filter INFORMATION_SCHEMA by LAST_ALTERED
- [ ] Store sync timestamp in ingestion_jobs
- [ ] Implement merge strategy (upsert existing capsules)
- [ ] Handle deleted objects (mark as deleted vs hard delete)
- [ ] Optimize queries for incremental sync
- [ ] Write unit tests for incremental logic
- [ ] Write integration tests comparing full vs incremental
- [ ] Performance benchmark incremental sync
- [ ] Document incremental sync usage

**Deliverables:**
- `backend/src/parsers/snowflake_parser.py` (updated with incremental)
- `backend/src/services/ingestion_service.py` (updated with merge logic)
- `backend/tests/unit/parsers/test_snowflake_incremental.py`

**Acceptance Criteria:**
- ✓ Incremental sync only queries changed objects
- ✓ Sync timestamp persisted across runs
- ✓ Merge strategy updates existing capsules without duplicates
- ✓ Incremental sync < 30 seconds for 100 changed objects
- ✓ No data loss compared to full sync

---

### Sprint 6: Error Handling & Resilience (Week 7)

**Goal:** Production-grade error handling and resilience.

**User Stories:**
1. As a user, I get clear error messages when something fails
2. As a platform engineer, sync continues even if some objects fail
3. As a developer, I can debug issues from structured logs

**Tasks:**
- [ ] Implement connection retry logic (exponential backoff)
- [ ] Handle Snowflake-specific errors (permissions, timeouts, rate limits)
- [ ] Add partial success support (continue on individual object failures)
- [ ] Implement circuit breaker for repeated failures
- [ ] Add structured logging (JSON format)
- [ ] Log query performance metrics
- [ ] Add health check for Snowflake connectivity
- [ ] Write unit tests for error scenarios
- [ ] Write integration tests for failure cases
- [ ] Document error handling behavior

**Deliverables:**
- `backend/src/parsers/snowflake_parser.py` (updated with error handling)
- `backend/src/utils/snowflake_connector.py` (connection pooling, retry)
- `backend/tests/unit/parsers/test_snowflake_errors.py`

**Acceptance Criteria:**
- ✓ Transient errors retry up to 3 times
- ✓ Partial failures don't abort entire ingestion
- ✓ Clear error messages for common issues
- ✓ All errors logged with context (query, object, timestamp)
- ✓ Health check endpoint validates Snowflake connectivity

---

### Sprint 7: Performance Optimization (Week 7)

**Goal:** Optimize for production scale and cost.

**User Stories:**
1. As a platform engineer, I can ingest 10K objects in < 10 minutes
2. As a user, I minimize Snowflake compute costs
3. As a developer, I can monitor ingestion performance

**Tasks:**
- [ ] Implement query batching (batch INFORMATION_SCHEMA queries)
- [ ] Add parallel execution for multiple databases
- [ ] Optimize ACCESS_HISTORY query (reduce scan)
- [ ] Add query result caching (avoid duplicate queries)
- [ ] Configure warehouse auto-suspend
- [ ] Add performance metrics (timing, object counts)
- [ ] Benchmark against large datasets (10K, 50K objects)
- [ ] Optimize database queries (indexes, query plans)
- [ ] Write performance tests
- [ ] Document performance tuning guide

**Deliverables:**
- `backend/src/parsers/snowflake_parser.py` (optimized)
- `backend/tests/performance/test_snowflake_performance.py`
- Performance tuning guide in docs

**Acceptance Criteria:**
- ✓ 10K objects ingest in < 10 minutes
- ✓ Queries use X-Small warehouse (minimize cost)
- ✓ Parallel execution for multiple databases
- ✓ Performance metrics logged
- ✓ No timeout errors on large datasets

---

### Sprint 8: Documentation & Rollout (Week 8)

**Goal:** Complete documentation and prepare for production rollout.

**User Stories:**
1. As a new user, I can follow a quickstart guide to ingest Snowflake metadata
2. As a platform engineer, I understand how to configure production deployments
3. As a developer, I can troubleshoot issues using documentation

**Tasks:**
- [ ] Write user documentation (quickstart, configuration reference)
- [ ] Write developer documentation (architecture, extending parser)
- [ ] Create example configurations (dev, prod)
- [ ] Write troubleshooting guide
- [ ] Create video walkthrough (optional)
- [ ] Update main README with Snowflake support
- [ ] Write migration guide (for existing users)
- [ ] Conduct security review
- [ ] Prepare release notes
- [ ] Create rollout checklist

**Deliverables:**
- `docs/user_guide/snowflake_integration.md`
- `docs/developer_guide/snowflake_parser.md`
- `docs/troubleshooting/snowflake.md`
- `examples/snowflake_config.yaml`
- Release notes

**Acceptance Criteria:**
- ✓ Quickstart guide allows new user to ingest in < 15 minutes
- ✓ Configuration reference covers all options
- ✓ Troubleshooting guide covers common issues
- ✓ Security review complete (no vulnerabilities)
- ✓ Release notes published

---

## 3. File Structure

### 3.1 New Files

```
backend/
├── src/
│   ├── parsers/
│   │   ├── snowflake_parser.py          # Main parser implementation
│   │   ├── snowflake_config.py          # Configuration dataclass
│   │   └── snowflake_queries.py         # SQL query templates
│   ├── utils/
│   │   └── snowflake_connector.py       # Connection pooling, retry logic
│   └── api/
│       └── routers/
│           └── ingest.py                 # Updated with Snowflake endpoint
├── tests/
│   ├── unit/
│   │   └── parsers/
│   │       ├── test_snowflake_parser.py
│   │       ├── test_snowflake_config.py
│   │       ├── test_snowflake_lineage.py
│   │       ├── test_snowflake_tags.py
│   │       ├── test_snowflake_incremental.py
│   │       └── test_snowflake_errors.py
│   ├── integration/
│   │   └── test_snowflake_integration.py
│   └── performance/
│       └── test_snowflake_performance.py
└── examples/
    └── snowflake_config.yaml             # Sample configuration

docs/
├── user_guide/
│   └── snowflake_integration.md
├── developer_guide/
│   └── snowflake_parser.md
├── troubleshooting/
│   └── snowflake.md
└── design_docs/
    ├── snowflake_integration_design.md   # Design document (already created)
    └── snowflake_integration_implementation_plan.md  # This file
```

### 3.2 Modified Files

```
backend/
├── src/
│   ├── parsers/
│   │   └── __init__.py                   # Register SnowflakeParser
│   └── cli/
│       └── commands/
│           └── ingest.py                  # Add snowflake subcommand
├── requirements.txt                       # Add snowflake-connector-python
└── pyproject.toml                         # Update dependencies

docs/
└── USER_GUIDE.md                          # Add Snowflake section
```

---

## 4. Dependencies

### 4.1 Python Libraries

Add to `requirements.txt`:

```txt
# Snowflake connector
snowflake-connector-python[pandas]==3.5.0
cryptography>=41.0.0  # For key-pair authentication
```

### 4.2 Snowflake Prerequisites

**Account Requirements:**
- Snowflake account with ACCOUNTADMIN or custom role with IMPORTED PRIVILEGES on SNOWFLAKE database
- Warehouse for metadata queries (X-Small recommended)
- Network access from DCS server to Snowflake

**Service User Setup:**
```sql
-- Run as ACCOUNTADMIN
CREATE USER dcs_service_user
  PASSWORD = 'CHANGE_ME'
  DEFAULT_ROLE = METADATA_READER
  DEFAULT_WAREHOUSE = METADATA_WH;

CREATE ROLE METADATA_READER;
GRANT USAGE ON WAREHOUSE METADATA_WH TO ROLE METADATA_READER;
GRANT USAGE ON DATABASE PROD TO ROLE METADATA_READER;
GRANT USAGE ON ALL SCHEMAS IN DATABASE PROD TO ROLE METADATA_READER;
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE METADATA_READER;
GRANT ROLE METADATA_READER TO USER dcs_service_user;
```

---

## 5. Implementation Steps

### 5.1 Step-by-Step Guide

#### Step 1: Set up development environment

```bash
# 1. Create feature branch
git checkout -b feature/snowflake-integration

# 2. Install dependencies
cd backend
pip install snowflake-connector-python[pandas]==3.5.0
pip install cryptography>=41.0.0

# 3. Update requirements.txt
echo "snowflake-connector-python[pandas]==3.5.0" >> requirements.txt
echo "cryptography>=41.0.0" >> requirements.txt
```

#### Step 2: Create configuration module

Create `backend/src/parsers/snowflake_config.py`:

```python
"""Configuration for Snowflake metadata parser."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class SnowflakeParserConfig:
    """Configuration for Snowflake metadata parser."""

    # Connection (required)
    account: str
    user: str
    warehouse: str = "COMPUTE_WH"
    role: str = "SYSADMIN"

    # Authentication (one required)
    password: Optional[str] = None
    private_key_path: Optional[Path] = None

    # Scope
    databases: list[str] = field(default_factory=list)
    schemas: list[str] = field(default_factory=list)
    include_views: bool = True
    include_external_tables: bool = True

    # Features
    enable_lineage: bool = True
    lineage_lookback_days: int = 7
    use_account_usage: bool = True
    enable_tag_extraction: bool = True

    # Tag mappings
    tag_mappings: dict[str, dict[str, str]] = field(default_factory=dict)

    # Layer inference patterns
    layer_patterns: dict[str, list[str]] = field(default_factory=lambda: {
        "bronze": [r"^(raw|landing|bronze|stage|l1).*"],
        "silver": [r"^(staging|stg|silver|intermediate|int|l2).*"],
        "gold": [r"^(mart|marts|gold|analytics|prod|l3).*"]
    })

    # Performance
    batch_size: int = 1000
    max_workers: int = 4
    query_timeout_seconds: int = 300

    # Incremental sync
    last_sync_timestamp: Optional[str] = None

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> "SnowflakeParserConfig":
        """Create config from dictionary."""
        # Convert string paths to Path objects
        if "private_key_path" in config and config["private_key_path"]:
            config["private_key_path"] = Path(config["private_key_path"])
        return cls(**config)

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if not self.account:
            errors.append("account is required")
        if not self.user:
            errors.append("user is required")
        if not self.password and not self.private_key_path:
            errors.append("Either password or private_key_path must be provided")
        if self.private_key_path and not self.private_key_path.exists():
            errors.append(f"private_key_path does not exist: {self.private_key_path}")
        if self.lineage_lookback_days < 1 or self.lineage_lookback_days > 365:
            errors.append("lineage_lookback_days must be between 1 and 365")

        return errors
```

#### Step 3: Create query templates module

Create `backend/src/parsers/snowflake_queries.py`:

```python
"""SQL query templates for Snowflake metadata extraction."""

# Extract tables and views from INFORMATION_SCHEMA
QUERY_TABLES = """
SELECT
    TABLE_CATALOG AS database_name,
    TABLE_SCHEMA AS schema_name,
    TABLE_NAME AS table_name,
    TABLE_TYPE,
    ROW_COUNT,
    BYTES,
    CREATED,
    LAST_ALTERED,
    COMMENT AS description
FROM {database}.INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA', 'ACCOUNT_USAGE')
  {schema_filter}
  {type_filter}
  {incremental_filter}
ORDER BY TABLE_SCHEMA, TABLE_NAME
"""

# Extract columns from INFORMATION_SCHEMA
QUERY_COLUMNS = """
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
  {schema_filter}
ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
"""

# Extract lineage from ACCESS_HISTORY
QUERY_LINEAGE = """
WITH lineage_raw AS (
    SELECT DISTINCT
        ah.query_id,
        ah.query_start_time,
        base.value:objectName::STRING AS base_object_name,
        base.value:objectDomain::STRING AS base_object_domain,
        ref.value:objectName::STRING AS referenced_object_name,
        ref.value:objectDomain::STRING AS referenced_object_domain
    FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY ah,
        LATERAL FLATTEN(input => ah.base_objects_accessed) base,
        LATERAL FLATTEN(input => ah.objects_modified, OUTER => TRUE) ref
    WHERE ah.query_start_time >= DATEADD(day, -:lookback_days, CURRENT_TIMESTAMP())
      AND base.value:objectDomain IN ('Table', 'View', 'Materialized view')
      AND (ref.value:objectDomain IN ('Table', 'View', 'Materialized view')
           OR ref.value IS NULL)
)
SELECT
    referenced_object_name AS source_object,
    base_object_name AS target_object,
    COUNT(DISTINCT query_id) AS query_count,
    MAX(query_start_time) AS last_query_time
FROM lineage_raw
WHERE referenced_object_name IS NOT NULL
  AND source_object != target_object
GROUP BY source_object, target_object
ORDER BY query_count DESC
"""

# Extract tags from TAG_REFERENCES
QUERY_TAGS = """
SELECT
    TAG_DATABASE,
    TAG_SCHEMA,
    TAG_NAME,
    TAG_VALUE,
    OBJECT_DATABASE,
    OBJECT_SCHEMA,
    OBJECT_NAME,
    COLUMN_NAME,
    DOMAIN
FROM SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES
WHERE OBJECT_DELETED IS NULL
  AND TAG_DROPPED IS NULL
  {database_filter}
ORDER BY OBJECT_DATABASE, OBJECT_SCHEMA, OBJECT_NAME, COLUMN_NAME
"""

# Get list of accessible databases
QUERY_DATABASES = """
SELECT DATABASE_NAME
FROM SNOWFLAKE.INFORMATION_SCHEMA.DATABASES
WHERE DATABASE_NAME NOT IN ('SNOWFLAKE', 'SNOWFLAKE_SAMPLE_DATA')
ORDER BY DATABASE_NAME
"""
```

#### Step 4: Implement core parser

Create `backend/src/parsers/snowflake_parser.py` (scaffold):

```python
"""Snowflake metadata parser."""

import logging
import re
from pathlib import Path
from typing import Any, Optional

import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from src.parsers.base import (
    MetadataParser,
    ParseError,
    ParseErrorSeverity,
    ParseResult,
    RawCapsule,
    RawColumn,
    RawEdge,
)
from src.parsers.snowflake_config import SnowflakeParserConfig
from src.parsers import snowflake_queries

logger = logging.getLogger(__name__)


class SnowflakeParser(MetadataParser):
    """Parser for Snowflake INFORMATION_SCHEMA and ACCOUNT_USAGE."""

    def __init__(self):
        self.connector: Optional[snowflake.connector.SnowflakeConnection] = None

    @property
    def source_type(self) -> str:
        return "snowflake"

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate configuration."""
        try:
            parser_config = SnowflakeParserConfig.from_dict(config)
            return parser_config.validate()
        except Exception as e:
            return [f"Invalid configuration: {e}"]

    async def parse(self, config: dict[str, Any]) -> ParseResult:
        """Parse Snowflake metadata."""
        result = ParseResult(source_type=self.source_type)

        # Parse and validate config
        try:
            parser_config = SnowflakeParserConfig.from_dict(config)
        except Exception as e:
            result.add_error(
                f"Invalid configuration: {e}",
                severity=ParseErrorSeverity.ERROR
            )
            return result

        validation_errors = parser_config.validate()
        if validation_errors:
            for error in validation_errors:
                result.add_error(error, severity=ParseErrorSeverity.ERROR)
            return result

        # Connect to Snowflake
        try:
            await self._connect(parser_config)
        except Exception as e:
            result.add_error(
                f"Failed to connect to Snowflake: {e}",
                severity=ParseErrorSeverity.ERROR
            )
            return result

        try:
            # Extract metadata
            # TODO: Implement extraction logic
            pass

        finally:
            await self._disconnect()

        return result

    async def _connect(self, config: SnowflakeParserConfig):
        """Establish Snowflake connection."""
        # TODO: Implement connection logic
        pass

    async def _disconnect(self):
        """Close Snowflake connection."""
        if self.connector:
            self.connector.close()
            self.connector = None

    # TODO: Add extraction methods
```

#### Step 5: Register parser

Update `backend/src/parsers/__init__.py`:

```python
from src.parsers.base import MetadataParser, ParserRegistry, ParseResult
from src.parsers.dbt_parser import DbtParser
from src.parsers.airflow_parser import AirflowParser
from src.parsers.snowflake_parser import SnowflakeParser  # Add this

# Global parser registry
parser_registry = ParserRegistry()
parser_registry.register("dbt", DbtParser)
parser_registry.register("airflow", AirflowParser)
parser_registry.register("snowflake", SnowflakeParser)  # Add this

__all__ = [
    "MetadataParser",
    "ParserRegistry",
    "ParseResult",
    "DbtParser",
    "AirflowParser",
    "SnowflakeParser",  # Add this
    "parser_registry",
]
```

#### Step 6: Add API endpoint

Update `backend/src/api/routers/ingest.py` to add Snowflake endpoint (follow existing dbt pattern).

#### Step 7: Add CLI command

Update `backend/src/cli/commands/ingest.py` to add snowflake subcommand (follow existing dbt pattern).

#### Step 8: Write tests

Create test files following the structure in section 3.1.

---

## 6. Testing Plan

### 6.1 Unit Tests

**Coverage Target:** >80%

**Test Categories:**
1. Configuration validation
2. URN generation
3. Layer inference
4. Tag mapping
5. Connection handling (mocked)
6. Query building
7. Result parsing

**Example Test:**
```python
# tests/unit/parsers/test_snowflake_parser.py

import pytest
from src.parsers.snowflake_parser import SnowflakeParser
from src.parsers.snowflake_config import SnowflakeParserConfig


def test_config_validation_missing_account():
    """Test config validation fails when account is missing."""
    config = {"user": "test", "password": "test"}
    errors = SnowflakeParserConfig.from_dict(config).validate()
    assert "account is required" in errors


def test_layer_inference_bronze():
    """Test layer inference for bronze/raw schemas."""
    parser = SnowflakeParser()
    assert parser._infer_layer("raw_data", None) == "bronze"
    assert parser._infer_layer("landing", None) == "bronze"


def test_urn_generation():
    """Test URN generation for Snowflake objects."""
    parser = SnowflakeParser()
    urn = parser._build_urn("BASE TABLE", "PROD", "RAW_DATA", "CUSTOMERS")
    assert urn == "urn:dcs:snowflake:table:PROD.RAW_DATA:CUSTOMERS"
```

### 6.2 Integration Tests

**Prerequisites:**
- Test Snowflake account with sample data
- Service user with appropriate permissions
- Credentials in environment variables

**Test Scenarios:**
1. Full ingestion from test database
2. Incremental sync with changed objects
3. Lineage extraction with sample queries
4. Tag extraction with tagged columns
5. Error handling (permission denied, timeout)

**Example Test:**
```python
# tests/integration/test_snowflake_integration.py

import os
import pytest
from src.parsers.snowflake_parser import SnowflakeParser


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("SNOWFLAKE_ACCOUNT"),
    reason="Snowflake credentials not configured"
)
async def test_snowflake_ingestion():
    """Test full Snowflake ingestion against test account."""
    parser = SnowflakeParser()
    config = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "password": os.environ["SNOWFLAKE_PASSWORD"],
        "warehouse": "METADATA_WH",
        "databases": ["TEST_DCS"],
        "enable_lineage": False  # Skip for speed
    }

    result = await parser.parse(config)

    assert not result.has_errors
    assert len(result.capsules) > 0
    assert len(result.columns) > 0
    print(f"Extracted {len(result.capsules)} capsules, {len(result.columns)} columns")
```

### 6.3 Performance Tests

**Scenarios:**
1. 100 tables, 5K columns (Small)
2. 1,000 tables, 50K columns (Medium)
3. 10,000 tables, 500K columns (Large)

**Metrics:**
- Query time
- Ingestion time
- Memory usage
- Warehouse credit consumption

---

## 7. Deployment Strategy

### 7.1 Pre-Production Checklist

- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Performance benchmarks within targets
- [ ] Security review complete
- [ ] Documentation complete
- [ ] Example configurations tested
- [ ] Backward compatibility verified

### 7.2 Rollout Phases

**Phase 1: Internal Testing (Week 8)**
- Deploy to internal dev environment
- Test with internal Snowflake accounts
- Gather feedback from team

**Phase 2: Beta Testing (Week 9-10)**
- Deploy to staging environment
- Invite select users for beta testing
- Monitor for issues, gather feedback

**Phase 3: General Availability (Week 11)**
- Deploy to production
- Announce feature in release notes
- Provide migration guide for existing users

### 7.3 Monitoring

**Key Metrics:**
- Ingestion success rate
- Average ingestion time
- Error rate by type
- Snowflake warehouse credit usage
- API endpoint latency

**Alerts:**
- Ingestion failure rate > 5%
- Ingestion time > 15 minutes
- Snowflake connection failures

---

## 8. Success Criteria

### 8.1 Functional Requirements

- [ ] Can connect to Snowflake with key-pair authentication
- [ ] Extracts tables, views, materialized views, external tables
- [ ] Extracts columns with data types and constraints
- [ ] Generates correct URNs for all object types
- [ ] Infers layers from schema names
- [ ] Extracts lineage from ACCESS_HISTORY
- [ ] Extracts and applies Snowflake tags
- [ ] Supports incremental sync
- [ ] Exposes API endpoint for ingestion
- [ ] Provides CLI command for ingestion
- [ ] Stores metadata in DCS graph
- [ ] Handles errors gracefully

### 8.2 Non-Functional Requirements

- [ ] Ingestion time < 10 minutes for 10K objects
- [ ] Incremental sync < 30 seconds for 100 changed objects
- [ ] Unit test coverage > 80%
- [ ] Error rate < 1% of objects
- [ ] Lineage accuracy > 90%
- [ ] Documentation complete and reviewed
- [ ] Security review passed

### 8.3 Quality Gates

Each sprint must meet:
- All unit tests passing
- Code reviewed and approved
- Documentation updated
- No critical bugs

Before GA:
- All acceptance criteria met
- Performance benchmarks passed
- Security review complete
- Beta testing feedback addressed

---

## Appendices

### Appendix A: Sample Configuration File

```yaml
# config/snowflake_prod.yaml
source_type: snowflake

# Connection
account: myorg-account123
user: dcs_service_user
private_key_path: /secure/snowflake_key.p8
warehouse: METADATA_WH
role: METADATA_READER

# Scope
databases:
  - PROD
  - ANALYTICS
schemas:
  - PROD.RAW_*
  - PROD.STAGING_*
  - ANALYTICS.*

# Features
enable_lineage: true
lineage_lookback_days: 7
enable_tag_extraction: true

# Tag mappings
tag_mappings:
  PII:
    semantic_type: pii
  PII:EMAIL:
    semantic_type: pii
    pii_type: email

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

# Performance
batch_size: 1000
max_workers: 4
query_timeout_seconds: 300
```

### Appendix B: CLI Usage Examples

```bash
# Full ingestion with config file
dcs ingest snowflake --config config/snowflake_prod.yaml

# Incremental sync
dcs ingest snowflake --config config/snowflake_prod.yaml --incremental

# Override config with CLI flags
dcs ingest snowflake \
  --account myorg-account123 \
  --user dcs_user \
  --password $SNOWFLAKE_PASSWORD \
  --databases PROD,ANALYTICS \
  --enable-lineage

# Dry run (validate config, don't ingest)
dcs ingest snowflake --config config/snowflake_prod.yaml --dry-run
```

### Appendix C: API Usage Examples

```bash
# Trigger Snowflake ingestion via API
curl -X POST http://localhost:8001/api/v1/ingest/snowflake \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d @config/snowflake_config.json

# Check ingestion status
curl http://localhost:8001/api/v1/ingest/jobs/{job_id} \
  -H "X-API-Key: your-api-key"

# Query Snowflake capsules
curl "http://localhost:8001/api/v1/capsules?source=snowflake&layer=gold" \
  -H "X-API-Key: your-api-key"
```

### Appendix D: Troubleshooting Guide

**Issue: Connection timeout**
- Verify network connectivity to Snowflake
- Check warehouse is running
- Increase `query_timeout_seconds`

**Issue: Permission denied on ACCOUNT_USAGE**
- Ensure role has `IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE`
- Verify user has correct role assigned
- Contact Snowflake admin

**Issue: Lineage extraction slow**
- Reduce `lineage_lookback_days`
- Filter to specific databases
- Use larger warehouse for ACCESS_HISTORY queries

**Issue: Incremental sync not working**
- Verify `last_sync_timestamp` is persisted
- Check `LAST_ALTERED` timestamps in Snowflake
- Review ingestion job logs

---

*End of Snowflake Integration Implementation Plan*
