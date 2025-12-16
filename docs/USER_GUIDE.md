# Data Architecture Brain - User Guide

## Overview

Data Architecture Brain (DAB) is a read-only architecture intelligence platform that helps you understand, govern, and optimize your data landscape. It ingests metadata from dbt projects and Airflow orchestration platforms and provides insights into:

- **PII/Sensitive Data Tracking**: Trace sensitive data through your transformation pipelines
- **Architecture Conformance**: Detect anti-patterns and validate against best practices
- **Lineage Analysis**: Understand data flow at model, column, and orchestration level
- **Impact Analysis**: Assess downstream effects of changes
- **Redundancy Detection**: Identify duplicate and similar data assets
- **Violation Management**: Track and resolve conformance violations
- **Orchestration Visibility**: Map DAG workflows and task dependencies from Airflow
- **Web Dashboard**: Modern React UI with 10+ pages for visual exploration

## Quick Start

### Web Dashboard Access

Access the web dashboard to visually explore your data architecture:

```bash
# Start all services (backend + frontend)
docker compose up -d

# Access the dashboard
open http://localhost:3000
```

**Dashboard Pages:**
- **`/capsules`** - Data Capsule Browser with search and filtering
- **`/capsules/[urn]`** - Detailed capsule view with lineage visualization
- **`/lineage`** - Interactive lineage graph (React Flow)
- **`/compliance`** - PII Compliance Dashboard (inventory, exposure, trace)
- **`/conformance`** - Architecture Conformance Scoring
- **`/impact`** - Impact Analysis for assessing downstream effects
- **`/redundancy`** - Redundancy Detection (find similar capsules)
- **`/domains`** - Business domain browser
- **`/products`** - Data Products with SLO tracking
- **`/tags`** - Tag management and exploration
- **`/settings`** - Configuration management
- **`/reports`** - Generate and download reports

### CLI and API Access

### Prerequisites

- Docker and Docker Compose installed
- A dbt project with `manifest.json` and optionally `catalog.json` (for dbt ingestion)
- Access to an Airflow REST API (for Airflow ingestion)

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

### Ingesting Your First Airflow Instance

```bash
# No authentication (for local/dev instances)
dab ingest airflow --base-url http://localhost:8080

# With bearer token authentication (recommended for production)
export AIRFLOW_TOKEN=your-token-here
dab ingest airflow \
  --base-url https://airflow.example.com \
  --auth-mode bearer_env

# With DAG filtering
dab ingest airflow \
  --base-url https://airflow.example.com \
  --auth-mode bearer_env \
  --dag-regex "customer_.*"
```

---

## CLI Commands Reference

### `dab ingest` - Ingest Metadata

Ingest metadata from dbt projects or Airflow instances:

#### dbt Ingestion

```bash
# With catalog for column info
dab ingest dbt --manifest /path/to/manifest.json --catalog /path/to/catalog.json

# With project name override
dab ingest dbt --manifest /path/to/manifest.json --project my_project
```

**dbt Options:**
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

#### Airflow Ingestion

```bash
# No authentication
dab ingest airflow --base-url https://airflow.example.com

# With bearer token
export AIRFLOW_TOKEN=your-token
dab ingest airflow --base-url https://airflow.example.com --auth-mode bearer_env

# With basic auth
export AIRFLOW_USERNAME=admin
export AIRFLOW_PASSWORD=password
dab ingest airflow --base-url https://airflow.example.com --auth-mode basic_env

# With DAG filtering
dab ingest airflow \
  --base-url https://airflow.example.com \
  --dag-regex "customer_.*" \
  --include-paused

# Full configuration
dab ingest airflow \
  --base-url https://airflow.example.com \
  --instance prod-airflow \
  --auth-mode bearer_env \
  --dag-allowlist dag1,dag2,dag3 \
  --page-limit 50 \
  --timeout 60.0 \
  --cleanup-orphans
```

**Airflow Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--base-url` | `-u` | Airflow REST API base URL (required) |
| `--instance` | `-i` | Instance name for URN namespace |
| `--auth-mode` | `-a` | Authentication: none, bearer_env, basic_env |
| `--token-env` | | Environment variable name for bearer token |
| `--username-env` | | Environment variable name for username |
| `--password-env` | | Environment variable name for password |
| `--dag-regex` | `-r` | Regex pattern to filter DAGs |
| `--dag-allowlist` | | Comma-separated DAG IDs to include |
| `--dag-denylist` | | Comma-separated DAG IDs to exclude |
| `--include-paused` | | Include paused DAGs |
| `--include-inactive` | | Include inactive DAGs |
| `--page-limit` | | API pagination size (default: 100) |
| `--timeout` | `-t` | HTTP timeout in seconds (default: 30) |
| `--cleanup-orphans` | | Remove stale capsules from previous ingestions |

**Example Output:**
```
Ingesting Airflow metadata...
✓ Connected to Airflow 2.7.0
✓ Found 23 DAGs
✓ Parsed 156 tasks
✓ Created 312 edges (223 contains + 89 flows_to)
Ingestion completed in 4.1s
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

### `dab redundancy` - Redundancy Detection

Identify duplicate and overlapping data assets to reduce waste and consolidate redundant models.

#### Find Similar Capsules

Find data assets similar to a given capsule:

```bash
# Find similar capsules with default threshold (0.5)
dab redundancy find "urn:dab:dbt:model:staging:stg_customers"

# With custom threshold (higher = more strict)
dab redundancy find "urn:dab:dbt:model:staging:stg_customers" --threshold 0.75

# Limit results
dab redundancy find "urn:dab:dbt:model:staging:stg_customers" --limit 5

# JSON output
dab redundancy find "urn:dab:dbt:model:staging:stg_customers" --format json
```

**Options:**
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--threshold` | `-t` | Minimum similarity score (0.0-1.0) | 0.5 |
| `--limit` | `-l` | Maximum results to return | 10 |
| `--format` | `-f` | Output format: table, json | table |

**Example Output:**
```
Similar Capsules for stg_customers
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Capsule Name              ┃ Score   ┃ Layer  ┃ Confidence   ┃ Type            ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ stg_customers_v2          │ 0.84    │ silver │ high         │ model           │
│ staging_customers         │ 0.72    │ silver │ medium       │ model           │
│ int_customers             │ 0.58    │ silver │ medium       │ model           │
└───────────────────────────┴─────────┴────────┴──────────────┴─────────────────┘

Top Match Reasons:
  • Very similar names: 'stg_customers' vs 'stg_customers_v2'
  • High schema overlap: 90% of columns match
  • Same domain: customer
```

#### Compare Two Capsules

Compare two specific capsules to assess similarity:

```bash
# Compare two capsules
dab redundancy compare \
  "urn:dab:dbt:model:staging:stg_customers" \
  "urn:dab:dbt:model:staging:staging_customers"
```

**Example Output:**
```
Comparison: stg_customers vs staging_customers
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Similarity Breakdown
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┓
┃ Component            ┃ Score   ┃ Weight  ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━┩
│ Name Similarity      │ 0.88    │ 30%     │
│ Schema Similarity    │ 0.92    │ 35%     │
│ Lineage Similarity   │ 0.85    │ 25%     │
│ Metadata Similarity  │ 0.70    │ 10%     │
├──────────────────────┼─────────┼─────────┤
│ Combined Score       │ 0.86    │ 100%    │
└──────────────────────┴─────────┴─────────┘

Confidence: high

Recommendation: Likely Duplicates

These capsules appear to be duplicates or overlapping implementations.
Consider consolidating them to reduce redundancy.

Reasons:
  • Very similar names
  • High schema overlap: 92% of columns match
  • Shared upstream sources: raw_customers
  • Same layer: silver
```

#### List Duplicate Candidates

Find high-confidence duplicate pairs across your data landscape:

```bash
# List all duplicate candidates (threshold 0.75)
dab redundancy candidates

# With custom threshold
dab redundancy candidates --threshold 0.8

# Filter by layer
dab redundancy candidates --layer gold

# Filter by capsule type
dab redundancy candidates --capsule-type model
```

**Options:**
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--threshold` | `-t` | Minimum similarity score (0.5-1.0) | 0.75 |
| `--layer` | `-l` | Filter by layer | - |
| `--capsule-type` | `-c` | Filter by capsule type | - |

**Example Output:**
```
Duplicate Candidates (threshold: 0.75)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┓
┃ Capsule 1           ┃ Capsule 2           ┃ Score   ┃ Layer1 ┃ Layer2 ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━━┩
│ stg_customers       │ staging_customers   │ 0.88    │ silver │ silver │
│ dim_customer        │ dim_customers       │ 0.82    │ gold   │ gold   │
│ int_orders_daily    │ daily_orders        │ 0.76    │ silver │ silver │
└─────────────────────┴─────────────────────┴─────────┴────────┴────────┘

Found 3 high-confidence duplicate pairs
Potential for consolidation and cost savings
```

#### Generate Redundancy Report

Generate a comprehensive redundancy report:

```bash
# Table format (default)
dab redundancy report

# JSON format for processing
dab redundancy report --format json > redundancy-report.json
```

**Options:**
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--format` | `-f` | Output format: table, json | table |

**Example Output:**
```
Redundancy Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Summary:
  Total Capsules:        150
  Duplicate Pairs:       12

Duplicates by Layer:
  silver:    8 pairs
  gold:      4 pairs

Duplicates by Type:
  model:     10 pairs
  source:    2 pairs

Savings Estimate:
  Storage reduction:     ~120%
  Compute reduction:     ~180%
  Models to review:      24

Top 10 Duplicate Candidates:
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Capsule 1           ┃ Capsule 2           ┃ Score   ┃ Reasons                      ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ stg_customers       │ staging_customers   │ 0.88    │ Very similar names, 88% sc...│
│ dim_customer        │ dim_customers       │ 0.82    │ Very similar names, High s...│
└─────────────────────┴─────────────────────┴─────────┴──────────────────────────────┘
```

---

## Web Dashboard Guide

The Data Architecture Brain includes a modern React web dashboard for visual exploration of your data architecture. The dashboard provides an intuitive interface to all platform features.

### Accessing the Dashboard

```bash
# Start all services
docker compose up -d

# Access at http://localhost:3000
```

### Dashboard Navigation

The dashboard includes a sidebar with the following pages:

#### **Home** (`/`)
- Overview dashboard with summary statistics
- Quick access to recent capsules and violations
- Navigation cards to main features

#### **Capsules** (`/capsules`)
- Browse all data capsules (models, sources, seeds, DAGs, tasks)
- **Search**: Full-text search across capsule names
- **Filters**: Layer (bronze/silver/gold), Type (model/source/seed), Domain, Has PII
- **Pagination**: Navigate large datasets
- **Sort**: By name, updated date, column count
- Click any capsule to view details

#### **Capsule Detail** (`/capsules/[urn]`)
- **Overview Tab**: Metadata, owner, source system, statistics
- **Columns Tab**: List of columns with PII indicators, filterable by PII type
- **Lineage Tab**: Upstream sources and downstream dependents (interactive graph or list view)
- **Violations Tab**: Conformance violations for this capsule, filterable by severity

#### **Lineage** (`/lineage`)
- **Interactive Graph**: React Flow-based lineage visualization
- **Type-Ahead Search**: Find capsules quickly with dropdown
- **Direction Control**: View upstream, downstream, or both
- **Depth Control**: Configure traversal depth (1-10 levels)
- **Node Interactions**: Click nodes to navigate to capsule detail
- **Deep Linking**: Share specific lineage views via URL

#### **Compliance** (`/compliance`)
- **PII Inventory Tab**:
  - Summary statistics (total PII columns, affected capsules)
  - Breakdown by PII type (email, phone, SSN, etc.)
  - Breakdown by layer (bronze, silver, gold)
  - Export to CSV
  - Bar charts for visualization
- **PII Exposure Tab**:
  - List of unmasked PII in consumption layers (gold/marts)
  - Severity indicators (critical, high, medium)
  - Recommendations for masking
  - Lineage path showing propagation
- **PII Trace Tab**:
  - Search by column URN
  - Display trace results: origin, propagation path, terminals
  - Masking status at terminals
  - Visual flow diagram

#### **Conformance** (`/conformance`)
- **Overview Tab**:
  - Real-time conformance score
  - Breakdown by severity (critical, error, warning, info)
  - Breakdown by category (naming, lineage, PII, documentation, testing)
  - Auto-refresh every 5 minutes
  - Manual refresh button
- **Violations Tab**:
  - List all violations with filtering
  - Filter by severity, category, status
  - Drill down to specific capsules
  - Resolve or acknowledge violations
- **Rules Tab**:
  - View active conformance rules
  - Upload custom rules (YAML)
  - Export rules
  - Filter by rule set, category

#### **Impact** (`/impact`)
- **Capsule Selection**: Type-ahead dropdown to select target capsule
- **Depth Configuration**: Set traversal depth (1-10 levels)
- **Impact Summary**:
  - Total affected capsules
  - High-impact warnings for production systems
  - Breakdown by layer
- **Affected Capsules List**:
  - Grouped by propagation depth
  - Type and layer indicators
  - Direct navigation to capsule details

#### **Redundancy** (`/redundancy`)
- **Report Tab**:
  - Summary of duplicate candidates
  - Breakdown by layer and type
  - Savings estimates (storage, compute)
  - Top 10 duplicate pairs with similarity scores
- **Finder Tab**:
  - Search for similar capsules
  - Configure similarity threshold (0.5-1.0)
  - Same-type-only filter
  - Results with similarity breakdown (name, schema, lineage, metadata)
  - Human-readable similarity reasons

#### **Domains** (`/domains`)
- **Master-Detail Layout**:
  - Left: List of all domains with search
  - Right: Domain details with capsule list
- **Domain Details**:
  - Description, parent domain
  - Statistics (capsule count)
  - List of capsules in domain
  - Navigation to capsule details

#### **Data Products** (`/products`)
- **Master-Detail Layout**:
  - Left: List of all data products
  - Right: Product details with SLO status
- **Product Details**:
  - Version, status (draft/active/deprecated)
  - SLO configuration (freshness, availability, quality)
  - SLO compliance status
  - List of capsules (PART_OF relationships)
  - Tags associated with product
- **CRUD Operations**: Create, update, delete data products

#### **Tags** (`/tags`)
- **Master-Detail Layout**:
  - Left: List of tags with category filter
  - Right: Tag details
- **Tag Details**:
  - Category, sensitivity level, color
  - List of tagged capsules
  - List of tagged columns
  - Navigation to capsule/column details
- **Tag Management**: Create, update, delete tags

#### **Settings** (`/settings`)
- **Domains Tab**: Browse and manage business domains
- **Tags Tab**: Full CRUD for tags with color picker, sensitivity levels
- **Products Tab**: Manage data products
- **Rules Tab**: Upload/export custom conformance rules
- **System Info Tab**: View system configuration and health

#### **Reports** (`/reports`)
- **Report Types**:
  - PII Inventory Report
  - Conformance Report
  - Capsule Summary Report
- **Format Selection**: JSON, CSV, HTML
- **Filter Options**: Layer, type, severity
- **Generate & Download**: Trigger report generation and download

### Dashboard Features

#### Search & Filters
- All list views support search and filtering
- Filters persist across navigation
- Clear filters button resets to defaults

#### Navigation
- Breadcrumbs for context
- Back button support
- Deep linking (shareable URLs)
- Sidebar always visible with active page highlight

#### Real-Time Updates
- Auto-refresh for conformance score (5 minutes)
- Manual refresh buttons where applicable
- Loading states with spinners

#### Responsive Design
- Mobile-friendly layouts
- Tablet and desktop optimized
- Scrollable tables for large datasets

#### Error Handling
- User-friendly error messages
- Retry mechanisms for failed requests
- Graceful degradation

### Dashboard Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `/` | Focus search input |
| `Esc` | Close modals/dialogs |
| `Ctrl+K` | Quick command palette (future) |

### Dashboard Tips

1. **Bookmarking**: Bookmark frequently accessed capsules - URLs are stable
2. **Filters**: Use layer filters to focus on specific architecture layers
3. **Lineage**: Start with depth=3 for balanced performance and visibility
4. **PII Trace**: Use column URNs from capsule detail view
5. **Reports**: Generate reports during off-peak hours for large datasets
6. **Settings**: Regularly review and update tags for better organization

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
| `/api/v1/ingest/airflow` | POST | Ingest Airflow DAG and task metadata |
| `/api/v1/ingest/status/{job_id}` | GET | Get ingestion job status |
| `/api/v1/ingest/cancel/{job_id}` | POST | Cancel ingestion job |
| `/api/v1/ingest/history` | GET | Get ingestion history |

```bash
# Ingest dbt via file path
curl -X POST "http://localhost:8002/api/v1/ingest/dbt" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"manifest_path": "/path/to/manifest.json", "catalog_path": "/path/to/catalog.json"}'

# Ingest dbt via file upload
curl -X POST "http://localhost:8002/api/v1/ingest/dbt/upload" \
  -H "X-API-Key: your-api-key" \
  -F "manifest=@manifest.json" \
  -F "catalog=@catalog.json"

# Ingest Airflow (no auth)
curl -X POST "http://localhost:8002/api/v1/ingest/airflow" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "https://airflow.example.com"
  }'

# Ingest Airflow with authentication and filtering
curl -X POST "http://localhost:8002/api/v1/ingest/airflow" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "https://airflow.example.com",
    "instance_name": "prod-airflow",
    "auth_mode": "bearer_env",
    "token_env": "AIRFLOW_TOKEN",
    "dag_id_regex": "customer_.*",
    "include_paused": false,
    "cleanup_orphans": true
  }'

# Check job status
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/ingest/status/{job_id}"

# List ingestion history (all sources)
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/ingest/history?limit=20"

# Filter history by source type
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/ingest/history?source_type=airflow"
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

### Data Product Endpoints

Data Products allow you to group capsules into logical units with SLO tracking (Data Mesh pattern).

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/products` | GET | List all data products |
| `/api/v1/products` | POST | Create a new data product |
| `/api/v1/products/{id}` | GET | Get data product details |
| `/api/v1/products/{id}` | PUT | Update data product |
| `/api/v1/products/{id}` | DELETE | Delete data product |
| `/api/v1/products/{id}/capsules` | GET | List capsules in data product |
| `/api/v1/products/{id}/capsules/{capsule_id}` | POST | Add capsule to data product |
| `/api/v1/products/{id}/capsules/{capsule_id}` | DELETE | Remove capsule from data product |
| `/api/v1/products/{id}/slo-status` | GET | Get SLO compliance status |

```bash
# List all data products
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/products"

# Create a data product
curl -X POST "http://localhost:8002/api/v1/products" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Analytics",
    "description": "Customer data product for marketing analytics",
    "domain_id": "uuid-of-domain",
    "slo_freshness_hours": 24,
    "slo_availability_percent": 99.9,
    "slo_quality_threshold": 0.95
  }'

# Add a capsule to a data product (PART_OF edge)
curl -X POST "http://localhost:8002/api/v1/products/{product_id}/capsules/{capsule_id}" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"role": "output"}'

# Check SLO status
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/products/{product_id}/slo-status"
# Response: {"freshness_met": true, "availability_met": true, "quality_met": false, "overall_status": "degraded"}
```

### Tag Management Endpoints

Tags can be applied to capsules and columns as graph edges (TAGGED_WITH relationship).

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/tags` | GET | List all tags |
| `/api/v1/tags` | POST | Create a new tag |
| `/api/v1/tags/{id}` | GET | Get tag details |
| `/api/v1/tags/{id}` | PUT | Update tag |
| `/api/v1/tags/{id}` | DELETE | Delete tag |
| `/api/v1/tags/capsules/{capsule_id}` | GET | Get tags for a capsule |
| `/api/v1/tags/capsules/{capsule_id}/{tag_id}` | POST | Add tag to capsule |
| `/api/v1/tags/capsules/{capsule_id}/{tag_id}` | DELETE | Remove tag from capsule |
| `/api/v1/tags/columns/{column_id}` | GET | Get tags for a column |
| `/api/v1/tags/columns/{column_id}/{tag_id}` | POST | Add tag to column |
| `/api/v1/tags/columns/{column_id}/{tag_id}` | DELETE | Remove tag from column |
| `/api/v1/tags/{tag_id}/capsules` | GET | Get all capsules with a tag |
| `/api/v1/tags/{tag_id}/columns` | GET | Get all columns with a tag |

```bash
# Create a tag
curl -X POST "http://localhost:8002/api/v1/tags" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "pii",
    "category": "compliance",
    "description": "Contains personally identifiable information",
    "color": "#FF0000",
    "sensitivity_level": "high"
  }'

# Tag a capsule
curl -X POST "http://localhost:8002/api/v1/tags/capsules/{capsule_id}/{tag_id}" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"added_by": "john.doe@company.com"}'

# Find all capsules with a specific tag
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/tags/{tag_id}/capsules"

# Get tags for a column
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/tags/columns/{column_id}"
```

### Graph Export Endpoints

Export the property graph in various formats for visualization and integration with external tools.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/graph/formats` | GET | List available export formats |
| `/api/v1/graph/export` | GET | Export full property graph |
| `/api/v1/graph/export/lineage/{urn}` | GET | Export lineage subgraph for a capsule |

**Supported Export Formats:**

| Format | Content-Type | Use Cases |
|--------|-------------|-----------|
| `graphml` | `application/xml` | yEd, Gephi, Cytoscape, NetworkX |
| `dot` | `text/plain` | Graphviz (dot, neato, fdp), VSCode extensions |
| `cypher` | `text/plain` | Neo4j, Amazon Neptune, Memgraph |
| `mermaid` | `text/plain` | GitHub, GitLab, Notion, Obsidian |
| `json-ld` | `application/ld+json` | Semantic web, Apache Jena, RDF tools |

```bash
# List available formats
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/graph/formats"

# Export full graph in Mermaid format (default)
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/graph/export" > graph.mmd

# Export in GraphML for Gephi/yEd
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/graph/export?format=graphml" > graph.graphml

# Export with additional nodes (columns, tags, data products)
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/graph/export?format=dot&include_columns=true&include_tags=true&include_data_products=true" > full_graph.dot

# Export only a specific domain
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/graph/export?format=mermaid&domain_id={domain_id}" > domain_graph.mmd

# Export lineage subgraph for a specific capsule
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/graph/export/lineage/urn:dab:dbt:model:jaffle_shop.marts:dim_customers?format=mermaid&depth=3" > lineage.mmd

# Export upstream lineage only (where data comes from)
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/graph/export/lineage/urn:dab:dbt:model:project:orders?format=dot&direction=upstream&depth=5" > upstream.dot

# Export for Neo4j import
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/graph/export?format=cypher" > import.cypher

# Then in Neo4j:
# cat import.cypher | cypher-shell -u neo4j -p password
```

### Redundancy Detection Endpoints

Identify duplicate and overlapping data assets using multi-algorithm similarity scoring.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/redundancy/capsules/{urn}/similar` | GET | Find capsules similar to the given URN |
| `/api/v1/redundancy/capsules/{urn}/similar/{other_urn}` | GET | Compare two specific capsules |
| `/api/v1/redundancy/candidates` | GET | Get high-confidence duplicate candidates |
| `/api/v1/redundancy/report` | GET | Get comprehensive redundancy report |

**Similarity Algorithms:**

Redundancy detection uses 4 weighted algorithms:
- **Name Similarity (30%)**: Fuzzy string matching using Ratcliff/Obershelp
- **Schema Similarity (35%)**: Jaccard index on column names/types
- **Lineage Similarity (25%)**: Jaccard index on upstream dependencies
- **Metadata Similarity (10%)**: Domain, layer, tags, description comparison

**Similarity Thresholds:**
- **High (≥0.75)**: Likely duplicates - consolidation recommended
- **Medium (0.50-0.74)**: Potential overlap - manual review suggested
- **Low (<0.50)**: Distinct assets - not redundant

```bash
# Find similar capsules
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/redundancy/capsules/urn:dab:dbt:model:staging:stg_customers/similar?threshold=0.5&limit=10"

# Response:
{
  "target_urn": "urn:dab:dbt:model:staging:stg_customers",
  "target_name": "stg_customers",
  "threshold": 0.5,
  "results_count": 2,
  "results": [
    {
      "capsule_id": "uuid-123",
      "capsule_urn": "urn:dab:dbt:model:staging:stg_customers_v2",
      "capsule_name": "stg_customers_v2",
      "capsule_type": "model",
      "layer": "silver",
      "domain_name": "customer",
      "similarity": {
        "name_score": 0.85,
        "schema_score": 0.90,
        "lineage_score": 0.75,
        "metadata_score": 0.80,
        "combined_score": 0.84,
        "confidence": "high"
      },
      "reasons": [
        "Very similar names: 'stg_customers' vs 'stg_customers_v2'",
        "High schema overlap: 90% of columns match",
        "Same domain: customer"
      ]
    }
  ]
}

# Compare two capsules
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/redundancy/capsules/urn:dab:dbt:model:staging:stg_customers/similar/urn:dab:dbt:model:staging:staging_customers"

# Response:
{
  "capsule1": {
    "capsule_urn": "urn:dab:dbt:model:staging:stg_customers",
    "capsule_name": "stg_customers",
    "similarity": { ... }
  },
  "capsule2": {
    "capsule_urn": "urn:dab:dbt:model:staging:staging_customers",
    "capsule_name": "staging_customers",
    "similarity": { ... }
  },
  "recommendation": "likely_duplicates",
  "explanation": "Combined similarity score of 0.86 indicates these are likely duplicates..."
}

# Get duplicate candidates (high confidence)
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/redundancy/candidates?threshold=0.75&layer=gold"

# Response:
{
  "threshold": 0.75,
  "layer": "gold",
  "candidates_count": 3,
  "candidates": [
    {
      "capsule1_urn": "urn:dab:dbt:model:marts:dim_customer",
      "capsule1_name": "dim_customer",
      "capsule1_layer": "gold",
      "capsule2_urn": "urn:dab:dbt:model:marts:dim_customers",
      "capsule2_name": "dim_customers",
      "capsule2_layer": "gold",
      "similarity_score": 0.82,
      "reasons": [
        "Very similar names",
        "High schema overlap: 95% of columns match"
      ]
    }
  ]
}

# Get redundancy report
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/redundancy/report"

# Response:
{
  "total_capsules": 150,
  "duplicate_pairs": 12,
  "potential_duplicates": [...],
  "by_layer": {
    "silver": 8,
    "gold": 4
  },
  "by_type": {
    "model": 10,
    "source": 2
  },
  "savings_estimate": {
    "potential_storage_reduction": "120%",
    "potential_compute_reduction": "180%",
    "models_to_review": 24
  }
}
```

**Query Parameters for `/redundancy/capsules/{urn}/similar`:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `threshold` | float | Minimum similarity score (0.0-1.0) | 0.5 |
| `limit` | int | Maximum results (1-100) | 10 |
| `same_type_only` | bool | Only compare same capsule type | true |
| `same_layer_only` | bool | Only compare same layer | false |

**Query Parameters for `/redundancy/candidates`:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `threshold` | float | Minimum similarity score (0.5-1.0) | 0.75 |
| `layer` | string | Filter by layer (bronze, silver, gold) | - |
| `capsule_type` | string | Filter by type (model, source, seed) | - |

---

**Graph Export Options:**

| Parameter | Description | Default |
|-----------|-------------|---------|
| `format` | Export format (graphml, dot, cypher, mermaid, json-ld) | `mermaid` |
| `domain_id` | Filter to specific domain | - |
| `include_columns` | Include column nodes and CONTAINS edges | `false` |
| `include_tags` | Include tag nodes and TAGGED_WITH edges | `false` |
| `include_data_products` | Include data product nodes and PART_OF edges | `false` |

**Lineage Export Options:**

| Parameter | Description | Default |
|-----------|-------------|---------|
| `format` | Export format | `mermaid` |
| `depth` | Number of hops to traverse (1-10) | `3` |
| `direction` | Direction: upstream, downstream, or both | `both` |
| `include_columns` | Include column-level lineage | `false` |

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
| dbt Model | `urn:dab:dbt:model:{project}.{schema}:{name}` | `urn:dab:dbt:model:jaffle_shop.marts:dim_customers` |
| dbt Source | `urn:dab:dbt:source:{project}.{schema}:{name}` | `urn:dab:dbt:source:jaffle_shop.raw:customers` |
| dbt Seed | `urn:dab:dbt:seed:{project}.{schema}:{name}` | `urn:dab:dbt:seed:jaffle_shop.seeds:country_codes` |
| dbt Column | `urn:dab:dbt:column:{project}.{schema}:{table}.{column}` | `urn:dab:dbt:column:jaffle_shop.marts:dim_customers.email` |
| Airflow DAG | `urn:dab:airflow:dag:{instance}:{dag_id}` | `urn:dab:airflow:dag:prod-airflow:customer_daily_pipeline` |
| Airflow Task | `urn:dab:airflow:task:{instance}:{dag_id}.{task_id}` | `urn:dab:airflow:task:prod-airflow:customer_daily_pipeline.extract_data` |

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

---

## Resetting the Application

If you need to clear all data and start fresh, you can reset the application to remove all capsules, lineage, and property graph information.

### Full Reset

To remove all ingested data while preserving the database schema:

```bash
# Connect to PostgreSQL and clear all tables
# For Docker deployments:
docker compose exec postgres psql -U dab -d dab -c "
TRUNCATE TABLE
    lineage_edges,
    column_lineage_edges,
    conformance_violations,
    capsule_tags,
    column_tags,
    data_product_capsules,
    columns,
    capsules,
    data_products,
    tags,
    domains,
    ingestion_jobs
CASCADE;
"

# For local development (adjust connection details as needed):
psql -h localhost -p 5433 -U dab -d dab -c "
TRUNCATE TABLE
    lineage_edges,
    column_lineage_edges,
    conformance_violations,
    capsule_tags,
    column_tags,
    data_product_capsules,
    columns,
    capsules,
    data_products,
    tags,
    domains,
    ingestion_jobs
CASCADE;
"
```

### Clear Cache

After resetting the database, clear the cache to ensure stale data is not served:

```bash
# If using Redis
redis-cli -h localhost -p 6379 FLUSHDB

# Or restart the application to clear in-memory cache
docker compose restart dab-api
```

### Selective Reset

You can also reset specific components:

```bash
# Clear only capsules and lineage (keeps tag definitions, rules)
psql -h localhost -p 5433 -U dab -d dab -c "
TRUNCATE TABLE
    lineage_edges,
    column_lineage_edges,
    conformance_violations,
    capsule_tags,
    column_tags,
    data_product_capsules,
    columns,
    capsules
CASCADE;
"

# Clear only lineage information
psql -h localhost -p 5433 -U dab -d dab -c "
TRUNCATE TABLE lineage_edges, column_lineage_edges CASCADE;
"

# Clear only conformance violations (to re-run evaluation)
psql -h localhost -p 5433 -U dab -d dab -c "
TRUNCATE TABLE conformance_violations;
"
```

### Verify Reset

Confirm the reset was successful:

```bash
# Check capsule count (should be 0)
dab capsules --limit 1

# Or via API
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8002/api/v1/capsules?limit=1"
# Expected: {"items": [], "total": 0, ...}

# Verify application health
curl http://localhost:8002/api/v1/health/ready
# Expected: {"status": "ready"}
```

After resetting, you can re-ingest your data:

```bash
# Re-ingest dbt project
dab ingest dbt --manifest /path/to/manifest.json --catalog /path/to/catalog.json

# Re-ingest Airflow
dab ingest airflow --base-url https://airflow.example.com --auth-mode bearer_env
```
