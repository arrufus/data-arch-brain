# Data Architecture Brain - User Guide

## Overview

Data Architecture Brain (DAB) is a read-only architecture intelligence platform that helps you understand, govern, and optimize your data landscape. It ingests metadata from dbt projects and provides insights into:

- **PII/Sensitive Data Tracking**: Trace sensitive data through your transformation pipelines
- **Architecture Conformance**: Detect anti-patterns and validate against best practices
- **Lineage Analysis**: Understand data flow at model and column level
- **Impact Analysis**: Assess downstream effects of changes

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- A dbt project with `manifest.json` and optionally `catalog.json`

### Starting the Services

```bash
# Start PostgreSQL and the API server via Docker
cd docker
docker compose up -d

# Or run locally
cd backend
source .venv/bin/activate
dab serve
```

The API server runs on port **8002** by default.

### Ingesting Your First dbt Project

```bash
# Ingest from manifest.json
dab ingest dbt --manifest /path/to/your/dbt/target/manifest.json

# Include catalog for column metadata
dab ingest dbt --manifest /path/to/manifest.json --catalog /path/to/catalog.json
```

## CLI Commands

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
| `--layer` | `-l` | Filter by layer | - |
| `--type` | `-t` | Filter by type | - |
| `--search` | `-s` | Search by name | - |
| `--limit` | `-n` | Number of results | 20 |

**Output columns:** Name, Type, Layer, Cols (column count), PII flag, URN

### `dab stats` - Architecture Statistics

Get a summary of your architecture:

```bash
dab stats
```

**Output shows:**
- Total capsules by type (model, source, seed)
- Distribution by layer (bronze, silver, gold)
- Total columns and PII column counts by type

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
| `--type` | `-t` | Filter by PII type | - |
| `--limit` | `-n` | Number of results | 50 |

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

**Output shows:**
- Total PII columns and affected capsules
- Breakdown by PII type (email, name, SSN, etc.)
- Breakdown by architecture layer

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
| `--severity` | `-s` | Filter by severity |

### `dab lineage` - Trace Lineage

View upstream and downstream dependencies:

```bash
# Show lineage for a capsule (both directions)
dab lineage urn:dab:dbt:model:jaffle_shop.staging:stg_customers

# Only upstream dependencies
dab lineage <urn> --direction upstream

# Only downstream dependencies
dab lineage <urn> --direction downstream

# Increase depth
dab lineage <urn> --depth 5
```

**Options:**
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--direction` | `-d` | upstream, downstream, or both | both |
| `--depth` | - | How many levels to traverse | 3 |

### `dab conformance` - Conformance Score

Check architecture conformance:

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
| `--rule-set` | `-r` | Filter by rule set |
| `--category` | `-c` | Filter by category |

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

## API Endpoints

Once the server is running, access the interactive API documentation at:
- **Swagger UI:** http://localhost:8002/api/v1/docs
- **ReDoc:** http://localhost:8002/api/v1/redoc

### Health Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/health/ready` | GET | Readiness check (includes DB) |
| `/api/v1/health/live` | GET | Liveness check |

### Ingestion Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ingest/dbt` | POST | Ingest dbt project via file paths |
| `/api/v1/ingest/dbt/upload` | POST | Ingest dbt project via file upload |
| `/api/v1/ingest/status/{job_id}` | GET | Get ingestion job status |
| `/api/v1/ingest/cancel/{job_id}` | POST | Cancel ingestion job |
| `/api/v1/ingest/history` | GET | Get ingestion history |

### Capsule Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/capsules` | GET | List capsules with filters |
| `/api/v1/capsules/stats` | GET | Get capsule statistics |
| `/api/v1/capsules/{urn}/detail` | GET | Get capsule details by URN |
| `/api/v1/capsules/{urn}/columns` | GET | Get capsule columns |
| `/api/v1/capsules/{urn}/lineage` | GET | Get capsule lineage |
| `/api/v1/capsules/{urn}/violations` | GET | Get capsule violations |

### Column Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/columns` | GET | List columns with filters |
| `/api/v1/columns/pii` | GET | List PII columns |
| `/api/v1/columns/stats` | GET | Get column statistics |
| `/api/v1/columns/{urn}` | GET | Get column by URN |
| `/api/v1/columns/{urn}/lineage` | GET | Get column lineage |

### Compliance Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/compliance/pii-inventory` | GET | PII inventory report |
| `/api/v1/compliance/pii-exposure` | GET | PII exposure report |
| `/api/v1/compliance/pii-trace/{column_urn}` | GET | Trace PII lineage for column |

### Conformance Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/conformance/score` | GET | Get conformance score |
| `/api/v1/conformance/violations` | GET | List violations |
| `/api/v1/conformance/evaluate` | POST | Evaluate conformance |
| `/api/v1/conformance/rules` | GET | List available rules |
| `/api/v1/conformance/rules/{rule_id}` | GET | Get rule by ID |
| `/api/v1/conformance/rules/custom` | POST | Create custom rule |
| `/api/v1/conformance/rules/upload` | POST | Upload rules from file |
| `/api/v1/conformance/rules/export` | GET | Export rules to file |
| `/api/v1/conformance/rules/{rule_id}` | DELETE | Delete custom rule |

### Domain Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/domains` | GET | List all domains |
| `/api/v1/domains/stats` | GET | Get domain statistics |
| `/api/v1/domains/{name}` | GET | Get domain by name |
| `/api/v1/domains/{name}/capsules` | GET | Get capsules in domain |
| `/api/v1/domains/{name}/children` | GET | Get child domains |

### Report Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/reports/pii-inventory` | GET | Export PII inventory |
| `/api/v1/reports/conformance` | GET | Export conformance report |
| `/api/v1/reports/capsule-summary` | GET | Export capsule summary |

## Reports

Generate downloadable reports in JSON, CSV, or HTML formats.

### PII Inventory Report

```bash
# JSON format (default)
curl "http://localhost:8002/api/v1/reports/pii-inventory"

# CSV format
curl "http://localhost:8002/api/v1/reports/pii-inventory?format=csv"

# HTML format
curl "http://localhost:8002/api/v1/reports/pii-inventory?format=html"

# Filter by PII type
curl "http://localhost:8002/api/v1/reports/pii-inventory?pii_type=email"

# Filter by layer
curl "http://localhost:8002/api/v1/reports/pii-inventory?layer=gold"
```

**Query parameters:**
| Parameter | Description |
|-----------|-------------|
| `format` | Output format: json, csv, html (default: json) |
| `pii_type` | Filter by PII type |
| `layer` | Filter by layer |

### Conformance Report

```bash
# JSON format (default)
curl "http://localhost:8002/api/v1/reports/conformance"

# CSV format
curl "http://localhost:8002/api/v1/reports/conformance?format=csv"

# HTML format
curl "http://localhost:8002/api/v1/reports/conformance?format=html"

# Filter by rule set
curl "http://localhost:8002/api/v1/reports/conformance?rule_set=medallion"

# Filter by severity
curl "http://localhost:8002/api/v1/reports/conformance?severity=error"
```

**Query parameters:**
| Parameter | Description |
|-----------|-------------|
| `format` | Output format: json, csv, html (default: json) |
| `rule_set` | Filter by rule set |
| `severity` | Filter by severity |

### Capsule Summary Report

```bash
# JSON format (default)
curl "http://localhost:8002/api/v1/reports/capsule-summary"

# CSV format
curl "http://localhost:8002/api/v1/reports/capsule-summary?format=csv"

# Filter by layer
curl "http://localhost:8002/api/v1/reports/capsule-summary?layer=gold"

# Filter by type
curl "http://localhost:8002/api/v1/reports/capsule-summary?capsule_type=model"
```

**Query parameters:**
| Parameter | Description |
|-----------|-------------|
| `format` | Output format: json, csv (default: json) |
| `layer` | Filter by layer |
| `capsule_type` | Filter by capsule type |

## Conformance Rules

DAB includes three built-in rule sets:

### 1. Medallion Architecture

Rules for Medallion (Bronze/Silver/Gold) architecture:
- Gold models must source from Silver
- Bronze should source from external sources only
- Proper layer naming conventions

### 2. dbt Best Practices

Rules based on dbt conventions:
- Model naming prefixes (stg_, dim_, fct_)
- All models should have descriptions
- Tests on key columns

### 3. PII Compliance

Rules for handling sensitive data:
- PII must not be exposed raw in Gold layer
- PII columns should be documented
- PII transformations should be tracked

### Adding Custom Rules

Create custom rules via the API:

```bash
# Create a custom rule
curl -X POST "http://localhost:8002/api/v1/conformance/rules/custom" \
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

# Or upload from a YAML file
curl -X POST "http://localhost:8002/api/v1/conformance/rules/upload" \
  -F "rules_file=@custom_rules.yaml"
```

## PII Detection

DAB detects PII through multiple methods:

1. **dbt Meta Tags**: Use `meta.pii: true` in your schema.yml
2. **Pattern Matching**: Column names like `email`, `ssn`, `phone`
3. **Manual Tagging**: Tag columns via API

Example dbt schema.yml:
```yaml
models:
  - name: customers
    columns:
      - name: email
        meta:
          pii: true
          pii_type: email
          sensitivity: high
```

## URN Format

DAB uses URNs (Uniform Resource Names) to identify assets:

```
urn:dab:{source}:{type}:{namespace}:{name}
```

Examples:
- `urn:dab:dbt:model:jaffle_shop.staging:stg_customers`
- `urn:dab:dbt:source:jaffle_shop.raw:customers`
- `urn:dab:dbt:column:jaffle_shop.staging:stg_customers.email`

## Error Handling

The API returns standardized error responses:

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

**Common error codes:**
| Code | Description |
|------|-------------|
| `NOT_FOUND` | Resource does not exist |
| `VALIDATION_ERROR` | Invalid request parameters |
| `CONFLICT` | Resource already exists |
| `DATABASE_ERROR` | Database operation failed |
| `INGESTION_ERROR` | Ingestion process failed |

## Troubleshooting

### Common Issues

**1. Ingestion fails with "file not found"**
- Ensure the path to manifest.json is absolute or relative to current directory
- Check file permissions

**2. No columns showing**
- Include the catalog.json file: `dab ingest dbt --manifest manifest.json --catalog catalog.json`
- Run `dbt docs generate` first to create the catalog

**3. PII not detected**
- Add `meta.pii: true` to your dbt schema.yml
- Check column naming (email, phone, etc.)

**4. Conformance score seems wrong**
- Review which rule sets are enabled
- Check if your project follows expected conventions

**5. Reports returning 404**
- Ensure the API server is running on the correct port (default: 8002)
- Check the URL includes `/api/v1/` prefix
- If running via Docker, rebuild container after code changes: `docker compose build dab-api && docker compose up -d dab-api`

**6. API returns stale data after code changes**
- When running via Docker, the container must be rebuilt to pick up code changes
- Run: `cd docker && docker compose build dab-api && docker compose up -d dab-api`

### Getting Help

- Check the API docs at http://localhost:8002/api/v1/docs
- View server logs for detailed error messages
- Run `dab --help` for CLI options
