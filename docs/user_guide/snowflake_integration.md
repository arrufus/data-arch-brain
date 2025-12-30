# Snowflake Integration - User Guide

**Version**: 1.0
**Date**: December 24, 2024
**Status**: Production Ready

---

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Quickstart](#quickstart)
4. [Configuration Reference](#configuration-reference)
5. [Usage Examples](#usage-examples)
6. [Features](#features)
7. [Performance Tuning](#performance-tuning)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Introduction

The Snowflake integration allows you to automatically extract metadata from your Snowflake data warehouse, including:

- **Tables, Views, and Materialized Views**: Schema structure and metadata
- **Columns**: Data types, nullability, descriptions
- **Lineage**: Table-to-table data flow relationships
- **Tags**: PII detection and semantic classification
- **Layer Inference**: Bronze/Silver/Gold classification

### Key Benefits

- **Automated Discovery**: No manual documentation required
- **Lineage Tracking**: Understand data dependencies
- **PII Detection**: Identify sensitive data automatically
- **Incremental Sync**: Fast updates, low cost
- **Production-Grade**: Robust error handling and retry logic

---

## Prerequisites

### Snowflake Requirements

1. **Snowflake Account**: Active Snowflake account
2. **Service Account**: Dedicated user for DCS integration
3. **Warehouse**: X-Small warehouse (or larger)
4. **Permissions**: Grant appropriate roles/privileges

### Snowflake Setup

#### 1. Create Service User

```sql
-- Create user for DCS integration
CREATE USER dcs_service_user
  PASSWORD = 'YOUR_SECURE_PASSWORD'
  DEFAULT_ROLE = DCS_READER
  DEFAULT_WAREHOUSE = COMPUTE_WH
  MUST_CHANGE_PASSWORD = FALSE;
```

#### 2. Create Role with Minimal Privileges

```sql
-- Create role for DCS
CREATE ROLE DCS_READER;

-- Grant database read access
GRANT USAGE ON DATABASE PROD TO ROLE DCS_READER;
GRANT USAGE ON ALL SCHEMAS IN DATABASE PROD TO ROLE DCS_READER;
GRANT SELECT ON ALL TABLES IN DATABASE PROD TO ROLE DCS_READER;
GRANT SELECT ON ALL VIEWS IN DATABASE PROD TO ROLE DCS_READER;
GRANT SELECT ON FUTURE TABLES IN DATABASE PROD TO ROLE DCS_READER;
GRANT SELECT ON FUTURE VIEWS IN DATABASE PROD TO ROLE DCS_READER;

-- Grant warehouse usage
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE DCS_READER;

-- Grant ACCOUNT_USAGE access (required for lineage and tags)
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE DCS_READER;

-- Assign role to user
GRANT ROLE DCS_READER TO USER dcs_service_user;
```

#### 3. (Optional) Key-Pair Authentication

For enhanced security, use key-pair authentication:

```bash
# Generate private key
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out snowflake_key.p8 -nocrypt

# Generate public key
openssl rsa -in snowflake_key.p8 -pubout -out snowflake_key.pub

# Upload public key to Snowflake
ALTER USER dcs_service_user SET RSA_PUBLIC_KEY='<public_key_content>';
```

### DCS Requirements

- **DCS Backend**: Version 1.0+ with Snowflake parser
- **Python**: 3.8+
- **Dependencies**: `snowflake-connector-python`, `cryptography` (for key-pair auth)

---

## Quickstart

### 1. Basic Ingestion (Password Auth)

```python
from src.parsers.snowflake_parser import SnowflakeParser

# Create parser
parser = SnowflakeParser()

# Configure connection
config = {
    "account": "myorg-account123",  # Format: orgname-accountname
    "user": "dcs_service_user",
    "password": "YOUR_SECURE_PASSWORD",
    "warehouse": "COMPUTE_WH",
    "role": "DCS_READER",
    "databases": ["PROD"],  # Specific databases or leave empty for all
}

# Parse metadata
result = await parser.parse(config)

# Access results
print(f"Extracted {len(result.capsules)} tables/views")
print(f"Extracted {len(result.columns)} columns")
print(f"Extracted {len(result.edges)} lineage edges")
```

### 2. Using CLI

```bash
# Set password as environment variable
export SNOWFLAKE_PASSWORD="your_secure_password"

# Run ingestion
dcs ingest snowflake \
  --account myorg-account123 \
  --user dcs_service_user \
  --warehouse COMPUTE_WH \
  --role DCS_READER \
  --databases PROD

# View results
dcs list capsules --source snowflake
```

### 3. Incremental Sync (After First Run)

```python
# First sync (full)
result1 = await parser.parse(config)
last_timestamp = result1.metadata["last_sync_timestamp"]

# Store timestamp for next run
# (in your application database or config file)

# Subsequent sync (incremental)
config["last_sync_timestamp"] = last_timestamp
result2 = await parser.parse(config)

# Only changed tables are re-ingested
print(f"Sync mode: {result2.metadata['sync_mode']}")  # "incremental"
```

### Expected Timeline

Following this quickstart, you should be able to:
- ✅ Configure Snowflake user and permissions: **5 minutes**
- ✅ Run first ingestion: **5 minutes** (setup + execution)
- ✅ Verify results: **5 minutes**

**Total**: < 15 minutes to first successful ingestion

---

## Configuration Reference

### Connection Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `account` | string | Yes | - | Snowflake account identifier (orgname-accountname) |
| `user` | string | Yes | - | Snowflake username |
| `password` | string | Conditional | - | Password (required if not using key-pair) |
| `private_key_path` | Path | Conditional | - | Path to private key file (for key-pair auth) |
| `warehouse` | string | No | `"COMPUTE_WH"` | Warehouse for queries |
| `role` | string | No | `"SYSADMIN"` | Role to use for queries |

**Authentication Notes**:
- Provide either `password` OR `private_key_path`
- Use environment variable for password: `password_env: "SNOWFLAKE_PASSWORD"`

### Scope Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `databases` | list[str] | No | `[]` | Specific databases (empty = all accessible) |
| `schemas` | list[str] | No | `[]` | Specific schemas (empty = all) |
| `include_views` | bool | No | `True` | Include views |
| `include_materialized_views` | bool | No | `True` | Include materialized views |
| `include_external_tables` | bool | No | `True` | Include external tables |

### Feature Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `enable_lineage` | bool | No | `True` | Extract lineage from ACCESS_HISTORY |
| `enable_tag_extraction` | bool | No | `True` | Extract tags from TAG_REFERENCES |
| `use_account_usage` | bool | No | `True` | Use ACCOUNT_USAGE views (required for lineage/tags) |
| `lineage_lookback_days` | int | No | `7` | Lineage history window (1-365 days) |

**Feature Notes**:
- Lineage and tags require `use_account_usage: True`
- Longer lookback = more comprehensive but slower/costlier

### Performance Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `parallel_execution` | bool | No | `True` | Process databases concurrently |
| `enable_query_cache` | bool | No | `True` | Cache query results |
| `max_lineage_rows` | int | No | `10000` | Limit ACCESS_HISTORY query rows |
| `batch_size` | int | No | `1000` | Batch size for operations |
| `max_workers` | int | No | `4` | Max concurrent workers |
| `query_timeout_seconds` | int | No | `300` | Query timeout (seconds) |

**Performance Notes**:
- Parallel execution recommended for 2+ databases
- Lower `max_lineage_rows` for faster/cheaper lineage

### Incremental Sync Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `last_sync_timestamp` | string | No | `None` | Last sync timestamp (ISO 8601 format) |

**Format**: `"2024-12-24T10:00:00+00:00"`

### Tag Mapping Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `tag_mappings` | dict | No | See defaults | Custom tag-to-semantic-type mappings |

**Default Mappings**:
```python
{
    "PII": {"semantic_type": "pii", "infer_pii_type": True},
    "PII:EMAIL": {"semantic_type": "pii", "pii_type": "email"},
    "PII:PHONE": {"semantic_type": "pii", "pii_type": "phone"},
    "PII:SSN": {"semantic_type": "pii", "pii_type": "ssn"},
    "PRIMARY_KEY": {"semantic_type": "business_key"},
    "FOREIGN_KEY": {"semantic_type": "foreign_key"},
}
```

### Layer Inference Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `layer_patterns` | dict | No | See defaults | Schema name patterns for layer inference |

**Default Patterns**:
```python
{
    "bronze": [r"^(raw|landing|bronze|stage|l1).*", r".*_raw$"],
    "silver": [r"^(staging|stg|silver|intermediate|int|l2).*", r".*_stg$"],
    "gold": [r"^(mart|marts|gold|analytics|prod|l3).*", r".*_analytics$"],
}
```

---

## Usage Examples

### Example 1: Basic Ingestion (Single Database)

```python
config = {
    "account": "myorg-account123",
    "user": "dcs_service_user",
    "password": "YOUR_PASSWORD",
    "databases": ["PROD"],
}

result = await parser.parse(config)
print(f"Extracted {len(result.capsules)} capsules from PROD")
```

### Example 2: Multiple Databases with Parallel Execution

```python
config = {
    "account": "myorg-account123",
    "user": "dcs_service_user",
    "password": "YOUR_PASSWORD",
    "databases": ["PROD", "DEV", "STAGING"],
    "parallel_execution": True,  # Processes databases concurrently
}

result = await parser.parse(config)
# 2-3x faster than sequential for multiple databases
```

### Example 3: Key-Pair Authentication

```python
from pathlib import Path

config = {
    "account": "myorg-account123",
    "user": "dcs_service_user",
    "private_key_path": Path("/path/to/snowflake_key.p8"),
    "databases": ["PROD"],
}

result = await parser.parse(config)
```

### Example 4: Filtered Ingestion (Specific Schemas)

```python
config = {
    "account": "myorg-account123",
    "user": "dcs_service_user",
    "password": "YOUR_PASSWORD",
    "databases": ["PROD"],
    "schemas": ["PUBLIC", "ANALYTICS"],  # Only these schemas
    "include_views": True,
    "include_materialized_views": True,
}

result = await parser.parse(config)
```

### Example 5: Incremental Sync

```python
# Store timestamp from previous sync
previous_timestamp = "2024-12-24T10:00:00+00:00"

config = {
    "account": "myorg-account123",
    "user": "dcs_service_user",
    "password": "YOUR_PASSWORD",
    "databases": ["PROD"],
    "last_sync_timestamp": previous_timestamp,
}

result = await parser.parse(config)

# Store new timestamp for next sync
new_timestamp = result.metadata["last_sync_timestamp"]
# Save new_timestamp to database/config for next run
```

### Example 6: Cost-Optimized Configuration

```python
config = {
    "account": "myorg-account123",
    "user": "dcs_service_user",
    "password": "YOUR_PASSWORD",
    "warehouse": "COMPUTE_WH",  # X-Small warehouse
    "databases": ["PROD"],
    "max_lineage_rows": 5000,  # Aggressive limit
    "lineage_lookback_days": 3,  # Shorter window
    "enable_tag_extraction": False,  # Disable if not needed
}

result = await parser.parse(config)
# Minimizes Snowflake compute costs
```

### Example 7: Performance-Optimized Configuration

```python
config = {
    "account": "myorg-account123",
    "user": "dcs_service_user",
    "password": "YOUR_PASSWORD",
    "databases": ["PROD", "DEV"],
    "parallel_execution": True,
    "enable_query_cache": True,
    "max_lineage_rows": 10000,
    "last_sync_timestamp": previous_timestamp,  # Incremental
}

result = await parser.parse(config)
# Fastest ingestion with all optimizations
```

### Example 8: Custom Tag Mappings

```python
config = {
    "account": "myorg-account123",
    "user": "dcs_service_user",
    "password": "YOUR_PASSWORD",
    "databases": ["PROD"],
    "tag_mappings": {
        # Override default mappings
        "SENSITIVE": {"semantic_type": "pii", "pii_type": "confidential"},
        "CUSTOMER_ID": {"semantic_type": "business_key"},
        # Add custom mappings
        "GDPR": {"semantic_type": "pii", "pii_type": "gdpr_protected"},
    }
}

result = await parser.parse(config)
```

### Example 9: Using Environment Variables

```python
import os

config = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
    "databases": os.getenv("SNOWFLAKE_DATABASES", "PROD").split(","),
}

result = await parser.parse(config)
```

### Example 10: Accessing Results

```python
result = await parser.parse(config)

# Access capsules (tables/views)
for capsule in result.capsules:
    print(f"Table: {capsule.unique_id}")
    print(f"  Type: {capsule.capsule_type}")
    print(f"  Layer: {capsule.layer}")
    print(f"  Row count: {capsule.meta.get('row_count')}")

# Access columns
for column in result.columns:
    print(f"Column: {column.name}")
    print(f"  Type: {column.data_type}")
    print(f"  PII: {column.pii_type}")
    print(f"  Semantic: {column.semantic_type}")

# Access lineage edges
for edge in result.edges:
    print(f"Lineage: {edge.source_urn} -> {edge.target_urn}")
    print(f"  Query count: {edge.meta.get('query_count')}")

# Access performance metrics
perf = result.metadata["performance"]
print(f"Duration: {perf['total_duration_seconds']}s")
print(f"Capsules: {perf['capsules_extracted']}")
print(f"Columns: {perf['columns_extracted']}")
print(f"Edges: {perf['edges_extracted']}")

# Access errors
for error in result.errors:
    print(f"Error: {error.message}")
    print(f"  Severity: {error.severity}")
    print(f"  Context: {error.context}")
```

---

## Features

### 1. Metadata Extraction

Extracts comprehensive metadata from Snowflake:

**Tables & Views**:
- Table name, database, schema
- Table type (BASE TABLE, VIEW, MATERIALIZED VIEW, EXTERNAL TABLE)
- Row count, size in bytes
- Created and last modified timestamps
- Descriptions/comments

**Columns**:
- Column name, data type
- Nullability, default values
- Position, length, precision, scale
- Descriptions/comments

### 2. Lineage Extraction

Automatically discovers table-to-table lineage from `ACCESS_HISTORY`:

- Source and target tables
- Query count (how frequently accessed)
- Last query timestamp
- Filters to relevant databases
- De-duplicates relationships
- Configurable lookback window (1-365 days)

**Requirements**:
- `enable_lineage: True`
- `use_account_usage: True`
- `IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE` granted

### 3. Tag Extraction & PII Detection

Extracts tags from `TAG_REFERENCES` and applies semantic classification:

**Default Tag Mappings**:
- `PII` → Infers specific PII type from column name
- `PII:EMAIL` → Email address
- `PII:PHONE` → Phone number
- `PII:SSN` → Social Security Number
- `PRIMARY_KEY` → Business key
- `FOREIGN_KEY` → Foreign key

**Automatic PII Inference**:
If column has `PII` tag but no specific type, infers from column name:
- `email`, `e_mail`, `user_email` → `email`
- `phone`, `telephone`, `mobile` → `phone`
- `ssn`, `social_security` → `ssn`
- `address`, `addr`, `street` → `address`

### 4. Layer Inference

Automatically classifies tables into medallion architecture layers based on schema name patterns:

- **Bronze**: `raw`, `landing`, `bronze`, `stage`, `l1`
- **Silver**: `staging`, `stg`, `silver`, `intermediate`, `int`, `l2`
- **Gold**: `mart`, `marts`, `gold`, `analytics`, `prod`, `l3`

Customizable via `layer_patterns` parameter.

### 5. Incremental Sync

Dramatically reduces ingestion time and costs:

- Only queries tables modified since last sync
- Uses `LAST_ALTERED` timestamp filter
- 80-90% reduction in query time for regular syncs
- Stores timestamp for next run in `result.metadata["last_sync_timestamp"]`

**Best Practice**: Run periodic full syncs (weekly) for validation.

### 6. Parallel Execution

Processes multiple databases concurrently:

- 2-3x performance improvement for multi-database ingestion
- Automatic for 2+ databases
- Configurable via `parallel_execution` parameter

### 7. Query Caching

Caches database list to eliminate redundant queries:

- Reduces INFORMATION_SCHEMA queries
- Minimal memory overhead
- Configurable via `enable_query_cache` parameter

### 8. Error Handling & Resilience

Production-grade error handling:

- Exponential backoff retry (3 attempts)
- Partial success (continues on individual failures)
- Detailed error context
- Helpful error messages

---

## Performance Tuning

See [Snowflake Performance Tuning Guide](../snowflake_performance_tuning.md) for detailed tuning recommendations.

### Quick Tips

**For Fast Ingestion**:
- Enable parallel execution (`parallel_execution: True`)
- Use incremental sync after first run
- Limit lineage rows (`max_lineage_rows: 10000`)

**For Cost Optimization**:
- Use X-Small warehouse
- Reduce lineage lookback window (`lineage_lookback_days: 3`)
- Disable unused features
- Use incremental sync

**For Large Datasets (>50K objects)**:
- Filter to specific databases/schemas
- Disable lineage/tags if not needed
- Use aggressive lineage limits (`max_lineage_rows: 5000`)

---

## Troubleshooting

See [Troubleshooting Guide](./snowflake_troubleshooting.md) for detailed troubleshooting.

### Common Issues

**Connection Failed**:
- Verify account identifier format: `orgname-accountname`
- Check user credentials
- Verify warehouse exists and is accessible
- Check role permissions

**Slow Ingestion**:
- Enable parallel execution
- Use incremental sync
- Reduce lineage lookback window
- Filter to specific databases

**Missing Lineage/Tags**:
- Verify `use_account_usage: True`
- Check `IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE` granted
- Verify warehouse has access to ACCOUNT_USAGE

**High Costs**:
- Use X-Small warehouse
- Limit lineage rows
- Reduce lineage lookback window
- Use incremental sync

---

## FAQ

### Q: How often should I run ingestion?

**A**: Depends on your change frequency:
- **High change rate**: Hourly (use incremental sync)
- **Medium change rate**: Daily (use incremental sync)
- **Low change rate**: Weekly (full sync)

Run periodic full syncs (weekly) for validation.

### Q: What warehouse size should I use?

**A**: X-Small (COMPUTE_WH) is recommended for most use cases. Only use larger warehouses for very large datasets (>100K objects).

### Q: Does ingestion modify my Snowflake data?

**A**: No, ingestion is read-only. It only queries metadata views and never modifies data or schema.

### Q: How much does ingestion cost?

**A**: With X-Small warehouse and default settings:
- **1K objects**: ~$0.001/sync
- **10K objects**: ~$0.01/sync
- **50K objects**: ~$0.04/sync

With incremental sync, costs reduce by 80-90%.

### Q: Can I ingest from multiple Snowflake accounts?

**A**: Yes, run separate ingestion for each account. Configure different service users for each account.

### Q: How do I store passwords securely?

**A**: Use environment variables or key-pair authentication:
- Environment variable: `password_env: "SNOWFLAKE_PASSWORD"`
- Key-pair: `private_key_path: "/path/to/key.p8"`

### Q: What permissions are required?

**A**: Minimal permissions:
- `USAGE` on database, schemas, warehouse
- `SELECT` on tables/views
- `IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE` (for lineage/tags)

See [Prerequisites](#snowflake-setup) for detailed setup.

### Q: Can I customize PII detection?

**A**: Yes, via `tag_mappings` parameter. Add custom tags or override defaults.

### Q: How do I handle deleted tables?

**A**: Incremental sync only detects changed tables. Run periodic full syncs to detect deletions, or enable cleanup in ingestion service.

### Q: What if I don't have ACCOUNT_USAGE access?

**A**: Disable lineage and tag extraction:
```python
config = {
    "enable_lineage": False,
    "enable_tag_extraction": False,
    "use_account_usage": False,
}
```

You'll still get table/column metadata from INFORMATION_SCHEMA.

---

## Next Steps

1. **Complete Quickstart**: Follow the [Quickstart](#quickstart) to run your first ingestion
2. **Tune Performance**: Review [Performance Tuning Guide](../snowflake_performance_tuning.md)
3. **Automate**: Schedule regular ingestion (hourly/daily) with incremental sync
4. **Monitor**: Track performance metrics in `result.metadata["performance"]`
5. **Explore**: Use DCS web UI to explore extracted metadata

---

## Support

For issues or questions:
1. Review this guide and [Troubleshooting Guide](./snowflake_troubleshooting.md)
2. Check performance metrics in `result.metadata`
3. Review logs for detailed error messages
4. Open GitHub issue with configuration and error details

---

*Last Updated: December 24, 2024*
*Version: 1.0 - Production Ready*
