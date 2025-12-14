# Data Architecture Brain - User Guide

## Overview

Data Architecture Brain (DAB) is a read-only architecture intelligence platform that helps you understand, govern, and optimize your data landscape. It ingests metadata from dbt projects and provides insights into:

- **PII/Sensitive Data Tracking**: Trace sensitive data through your transformation pipelines
- **Architecture Conformance**: Detect anti-patterns and validate against best practices
- **Lineage Analysis**: Understand data flow at model and column level
- **Impact Analysis**: Assess downstream effects of changes
- **Violation Management**: Track and resolve conformance violations

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- A dbt project with `manifest.json` and optionally `catalog.json`

### Starting the Services

```bash
# Start PostgreSQL and the API server via Docker
cd docker
docker compose up -d

# Or run locally for development
cd backend
source .venv/bin/activate
dab serve
```

The API server runs on port **8002** by default.

### Authentication

DAB requires API key authentication by default. Include your API key in requests:

```bash
# CLI commands use the configured API key automatically
dab capsules

# For API requests, include the X-API-Key header
curl -H "X-API-Key: dev-api-key-change-in-prod" http://localhost:8002/api/v1/capsules
```

Health endpoints (`/health`, `/health/live`, `/health/ready`) are exempt from authentication.

### Ingesting Your First dbt Project

```bash
# Ingest from manifest.json
dab ingest dbt --manifest /path/to/your/dbt/target/manifest.json

# Include catalog for column metadata (recommended)
dab ingest dbt --manifest /path/to/manifest.json --catalog /path/to/catalog.json
```

---

## CLI Commands Reference

### `dab ingest` - Ingest Metadata

Ingest metadata from a dbt project:

```bash
# Basic ingestion (dbt is the default source type)
dab ingest --manifest /path/to/manifest.json

# Explicit source type
dab ingest dbt --manifest /path/to/manifest.json

# With catalog for column info
dab ingest dbt --manifest /path/to/manifest.json --catalog /path/to/catalog.json

# With project name override
dab ingest dbt --manifest /path/to/manifest.json --project my_project
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--manifest` | `-m` | Path to manifest.json (required) |
| `--catalog` | `-c` | Path to catalog.json (optional) |
| `--project` | `-p` | Project name override |

**Example Output:**
```
Ingesting dbt project...
✓ Parsed 45 models
✓ Detected 12 PII columns
✓ Created 128 lineage edges
Ingestion completed in 2.3s
```

---

### `dab capsules` - List Data Assets

Browse your data capsules (models, sources, seeds):

```bash
# List all capsules (default limit: 20)
dab capsules

# Filter by layer
dab capsules --layer gold

# Filter by type
dab capsules --type model

# Search by name
dab capsules --search customers

# Limit results
dab capsules --limit 50
```

**Options:**
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--layer` | `-l` | Filter by layer (bronze, silver, gold) | - |
| `--type` | `-t` | Filter by type (model, source, seed) | - |
| `--search` | `-s` | Search by name | - |
| `--limit` | `-n` | Number of results | 20 |

**Example Output:**
```
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━┳━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name               ┃ Type   ┃ Layer  ┃ Cols ┃ PII ┃ URN                                            ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━╇━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ dim_customers      │ model  │ gold   │   12 │ Yes │ urn:dab:dbt:model:jaffle_shop.marts:dim_cust...│
│ fct_orders         │ model  │ gold   │    8 │ No  │ urn:dab:dbt:model:jaffle_shop.marts:fct_orders │
│ stg_customers      │ model  │ silver │    6 │ Yes │ urn:dab:dbt:model:jaffle_shop.staging:stg_cu...│
└────────────────────┴────────┴────────┴──────┴─────┴────────────────────────────────────────────────┘
```

---

### `dab stats` - Architecture Statistics

Get a summary of your data architecture:

```bash
dab stats
```

**Example Output:**
```
Architecture Statistics
━━━━━━━━━━━━━━━━━━━━━━━━

Capsules by Type:
  model:    45
  source:   12
  seed:      3
  Total:    60

Capsules by Layer:
  bronze:   12
  silver:   25
  gold:     18
  unknown:   5

Columns:
  Total:           324
  PII columns:      18
  Documented:      286 (88%)

PII by Type:
  email:     6
  name:      5
  phone:     4
  address:   3
```

---

### `dab pii` - List PII Columns

Find all columns tagged as containing PII:

```bash
# List all PII columns (default limit: 50)
dab pii

# Filter by PII type
dab pii --type email

# Limit results
dab pii --limit 100
```

**Options:**
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--type` | `-t` | Filter by PII type (email, phone, name, ssn, address) | - |
| `--limit` | `-n` | Number of results | 50 |

**Example Output:**
```
PII Columns (18 total)
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Column             ┃ Capsule            ┃ PII Type  ┃ Detection   ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ customer_email     │ dim_customers      │ email     │ pattern     │
│ first_name         │ dim_customers      │ name      │ tag         │
│ last_name          │ dim_customers      │ name      │ tag         │
│ phone_number       │ stg_customers      │ phone     │ pattern     │
└────────────────────┴────────────────────┴───────────┴─────────────┘
```

---

### `dab pii-inventory` - PII Inventory Report

Generate a comprehensive PII inventory:

```bash
# Table format (default)
dab pii-inventory

# JSON format
dab pii-inventory --format json

# Filter by PII type
dab pii-inventory --type email

# Filter by layer
dab pii-inventory --layer gold
```

**Options:**
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--type` | `-t` | Filter by PII type | - |
| `--layer` | `-l` | Filter by layer | - |
| `--format` | `-f` | Output format: table, json | table |

**Example Output:**
```
PII Inventory Report
━━━━━━━━━━━━━━━━━━━━━

Summary:
  Total PII columns:     18
  Affected capsules:     8

By PII Type:
  email:     6 columns
  name:      5 columns
  phone:     4 columns
  address:   3 columns

By Layer:
  bronze:    4 columns (raw data)
  silver:    8 columns (staged)
  gold:      6 columns (exposed!)
```

---

### `dab pii-exposure` - Detect Exposed PII

Find PII that may be exposed in consumption layers:

```bash
# Check for exposed PII
dab pii-exposure

# Filter by layer
dab pii-exposure --layer gold

# Filter by severity
dab pii-exposure --severity critical
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--layer` | `-l` | Layer to check |
| `--severity` | `-s` | Filter by severity (critical, high, medium, low) |

**Example Output:**
```
PII Exposure Report
━━━━━━━━━━━━━━━━━━━━

⚠️  6 PII columns exposed in gold layer

Critical Exposures:
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Column        ┃ Capsule            ┃ PII Type  ┃ Risk                            ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ email         │ dim_customers      │ email     │ Direct identifier in gold layer │
│ ssn           │ dim_employees      │ ssn       │ Sensitive ID in gold layer      │
└───────────────┴────────────────────┴───────────┴─────────────────────────────────┘

Recommendation: Consider masking or hashing PII before exposing to gold layer.
```

---

### `dab lineage` - Trace Lineage

View upstream and downstream dependencies:

```bash
# Show lineage for a capsule (both directions)
dab lineage urn:dab:dbt:model:jaffle_shop.staging:stg_customers

# Only upstream dependencies (where data comes from)
dab lineage <urn> --direction upstream

# Only downstream dependencies (what depends on this)
dab lineage <urn> --direction downstream

# Increase depth
dab lineage <urn> --depth 5
```

**Options:**
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--direction` | `-d` | upstream, downstream, or both | both |
| `--depth` | - | How many levels to traverse | 3 |

**Example Output:**
```
Lineage for: stg_customers
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Upstream (sources):
  raw_customers (source)
    └─→ stg_customers

Downstream (dependents):
  stg_customers
    └─→ int_customer_orders
        └─→ dim_customers
        └─→ fct_orders
```

---

### `dab conformance` - Conformance Score

Check architecture conformance against best practices:

```bash
# Show overall conformance score
dab conformance

# Filter by rule set
dab conformance --rule-set medallion

# Filter by category
dab conformance --category naming
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--rule-set` | `-r` | Filter by rule set (medallion, dbt_best_practices, pii_compliance) |
| `--category` | `-c` | Filter by category (naming, lineage, pii, documentation, testing) |

**Example Output:**
```
Conformance Score: 78%
━━━━━━━━━━━━━━━━━━━━━━

By Severity:
  Critical:  2 failing / 5 total
  Error:     5 failing / 20 total
  Warning:   8 failing / 35 total
  Info:      3 failing / 15 total

By Category:
  naming:         85%
  lineage:        72%
  pii:            65%
  documentation:  90%
  testing:        70%

Run 'dab conformance-violations' to see specific violations.
```

---

### `dab conformance-violations` - List Violations

View conformance rule violations:

```bash
# List all violations (default limit: 50)
dab conformance-violations

# Filter by severity
dab conformance-violations --severity error

# Filter by category
dab conformance-violations --category naming

# Filter by rule set
dab conformance-violations --rule-set dbt_best_practices

# Limit results
dab conformance-violations --limit 100
```

**Options:**
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--severity` | `-s` | Filter by severity | - |
| `--category` | `-c` | Filter by category | - |
| `--rule-set` | `-r` | Filter by rule set | - |
| `--limit` | `-n` | Number of results | 50 |

**Example Output:**
```
Conformance Violations (18 total)
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Severity   ┃ Rule                       ┃ Capsule            ┃ Status  ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ error      │ staging_prefix_required    │ customers          │ open    │
│ error      │ gold_from_silver           │ dim_raw_customers  │ open    │
│ warning    │ model_description_required │ int_orders         │ open    │
│ warning    │ pii_must_be_masked         │ dim_customers      │ open    │
└────────────┴────────────────────────────┴────────────────────┴─────────┘
```

---

### `dab conformance-rules` - List Rules

View available conformance rules:

```bash
# List all rules
dab conformance-rules

# Filter by rule set
dab conformance-rules --rule-set medallion

# Filter by category
dab conformance-rules --category pii
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--rule-set` | `-r` | Filter by rule set |
| `--category` | `-c` | Filter by category |

**Example Output:**
```
Conformance Rules (25 total)
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Rule ID        ┃ Name                        ┃ Severity ┃ Category         ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ MEDAL_001      │ Gold must source from Silver│ error    │ architecture     │
│ MEDAL_002      │ Bronze from external only   │ warning  │ architecture     │
│ DBT_001        │ Model description required  │ warning  │ documentation    │
│ DBT_002        │ Staging prefix required     │ error    │ naming           │
│ PII_001        │ PII must be documented      │ warning  │ pii              │
│ PII_002        │ PII masked in gold          │ critical │ pii              │
└────────────────┴─────────────────────────────┴──────────┴──────────────────┘
```

---

### `dab serve` - Start API Server

Start the REST API server:

```bash
# Start with default settings (0.0.0.0:8002)
dab serve

# Custom host and port
dab serve --host 127.0.0.1 --port 8080

# With auto-reload for development
dab serve --reload
```

**Options:**
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--host` | `-h` | Host to bind to | 0.0.0.0 |
| `--port` | `-p` | Port to bind to | 8002 |
| `--reload` | `-r` | Enable auto-reload | false |

---

## REST API Reference

Once the server is running, access the interactive API documentation at:
- **Swagger UI:** http://localhost:8002/api/v1/docs
- **ReDoc:** http://localhost:8002/api/v1/redoc

### Authentication

All API endpoints (except health checks) require authentication via the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8002/api/v1/capsules
```

### Rate Limiting

The API implements rate limiting to ensure fair usage:
- **Default endpoints:** 100 requests/minute
- **Expensive operations:** 10 requests/minute (conformance evaluation)

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1702489200
```

### Health Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/v1/health` | GET | Basic health check | No |
| `/api/v1/health/ready` | GET | Readiness check (includes DB) | No |
| `/api/v1/health/live` | GET | Liveness check | No |

```bash
# Health check
curl http://localhost:8002/api/v1/health
# Response: {"status": "healthy", "version": "0.1.0"}
```

### Ingestion Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ingest/dbt` | POST | Ingest dbt project via file paths |
| `/api/v1/ingest/dbt/upload` | POST | Ingest dbt project via file upload |
| `/api/v1/ingest/status/{job_id}` | GET | Get ingestion job status |
| `/api/v1/ingest/cancel/{job_id}` | POST | Cancel ingestion job |
| `/api/v1/ingest/history` | GET | Get ingestion history |

```bash
# Ingest via file path
curl -X POST "http://localhost:8002/api/v1/ingest/dbt" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"manifest_path": "/path/to/manifest.json", "catalog_path": "/path/to/catalog.json"}'

# Ingest via file upload
curl -X POST "http://localhost:8002/api/v1/ingest/dbt/upload" \
  -H "X-API-Key: your-api-key" \
  -F "manifest=@manifest.json" \
  -F "catalog=@catalog.json"

# Check job status
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/ingest/status/{job_id}"
```

### Capsule Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/capsules` | GET | List capsules with filters |
| `/api/v1/capsules/stats` | GET | Get capsule statistics |
| `/api/v1/capsules/{urn}/detail` | GET | Get capsule details by URN |
| `/api/v1/capsules/{urn}/columns` | GET | Get capsule columns |
| `/api/v1/capsules/{urn}/lineage` | GET | Get capsule lineage |
| `/api/v1/capsules/{urn}/violations` | GET | Get capsule violations |

```bash
# List capsules with filters
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/capsules?layer=gold&limit=10"

# Get capsule details
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/capsules/urn:dab:dbt:model:jaffle_shop.marts:dim_customers/detail"

# Get capsule lineage
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/capsules/urn:dab:dbt:model:jaffle_shop.marts:dim_customers/lineage?direction=upstream&depth=3"
```

### Column Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/columns` | GET | List columns with filters |
| `/api/v1/columns/pii` | GET | List PII columns |
| `/api/v1/columns/stats` | GET | Get column statistics |
| `/api/v1/columns/{urn}` | GET | Get column by URN |
| `/api/v1/columns/{urn}/lineage` | GET | Get column lineage |

```bash
# List PII columns
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/columns/pii?pii_type=email"

# Get column lineage
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/columns/urn:dab:dbt:column:jaffle_shop.marts:dim_customers.email/lineage"
```

### Compliance Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/compliance/pii-inventory` | GET | PII inventory report |
| `/api/v1/compliance/pii-exposure` | GET | PII exposure report |
| `/api/v1/compliance/pii-trace/{column_urn}` | GET | Trace PII lineage for column |

```bash
# Get PII inventory
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/compliance/pii-inventory"

# Check PII exposure in gold layer
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/compliance/pii-exposure?layer=gold"

# Trace PII column lineage
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/compliance/pii-trace/urn:dab:dbt:column:jaffle_shop.marts:dim_customers.email"
```

### Conformance Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/conformance/score` | GET | Get conformance score |
| `/api/v1/conformance/violations` | GET | List violations |
| `/api/v1/conformance/evaluate` | POST | Evaluate conformance (rate limited: 10/min) |
| `/api/v1/conformance/rules` | GET | List available rules |
| `/api/v1/conformance/rules/{rule_id}` | GET | Get rule by ID |
| `/api/v1/conformance/rules/custom` | POST | Create custom rule |
| `/api/v1/conformance/rules/upload` | POST | Upload rules from file |
| `/api/v1/conformance/rules/export` | GET | Export rules to file |
| `/api/v1/conformance/rules/{rule_id}` | DELETE | Delete custom rule |

```bash
# Get conformance score
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/conformance/score"

# List violations
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/conformance/violations?severity=error"

# Evaluate conformance (creates violations)
curl -X POST "http://localhost:8002/api/v1/conformance/evaluate" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"rule_sets": ["medallion", "dbt_best_practices"]}'

# Create custom rule
curl -X POST "http://localhost:8002/api/v1/conformance/rules/custom" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "rule_id": "CUSTOM_001",
    "name": "Custom Naming Rule",
    "description": "All models must start with our prefix",
    "severity": "warning",
    "category": "naming",
    "scope": "capsule",
    "pattern": "^(acme_)",
    "remediation": "Rename model to start with acme_"
  }'
```

### Violation Management Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/violations` | GET | List all violations |
| `/api/v1/violations/summary` | GET | Get violation summary |
| `/api/v1/violations/{violation_id}` | GET | Get violation details |
| `/api/v1/violations/{violation_id}/status` | PATCH | Update violation status |
| `/api/v1/violations/{violation_id}/acknowledge` | POST | Acknowledge violation |
| `/api/v1/violations/{violation_id}/resolve` | POST | Resolve violation |
| `/api/v1/violations/{violation_id}/false-positive` | POST | Mark as false positive |
| `/api/v1/violations/bulk/status` | POST | Bulk update violation status |

```bash
# Get violation summary
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/violations/summary"

# Acknowledge a violation
curl -X POST "http://localhost:8002/api/v1/violations/{id}/acknowledge" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Will fix in next sprint"}'

# Resolve a violation
curl -X POST "http://localhost:8002/api/v1/violations/{id}/resolve" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"resolution": "Fixed naming convention"}'

# Bulk update status
curl -X POST "http://localhost:8002/api/v1/violations/bulk/status" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"violation_ids": ["id1", "id2"], "status": "acknowledged", "reason": "Batch acknowledgement"}'
```

### Domain Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/domains` | GET | List all domains |
| `/api/v1/domains/stats` | GET | Get domain statistics |
| `/api/v1/domains/{name}` | GET | Get domain by name |
| `/api/v1/domains/{name}/capsules` | GET | Get capsules in domain |
| `/api/v1/domains/{name}/children` | GET | Get child domains |

```bash
# List domains
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/domains"

# Get domain capsules
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/domains/marketing/capsules"
```

### Report Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/reports/pii-inventory` | GET | Export PII inventory |
| `/api/v1/reports/conformance` | GET | Export conformance report |
| `/api/v1/reports/capsule-summary` | GET | Export capsule summary |

```bash
# PII Inventory Report (JSON, CSV, or HTML)
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/reports/pii-inventory?format=html" > pii-report.html

# Conformance Report
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/reports/conformance?format=csv" > conformance.csv

# Capsule Summary Report
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/reports/capsule-summary?layer=gold&format=json"
```

---

## Configuration

DAB is configured via environment variables. Create a `.env` file or set them directly:

### Essential Configuration

```bash
# Database (required)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dab

# Authentication (required for production)
AUTH_ENABLED=true
API_KEYS=your-secure-api-key-1,your-secure-api-key-2

# Environment
ENVIRONMENT=production  # or 'development'
```

### Full Configuration Reference

| Variable | Description | Default |
|----------|-------------|---------|
| **Database** |||
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://dab:dab_password@localhost:5433/dab` |
| `DATABASE_POOL_SIZE` | Connection pool size | `5` |
| `DATABASE_MAX_OVERFLOW` | Max overflow connections | `10` |
| **Authentication** |||
| `AUTH_ENABLED` | Enable API key authentication | `true` |
| `API_KEYS` | Comma-separated list of valid API keys | `dev-api-key-change-in-prod` |
| `API_KEY_HEADER` | Header name for API key | `X-API-Key` |
| **Rate Limiting** |||
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` |
| `RATE_LIMIT_DEFAULT` | Default rate limit | `100/minute` |
| `RATE_LIMIT_EXPENSIVE` | Limit for expensive operations | `10/minute` |
| `RATE_LIMIT_STORAGE_URI` | Redis URI for distributed limiting | (in-memory) |
| **Caching** |||
| `CACHE_ENABLED` | Enable response caching | `true` |
| `CACHE_REDIS_URL` | Redis URL for caching | (in-memory) |
| `CACHE_DEFAULT_TTL` | Default cache TTL (seconds) | `300` |
| **Observability** |||
| `METRICS_ENABLED` | Enable Prometheus metrics | `true` |
| `TRACING_ENABLED` | Enable OpenTelemetry tracing | `false` |
| `TRACING_OTLP_ENDPOINT` | OTLP collector endpoint | - |
| **Application** |||
| `LOG_LEVEL` | Logging level | `INFO` |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |
| `MAX_LINEAGE_DEPTH` | Maximum lineage traversal depth | `10` |

---

## Conformance Rules

DAB includes three built-in rule sets:

### 1. Medallion Architecture (`medallion`)

Rules for Medallion (Bronze/Silver/Gold) architecture:
- Gold models must source from Silver
- Bronze should source from external sources only
- Proper layer naming conventions
- No direct bronze-to-gold dependencies

### 2. dbt Best Practices (`dbt_best_practices`)

Rules based on dbt conventions:
- Model naming prefixes (`stg_`, `int_`, `dim_`, `fct_`)
- All models should have descriptions
- Tests on key columns (unique, not_null)
- Source freshness configured

### 3. PII Compliance (`pii_compliance`)

Rules for handling sensitive data:
- PII must not be exposed raw in Gold layer
- PII columns should be documented
- PII transformations should be tracked
- Sensitive data must have access controls

### Custom Rules

Create custom rules via YAML:

```yaml
# custom_rules.yaml
rules:
  - rule_id: ACME_001
    name: "ACME Naming Convention"
    description: "All models must follow ACME naming"
    severity: warning
    category: naming
    scope: capsule
    pattern: "^(acme_|internal_)"
    remediation: "Prefix model name with 'acme_' or 'internal_'"

  - rule_id: ACME_002
    name: "Required Documentation"
    description: "All gold models must have descriptions"
    severity: error
    category: documentation
    scope: capsule
    condition: "layer == 'gold' and description is None"
    remediation: "Add description to model in schema.yml"
```

Upload rules:
```bash
curl -X POST "http://localhost:8002/api/v1/conformance/rules/upload" \
  -H "X-API-Key: your-api-key" \
  -F "rules_file=@custom_rules.yaml"
```

---

## PII Detection

DAB detects PII through multiple methods:

### 1. dbt Meta Tags (Recommended)

Use `meta.pii: true` in your schema.yml:

```yaml
models:
  - name: customers
    columns:
      - name: email
        description: Customer email address
        meta:
          pii: true
          pii_type: email
          sensitivity: high
      - name: phone
        meta:
          pii: true
          pii_type: phone
```

### 2. Pattern Matching

DAB automatically detects PII based on column names:

| Pattern | PII Type |
|---------|----------|
| `email`, `e_mail`, `e-mail` | email |
| `phone`, `telephone`, `mobile`, `cell` | phone |
| `ssn`, `social_security` | ssn |
| `name`, `first_name`, `last_name` | name |
| `address`, `street`, `city`, `zip` | address |
| `dob`, `date_of_birth`, `birth_date` | date_of_birth |
| `credit_card`, `card_number` | credit_card |

### 3. Detection Report

The detection method is tracked for each PII column:
- `tag`: Detected via dbt meta tags
- `pattern`: Detected via pattern matching
- `manual`: Manually tagged via API

---

## URN Format

DAB uses URNs (Uniform Resource Names) to uniquely identify assets:

```
urn:dab:{source}:{type}:{namespace}:{name}
```

### Examples

| Asset Type | URN Format | Example |
|------------|------------|---------|
| Model | `urn:dab:dbt:model:{project}.{schema}:{name}` | `urn:dab:dbt:model:jaffle_shop.marts:dim_customers` |
| Source | `urn:dab:dbt:source:{project}.{schema}:{name}` | `urn:dab:dbt:source:jaffle_shop.raw:customers` |
| Seed | `urn:dab:dbt:seed:{project}.{schema}:{name}` | `urn:dab:dbt:seed:jaffle_shop.seeds:country_codes` |
| Column | `urn:dab:dbt:column:{project}.{schema}:{table}.{column}` | `urn:dab:dbt:column:jaffle_shop.marts:dim_customers.email` |

---

## Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Capsule not found",
    "details": {
      "urn": "urn:dab:dbt:model:example:missing"
    },
    "request_id": "abc-123"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `NOT_FOUND` | 404 | Resource does not exist |
| `VALIDATION_ERROR` | 422 | Invalid request parameters |
| `CONFLICT` | 409 | Resource already exists |
| `DATABASE_ERROR` | 503 | Database operation failed |
| `INGESTION_ERROR` | 500 | Ingestion process failed |
| `RATE_LIMITED` | 429 | Too many requests |
| `UNAUTHORIZED` | 401 | Missing or invalid API key |

---

## Troubleshooting

### Common Issues

**1. Authentication errors (401)**
- Ensure `X-API-Key` header is included in requests
- Verify API key matches one in `API_KEYS` configuration
- Check if `AUTH_ENABLED=true` in production

**2. Rate limit exceeded (429)**
- Wait for `Retry-After` seconds before retrying
- Consider using bulk endpoints for multiple operations
- Contact administrator to increase limits if needed

**3. Ingestion fails with "file not found"**
- Ensure the path to manifest.json is absolute
- Check file permissions
- For Docker, ensure path is accessible in container

**4. No columns showing**
- Include the catalog.json file: `dab ingest dbt --manifest manifest.json --catalog catalog.json`
- Run `dbt docs generate` first to create the catalog

**5. PII not detected**
- Add `meta.pii: true` to your dbt schema.yml
- Check column naming matches patterns (email, phone, etc.)
- Verify `PII_DETECTION_ENABLED=true`

**6. Conformance score seems wrong**
- Review which rule sets are enabled
- Check if your project follows expected conventions
- Run `dab conformance-rules` to see active rules

**7. Reports returning 404**
- Ensure the API server is running on the correct port (default: 8002)
- Check the URL includes `/api/v1/` prefix
- If running via Docker, rebuild container: `docker compose build dab-api && docker compose up -d dab-api`

**8. API returns stale data**
- Clear cache by restarting the server
- For Redis cache, flush the cache database
- Wait for cache TTL to expire (default: 5 minutes)

### Debugging

```bash
# Check server logs
docker compose logs -f dab-api

# Test database connectivity
curl http://localhost:8002/api/v1/health/ready

# Verify authentication
curl -H "X-API-Key: your-key" http://localhost:8002/api/v1/capsules

# Check metrics (if enabled)
curl http://localhost:8002/metrics
```

### Getting Help

- Check the API docs at http://localhost:8002/api/v1/docs
- View server logs for detailed error messages
- Run `dab --help` for CLI options
- File issues at https://github.com/your-org/data-arch-brain/issues
