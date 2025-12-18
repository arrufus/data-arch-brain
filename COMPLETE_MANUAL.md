# Data Capsule Server - Complete System Manual

**Version**: 1.0
**Last Updated**: December 2025
**Application**: Data Capsule Server (DCS)

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Architecture](#2-system-architecture)
3. [Features & Capabilities](#3-features--capabilities)
4. [Components & Services](#4-components--services)
5. [Getting Started](#5-getting-started)
6. [User Guide](#6-user-guide)
7. [Administrator Guide](#7-administrator-guide)
8. [API Reference](#8-api-reference)
9. [Configuration Reference](#9-configuration-reference)
10. [Operations & Monitoring](#10-operations--monitoring)
11. [Security](#11-security)
12. [Troubleshooting](#12-troubleshooting)
13. [Support & Resources](#13-support--resources)

---

## 1. Introduction

### 1.1 What is Data Capsule Server?

**Data Capsule Server** is a comprehensive, read-only architecture intelligence platform designed to provide unified visibility and governance for your organization's data landscape. It ingests metadata from various data infrastructure sources, constructs a property graph representation of data assets, and delivers actionable insights for data governance, architecture conformance, and sensitive data tracking.

### 1.2 Key Value Propositions

- **Unified Visibility**: Single pane of glass for all data assets across multiple source systems
- **PII & Sensitive Data Tracking**: Automated detection and lineage tracing of sensitive data through transformation pipelines
- **Architecture Conformance**: Continuous validation against defined standards (naming conventions, Medallion architecture, etc.)
- **Impact Analysis**: Assess downstream effects of proposed changes to data models
- **Redundancy Detection**: Identify duplicate or overlapping data assets to optimize costs
- **Graph-Based Analysis**: Leverage property graph capabilities for complex lineage and relationship queries
- **Modern Web Interface**: Intuitive React-based dashboard with 10+ specialized pages

### 1.3 Target Audience

This manual is designed for:

- **Data Architects**: Design and maintain data architecture standards
- **Data Engineers**: Build and maintain data pipelines
- **Platform Engineers**: Deploy and operate the platform
- **Data Governance Teams**: Monitor compliance and enforce policies
- **Compliance Officers**: Track and audit sensitive data usage
- **Data Product Owners**: Manage data products and SLOs

### 1.4 System Requirements

**Minimum Requirements:**
- Docker Desktop 4.0+
- Docker Compose 2.0+
- 4 GB RAM
- 10 GB disk space

**Recommended Requirements:**
- Docker Desktop 4.30+
- Docker Compose 2.20+
- 8 GB RAM
- 50 GB disk space (for production data)

**Supported Platforms:**
- macOS (Intel & Apple Silicon)
- Linux (Ubuntu 20.04+, RHEL 8+)
- Windows 10/11 with WSL2

---

## 2. System Architecture

### 2.1 High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        Web[Web Dashboard<br/>React + Next.js]
        CLI[CLI Tool<br/>dcs command]
        API_Client[REST API Clients]
    end

    subgraph "API Layer"
        FastAPI[FastAPI Application<br/>Port 8002]
        Auth[Authentication<br/>API Key Middleware]
        RateLimit[Rate Limiter]
    end

    subgraph "Service Layer"
        IngestSvc[Ingestion Service]
        GraphSvc[Graph Service]
        PIISvc[PII Service]
        ConfSvc[Conformance Service]
        RedundSvc[Redundancy Service]
        ReportSvc[Report Service]
    end

    subgraph "Repository Layer"
        CapsuleRepo[Capsule Repository]
        ColumnRepo[Column Repository]
        LineageRepo[Lineage Repository]
        RuleRepo[Rule Repository]
        ViolationRepo[Violation Repository]
    end

    subgraph "Data Layer"
        Postgres[(PostgreSQL 15<br/>Primary Database)]
        Redis[(Redis<br/>Cache & Rate Limiting)]
    end

    Web --> FastAPI
    CLI --> FastAPI
    API_Client --> FastAPI

    FastAPI --> Auth
    Auth --> RateLimit
    RateLimit --> IngestSvc
    RateLimit --> GraphSvc
    RateLimit --> PIISvc
    RateLimit --> ConfSvc

    IngestSvc --> CapsuleRepo
    GraphSvc --> LineageRepo
    PIISvc --> ColumnRepo
    ConfSvc --> RuleRepo
    RedundSvc --> CapsuleRepo
    ReportSvc --> CapsuleRepo

    CapsuleRepo --> Postgres
    ColumnRepo --> Postgres
    LineageRepo --> Postgres
    RuleRepo --> Postgres
    ViolationRepo --> Postgres

    RateLimit -.-> Redis
```

### 2.2 Architectural Layers

#### Client Layer
- **Web Dashboard**: React 18 + Next.js 16 application providing visual interface
- **CLI Tool**: Python-based command-line interface for automation and scripting
- **REST API Clients**: Third-party integrations and custom tools

#### API Layer (FastAPI)
- **Routers**: 13 specialized routers handling different domains
  - Capsules, Columns, Domains, Tags, Products
  - Compliance, Conformance, Violations
  - Ingest, Graph, Reports, Redundancy, Health
- **Middleware**: Authentication, CORS, request logging, error handling
- **Rate Limiting**: SlowAPI-based rate limiting with Redis backend

#### Service Layer
Core business logic organized into specialized services:

| Service | Responsibility |
|---------|----------------|
| **Ingestion Service** | Orchestrates metadata parsing and loading from dbt and Airflow |
| **Graph Service** | Manages graph operations, lineage traversal, and graph export |
| **PII Service** | PII detection, exposure analysis, and lineage tracing |
| **Conformance Service** | Rule engine, violation detection, and scoring |
| **Redundancy Service** | Similarity detection using multiple algorithms |
| **Report Service** | Report generation in JSON, CSV, and HTML formats |
| **SLO Service** | Data product SLO tracking and alerting |

#### Repository Layer
Data access abstraction with async SQLAlchemy:

| Repository | Tables Managed |
|------------|----------------|
| **Capsule Repository** | `capsules` table - data assets |
| **Column Repository** | `columns` table - column metadata |
| **Lineage Repository** | `capsule_lineage`, `column_lineage` tables |
| **Domain Repository** | `domains` table - business domains |
| **Tag Repository** | `tags`, `capsule_tags`, `column_tags` tables |
| **Rule Repository** | `rules` table - conformance rules |
| **Violation Repository** | `violations` table - detected violations |
| **Data Product Repository** | `data_products` table - data product definitions |

#### Data Layer
- **PostgreSQL 15**: Primary relational database with JSONB support
- **Redis**: Caching layer and rate limiting storage

### 2.3 Data Flow Diagrams

#### Ingestion Flow (dbt)

```
┌─────────────┐
│ dbt Project │
│  manifest   │
│  catalog    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│ 1. PARSE                    │
│    • Read manifest.json     │
│    • Read catalog.json      │
│    • Extract models, sources│
│    • Extract column metadata│
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ 2. TRANSFORM                │
│    • Generate URNs          │
│    • Detect PII patterns    │
│    • Build lineage edges    │
│    • Infer layers           │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ 3. LOAD                     │
│    • Upsert capsules        │
│    • Upsert columns         │
│    • Create/update edges    │
│    • Record ingestion stats │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ 4. POST-PROCESS (Optional)  │
│    • Run conformance rules  │
│    • Calculate scores       │
│    • Detect violations      │
└─────────────────────────────┘
```

#### Query Flow (Lineage)

```
User Request: GET /api/v1/capsules/{urn}/lineage?direction=both&depth=3
                           │
                           ▼
                  ┌────────────────┐
                  │  API Router    │
                  │  Parse params  │
                  └────────┬───────┘
                           │
                           ▼
                  ┌────────────────┐
                  │ Graph Service  │
                  │  • Resolve URN │
                  │  • BFS/DFS     │
                  │  • Depth limit │
                  └────────┬───────┘
                           │
                           ▼
                  ┌────────────────┐
                  │ Repository     │
                  │  • Recursive   │
                  │    CTE query   │
                  │  • Join nodes  │
                  └────────┬───────┘
                           │
                           ▼
                  ┌────────────────┐
                  │   Response     │
                  │  JSON with     │
                  │  nodes & edges │
                  └────────────────┘
```

### 2.4 Deployment Architecture

#### Docker Compose Deployment (Standard)

```
┌─────────────────────────────────────────────────────────┐
│              Docker Network: dcs-network                │
│                                                         │
│  ┌──────────────────┐    ┌──────────────────┐         │
│  │  dcs-frontend    │    │    dcs-api       │         │
│  │  Next.js App     │    │   FastAPI App    │         │
│  │  Port: 3000      │◄───│   Port: 8002     │         │
│  └──────────────────┘    └────────┬─────────┘         │
│                                   │                     │
│                          ┌────────┴─────────┐          │
│                          │                  │          │
│                    ┌─────▼──────┐    ┌─────▼──────┐   │
│                    │ PostgreSQL │    │   Redis    │   │
│                    │ Port: 5432 │    │ Port: 6379 │   │
│                    └────────────┘    └────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Services:**
- **dcs-frontend**: Next.js web dashboard (port 3000)
- **dcs-api**: FastAPI backend (port 8002)
- **postgres**: PostgreSQL 15 database (port 5433 external)
- **redis**: Redis cache (port 6379, internal only)

**Volumes:**
- `postgres_data`: Persistent PostgreSQL data
- `./data`: Mounted read-only for ingestion files
- `./backend/config`: Configuration and rules directory

---

## 3. Features & Capabilities

### 3.1 Web Dashboard

The modern React-based web dashboard provides visual access to all platform capabilities.

#### Available Pages

| Page | Route | Description |
|------|-------|-------------|
| **Home** | `/` | Dashboard with quick stats and recent activity |
| **Data Capsule Browser** | `/capsules` | Searchable, filterable table of all data assets |
| **Capsule Detail** | `/capsules/[urn]` | Comprehensive view with tabs for columns, lineage, violations |
| **Interactive Lineage** | `/lineage` | React Flow-based graph visualization with search |
| **PII Compliance** | `/compliance` | 3 tabs: Inventory, Exposure Detection, Trace |
| **Conformance Scoring** | `/conformance` | Real-time architecture conformance monitoring |
| **Impact Analysis** | `/impact` | Assess downstream effects with configurable depth |
| **Redundancy Detection** | `/redundancy` | Find similar capsules using multiple algorithms |
| **Domains** | `/domains` | Browse and manage business domains |
| **Data Products** | `/products` | Manage data products with SLO tracking |
| **Tags** | `/tags` | Tag management and exploration |
| **Settings** | `/settings` | System configuration and rule management |
| **Reports** | `/reports` | Generate and download reports in multiple formats |

#### Key Features

**Search & Discovery**
- Full-text search across capsule names and descriptions
- Advanced filtering (layer, type, domain, PII presence)
- Pagination with configurable page size
- Sort by multiple columns

**Lineage Visualization**
- Upstream and downstream lineage graphs
- Configurable depth (1-5 levels)
- Interactive nodes with click-to-navigate
- Type-ahead search for quick navigation

**PII Compliance**
- PII inventory with distribution charts (Recharts)
- Exposure detection with severity classification
- Column-level PII lineage tracing
- CSV export with calculated percentages

**Reporting**
- PII Inventory Report (JSON, CSV, HTML)
- Conformance Report (JSON, CSV, HTML)
- Capsule Summary Report (JSON, CSV)
- Auto-download with timestamped filenames

### 3.2 Core Platform Capabilities

#### 3.2.1 Metadata Ingestion

**Supported Sources:**
- **dbt Projects**: manifest.json, catalog.json, schema.yml parsing
- **Airflow**: DAG and task metadata via REST API

**Ingestion Features:**
- Incremental updates (upsert by URN)
- Secret redaction from connection strings
- Automatic PII detection using patterns and tags
- Layer inference (bronze/silver/gold)
- Lineage edge construction
- Post-ingestion conformance checks

**Statistics Tracked:**
- Capsules created/updated
- Columns created/updated
- Lineage edges created
- PII columns detected
- Ingestion duration

#### 3.2.2 PII & Sensitive Data Tracking

**Detection Methods:**
1. **Tag-based**: Reads dbt meta tags (`pii: true`, `pii_type: email`)
2. **Pattern-based**: Regex patterns for column names
   - Email: `(?i)(email|e_mail)`
   - SSN: `(?i)(ssn|social_security)`
   - Phone: `(?i)(phone|mobile|cell)`
   - Address: `(?i)(address|street|city|zip)`
   - Names: `(?i)(first_name|last_name|full_name)`

**Lineage Tracing:**
- Trace PII from source to consumption layers
- Identify unmasked PII in reporting/analytics layers
- Track transformation types (direct, masked, hashed, aggregated)
- Generate PII flow diagrams

**Exposure Analysis:**
- Detect PII columns in Gold/Reporting layers
- Check for masking transformations
- Classify exposure severity (Critical, High, Medium, Low)
- Generate remediation recommendations

#### 3.2.3 Architecture Conformance

**Rule Categories:**
- **Naming Conventions**: Pattern matching (regex) for naming standards
- **Layering Rules**: Validate Medallion architecture (bronze/silver/gold)
- **Documentation Rules**: Ensure descriptions exist
- **PII Rules**: Validate PII handling and masking
- **Testing Rules**: Check for data quality tests

**Rule Definition (YAML):**
```yaml
rule_id: NAMING_001
name: Staging models must start with stg_
severity: warning
category: naming
scope: capsule
definition:
  type: pattern
  pattern: ^stg_
  apply_if:
    layer: silver
    capsule_type: model
```

**Conformance Scoring:**
- Weighted score calculation (0-100)
- Severity-based weighting (Critical=4, Error=3, Warning=2, Info=1)
- Domain-level and global scores
- Real-time violation tracking

#### 3.2.4 Graph-Based Analysis

**Lineage Queries:**
- Upstream lineage (data sources)
- Downstream lineage (data consumers)
- Bidirectional lineage (full context)
- Configurable depth limits

**Impact Analysis:**
- Identify all downstream dependencies
- Calculate blast radius for changes
- Support for multi-hop impact
- Filter by capsule type or layer

**Redundancy Detection:**
- Column-based similarity (Jaccard index)
- Name similarity (Levenshtein distance)
- Schema structure comparison
- Duplicate candidate identification

#### 3.2.5 Graph Export

**Supported Formats:**

| Format | Use Case | Tools |
|--------|----------|-------|
| **GraphML** | Graph analysis | yEd, Gephi, Cytoscape, NetworkX |
| **DOT** | Visualization | Graphviz |
| **Cypher** | Import to graph DB | Neo4j, Amazon Neptune |
| **Mermaid** | Documentation | GitHub, GitLab, Notion |
| **JSON-LD** | Semantic web | RDF tools, knowledge graphs |

**Export Options:**
- Full graph export
- Lineage subgraph export (for specific URN)
- Filtered exports (by layer, domain, etc.)

#### 3.2.6 Data Products

**Features:**
- Group capsules into logical data products
- Define owners and domains
- Track SLOs (freshness, quality, availability)
- Monitor SLO compliance status
- Data Mesh pattern support

**SLO Tracking:**
- Freshness SLO: Last update within threshold
- Quality SLO: Conformance score above threshold
- Availability SLO: Uptime percentage
- Custom SLO definitions

### 3.3 Integration Capabilities

#### 3.3.1 REST API

- **60+ endpoints** across 13 routers
- **OpenAPI 3.0** specification
- **Swagger UI** at `/api/v1/docs`
- **ReDoc** at `/api/v1/redoc`
- **API Key authentication**
- **Rate limiting** (configurable per endpoint)
- **CORS support** for browser clients

#### 3.3.2 CLI Tool

**Command Groups:**
- `dcs ingest`: Ingest metadata from sources
- `dcs capsules`: Query and list capsules
- `dcs pii`: PII inventory and analysis
- `dcs conformance`: Conformance checks and scoring
- `dcs lineage`: Lineage queries
- `dcs export`: Graph export operations

---

## 4. Components & Services

### 4.1 Backend Services

#### 4.1.1 Ingestion Service
**Location**: `backend/src/services/ingestion.py`

**Responsibilities:**
- Orchestrate end-to-end ingestion pipeline
- Coordinate parsers (dbt, Airflow)
- Transform raw metadata to normalized format
- Load data into graph database
- Track ingestion statistics
- Handle errors and rollbacks

**Key Methods:**
```python
async def ingest_dbt(manifest_path, catalog_path, project_name) -> IngestionResult
async def ingest_airflow(base_url, auth_config, filters) -> IngestionResult
```

#### 4.1.2 Graph Service
**Location**: `backend/src/services/graph_export.py`

**Responsibilities:**
- Property graph export in multiple formats
- Lineage traversal (BFS/DFS)
- Graph query optimization
- Subgraph extraction

**Supported Formats:**
- GraphML, DOT, Cypher, Mermaid, JSON-LD

#### 4.1.3 PII Service
**Location**: `backend/src/services/compliance.py`

**Responsibilities:**
- PII detection using patterns and tags
- PII inventory generation
- Exposure detection and risk assessment
- Column-level lineage tracing
- Remediation recommendations

**Detection Patterns:**
- 20+ built-in PII patterns
- Custom pattern support
- Tag-based detection from dbt metadata

#### 4.1.4 Conformance Service
**Location**: `backend/src/services/conformance.py`

**Responsibilities:**
- Rule loading from YAML files
- Rule execution engine
- Violation detection and scoring
- Score calculation (weighted)
- Violation lifecycle management

**Rule Types:**
- Pattern rules (regex matching)
- Graph rules (lineage conditions)
- Property rules (attribute checks)

#### 4.1.5 Redundancy Service
**Location**: `backend/src/services/redundancy.py`

**Responsibilities:**
- Similarity detection using multiple algorithms
- Column-based comparison (Jaccard)
- Name similarity (Levenshtein)
- Schema structure analysis
- Duplicate candidate ranking

**Algorithms:**
- Jaccard similarity for column sets
- Levenshtein distance for names
- Cosine similarity for vectors

#### 4.1.6 Secret Redaction Service
**Location**: `backend/src/services/secret_redaction.py`

**Responsibilities:**
- Scan connection strings for credentials
- Redact passwords, tokens, API keys
- Safe logging and storage
- Pattern-based detection

**Redacted Elements:**
- Database passwords
- API keys and tokens
- OAuth credentials
- SSH keys

#### 4.1.7 SLO Service
**Location**: `backend/src/services/slo.py`

**Responsibilities:**
- SLO definition and tracking
- Compliance status calculation
- Alerting for SLO violations
- Historical trend analysis

### 4.2 Parsers

#### 4.2.1 dbt Parser
**Location**: `backend/src/parsers/dbt_parser.py`

**Capabilities:**
- Parse manifest.json (models, sources, dependencies)
- Parse catalog.json (column metadata, statistics)
- Parse schema.yml (descriptions, meta, tests)
- Extract lineage from `depends_on` references
- Detect PII from meta tags and patterns

#### 4.2.2 Airflow Parser
**Location**: `backend/src/parsers/airflow_parser.py`

**Capabilities:**
- Connect to Airflow REST API
- Retrieve DAG definitions
- Extract task metadata
- Build task dependency graph
- Support multiple authentication modes

**Authentication Modes:**
- None (for local/dev)
- Bearer token (from environment)
- Basic auth (from environment)

### 4.3 Repositories

All repositories use **async SQLAlchemy 2.0** with PostgreSQL.

#### 4.3.1 Capsule Repository
**Location**: `backend/src/repositories/capsule.py`

**Methods:**
- `get_by_urn(urn)`: Retrieve capsule by URN
- `list_capsules(filters, pagination)`: List with filtering
- `create(capsule)`: Create new capsule
- `update(urn, data)`: Update existing capsule
- `search(query)`: Full-text search
- `get_statistics()`: Aggregate statistics

#### 4.3.2 Column Repository
**Location**: `backend/src/repositories/column.py`

**Methods:**
- `get_by_capsule(capsule_id)`: Get all columns for capsule
- `get_pii_columns(filters)`: Filter by PII type
- `get_by_semantic_type(type)`: Filter by semantic classification

#### 4.3.3 Lineage Repository
**Location**: `backend/src/repositories/lineage.py`

**Methods:**
- `get_lineage(urn, direction, depth)`: Recursive lineage query
- `get_upstream(urn, depth)`: Upstream dependencies
- `get_downstream(urn, depth)`: Downstream consumers
- `get_impact(urn, depth)`: Impact analysis

Uses **recursive CTEs** for efficient graph traversal.

### 4.4 Database Models

#### Core Models (SQLAlchemy)

**Capsules** (`backend/src/models/capsule.py`)
- Primary data asset representation
- Attributes: urn, name, type, layer, schema, database
- Relationships: columns, lineage, violations, tags

**Columns** (`backend/src/models/column.py`)
- Column-level metadata
- Attributes: urn, name, data_type, semantic_type, pii_type
- Relationships: capsule, lineage, tags

**Lineage** (`backend/src/models/lineage.py`)
- Capsule-to-capsule and column-to-column edges
- Attributes: source_id, target_id, edge_type, transformation

**Rules** (`backend/src/models/rule.py`)
- Conformance rule definitions
- Attributes: rule_id, severity, category, scope, definition

**Violations** (`backend/src/models/violation.py`)
- Detected conformance violations
- Attributes: rule_id, capsule_id, severity, status, message

---

## 5. Getting Started

### 5.1 Installation

#### Prerequisites Check

```bash
# Verify Docker installation
docker --version
# Output: Docker version 24.0.0 or higher

# Verify Docker Compose
docker compose version
# Output: Docker Compose version 2.20.0 or higher

# Check available memory
docker info | grep Memory
# Recommended: 4GB+ available
```

#### Clone Repository

```bash
git clone <repository-url>
cd data-capsule-server
```

#### Environment Setup

1. **Backend Configuration**

```bash
cd backend
cp .env.example .env

# Edit .env with your values
# Required variables:
# - DATABASE_URL
# - API_KEY
# - LOG_LEVEL
```

2. **Frontend Configuration**

```bash
cd frontend
cp .env.example .env.local

# Edit .env.local
# Required variables:
# - NEXT_PUBLIC_API_URL=http://localhost:8002
# - NEXT_PUBLIC_API_KEY=<your-api-key>
```

### 5.2 Starting the Application

#### Using Docker Compose (Recommended)

```bash
# Start all services
docker compose -f docker/docker-compose.yml up -d

# Verify services are running
docker compose ps

# Expected output:
# NAME                IMAGE               STATUS
# dcs-api             dcs-backend         Up
# dcs-postgres        postgres:15         Up (healthy)
# dcs-frontend        dcs-frontend        Up
```

#### Run Database Migrations

```bash
# Apply all migrations
docker compose exec dcs-api alembic upgrade head

# Verify migration status
docker compose exec dcs-api alembic current
```

#### Verify Installation

```bash
# Check API health
curl http://localhost:8002/api/v1/health

# Expected response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "version": "1.0.0"
# }

# Access web dashboard
open http://localhost:3000
```

### 5.3 First Ingestion

#### Prepare dbt Artifacts

```bash
# In your dbt project
cd /path/to/your/dbt/project
dbt compile
dbt docs generate

# Artifacts created at:
# - target/manifest.json
# - target/catalog.json
```

#### Ingest dbt Project

```bash
# Using CLI
docker compose exec dcs-api python -m src.cli.main ingest dbt \
  --manifest /app/data/manifest.json \
  --catalog /app/data/catalog.json

# Using Makefile
make ingest-dbt MANIFEST=./data/manifest.json
```

#### Verify Ingestion

```bash
# Check capsule count
curl -H "X-API-Key: your-api-key" \
  http://localhost:8002/api/v1/capsules?limit=10

# View in dashboard
open http://localhost:3000/capsules
```

### 5.4 Development Setup

#### Local Backend Development

```bash
cd backend

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/ -v

# Start development server
uvicorn src.api.main:app --reload --port 8002
```

#### Local Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
npm start
```

---

## 6. User Guide

### 6.1 Web Dashboard Usage

Please refer to the detailed Web Dashboard section in the full documentation for:
- Navigation guide
- Data Capsule Browser usage
- Capsule Detail View
- Interactive Lineage Graph
- PII Compliance Dashboard
- Conformance Scoring
- Impact Analysis
- Redundancy Detection
- Reports generation

### 6.2 CLI Usage

#### 6.2.1 Installation & Setup

```bash
# Install CLI globally
pip install -e backend/

# Verify installation
dcs --version

# Configure API endpoint and key
export DCS_API_URL=http://localhost:8002
export DCS_API_KEY=your-api-key

# Test connection
dcs health
```

#### 6.2.2 Common CLI Commands

**Ingestion:**
```bash
# dbt ingestion
dcs ingest dbt --manifest /path/to/manifest.json --catalog /path/to/catalog.json

# Airflow ingestion
dcs ingest airflow --base-url http://localhost:8080
```

**Query:**
```bash
# List capsules
dcs capsules list --layer gold

# Get capsule details
dcs capsules get "urn:dcs:dbt:model:jaffle_shop:dim_customers"

# Get lineage
dcs lineage upstream <urn> --depth 3
```

**PII:**
```bash
# PII inventory
dcs pii inventory

# PII exposure detection
dcs pii exposure

# Trace PII column
dcs pii trace <column-urn>
```

**Conformance:**
```bash
# Get conformance score
dcs conformance score

# List violations
dcs conformance violations --severity error
```

**Export:**
```bash
# Export graph
dcs export graph --format graphml --output graph.graphml
```

### 6.3 API Usage

#### Authentication

All API requests require API key in header:

```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:8002/api/v1/capsules
```

#### Common Endpoints

**List Capsules:**
```bash
GET /api/v1/capsules?layer=gold&limit=10
```

**Get Lineage:**
```bash
GET /api/v1/capsules/{urn}/lineage?direction=both&depth=3
```

**PII Inventory:**
```bash
GET /api/v1/compliance/pii-inventory
```

**Conformance Score:**
```bash
GET /api/v1/conformance/score
```

**Export Graph:**
```bash
GET /api/v1/graph/export?format=graphml
```

---

## 7. Administrator Guide

### 7.1 Deployment

#### Docker Compose Deployment

```bash
# Production deployment
docker compose -f docker/docker-compose.yml up -d

# Verify deployment
docker compose ps
docker compose logs -f

# Run migrations
docker compose exec dcs-api alembic upgrade head
```

#### Kubernetes Deployment

Sample Kubernetes manifests are available in the `k8s/` directory. Key resources:
- Deployment: `k8s/deployment.yaml`
- Service: `k8s/service.yaml`
- Ingress: `k8s/ingress.yaml`
- ConfigMap: `k8s/configmap.yaml`
- Secrets: `k8s/secrets.yaml`

### 7.2 Database Management

#### Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

#### Backup & Restore

```bash
# Backup
docker compose exec -T postgres pg_dump -U dcs dcs > backup.sql

# Restore
docker compose exec -T postgres psql -U dcs dcs < backup.sql
```

### 7.3 Monitoring

#### Health Checks

```bash
# Full health check
curl http://localhost:8002/api/v1/health

# Liveness probe
curl http://localhost:8002/api/v1/health/live

# Readiness probe
curl http://localhost:8002/api/v1/health/ready
```

#### Metrics

Prometheus metrics available at:
```
http://localhost:8002/metrics
```

Key metrics:
- `dcs_http_requests_total`
- `dcs_http_request_duration_seconds`
- `dcs_capsule_count`
- `dcs_pii_column_count`
- `dcs_conformance_score`

---

## 8. Configuration Reference

### 8.1 Environment Variables

#### Backend Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `API_KEY` | Yes | - | API authentication key |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `ENVIRONMENT` | No | development | Environment name |
| `MAX_LINEAGE_DEPTH` | No | 10 | Maximum lineage depth |
| `PII_DETECTION_ENABLED` | No | true | Enable PII detection |
| `CONFORMANCE_ON_INGEST` | No | true | Run conformance after ingestion |
| `CORS_ORIGINS` | No | ["*"] | Allowed CORS origins (JSON array) |

#### Frontend Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes | - | Backend API URL |
| `NEXT_PUBLIC_API_KEY` | Yes | - | API authentication key |

### 8.2 Conformance Rules

Rules are defined in YAML format in `backend/config/rules/`.

Example rule:
```yaml
rules:
  - rule_id: NAMING_001
    name: Staging models must start with stg_
    severity: warning
    category: naming
    scope: capsule
    enabled: true
    definition:
      type: pattern
      pattern: ^stg_
      apply_if:
        layer: silver
        capsule_type: model
```

### 8.3 PII Detection Patterns

PII patterns are configured in `backend/config/pii_patterns.yml`:

```yaml
patterns:
  email:
    pattern: (?i)(email|e_mail)
    pii_type: email
    severity: high

  ssn:
    pattern: (?i)(ssn|social_security)
    pii_type: ssn
    severity: critical
```

---

## 9. Operations & Monitoring

### 9.1 Health Monitoring

#### Health Endpoints

```bash
# Full health check
GET /api/v1/health
Response: {"status": "healthy", "database": "connected"}

# Liveness probe
GET /api/v1/health/live
Response: {"status": "alive"}

# Readiness probe
GET /api/v1/health/ready
Response: {"status": "ready"}
```

### 9.2 Logging

#### Log Configuration

```bash
# Set log level
LOG_LEVEL=DEBUG

# Log formats: json or text
LOG_FORMAT=json
```

#### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f dcs-api

# Last N lines
docker compose logs --tail=100 dcs-api
```

### 9.3 Performance Monitoring

#### Database Performance

```sql
-- View slow queries
SELECT query, mean_time, calls
FROM pg_stat_statements
WHERE mean_time > 1000
ORDER BY mean_time DESC
LIMIT 20;

-- Index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'dab'
ORDER BY idx_scan DESC;
```

#### API Performance

Monitor via Prometheus metrics:
- Request latency (p50, p95, p99)
- Request rate
- Error rate
- Cache hit rate

---

## 10. Security

### 10.1 Authentication

**API Key Authentication:**
- Include `X-API-Key` header in all requests
- Generate secure keys using `secrets.token_urlsafe(32)`
- Rotate keys regularly

### 10.2 Data Security

**Secret Redaction:**
- Automatic redaction of passwords, tokens, keys
- Safe logging and storage
- Pattern-based detection

**Encryption:**
- TLS for data in transit
- Database encryption for data at rest
- Secure credential storage

### 10.3 Network Security

**Firewall Rules:**
```bash
# Allow API port
ufw allow 8002/tcp

# Restrict database access
ufw allow from 172.18.0.0/16 to any port 5432
```

**CORS Configuration:**
```python
CORS_ORIGINS=["http://localhost:3000", "https://dcs.example.com"]
```

---

## 11. Troubleshooting

### 11.1 Common Issues

#### API Not Starting

**Check logs:**
```bash
docker compose logs dcs-api
```

**Common causes:**
- Database connection failed
- Missing environment variables
- Port conflict
- Migration failed

**Solutions:**
- Verify PostgreSQL is running
- Check `.env` file
- Change port or kill process
- Run migrations manually

#### Ingestion Fails

**Check logs:**
```bash
docker compose logs dcs-api | grep ingestion
```

**Common causes:**
- Invalid manifest.json
- File not found
- Permission denied
- Parser error

**Solutions:**
- Validate JSON: `jq '.' manifest.json`
- Use absolute path
- Fix file permissions: `chmod 644 manifest.json`
- Check dbt version compatibility

#### Dashboard Not Loading

**Check logs:**
```bash
docker compose logs dcs-frontend
```

**Common causes:**
- API not reachable
- Invalid API key
- CORS error
- Build error

**Solutions:**
- Verify `NEXT_PUBLIC_API_URL`
- Update `NEXT_PUBLIC_API_KEY`
- Add frontend URL to CORS_ORIGINS
- Rebuild frontend

#### Slow Queries

**Diagnose:**
```sql
SELECT query, mean_time FROM pg_stat_statements
WHERE mean_time > 1000 ORDER BY mean_time DESC LIMIT 10;
```

**Solutions:**
- Add indexes
- Increase connection pool
- Enable caching
- Optimize queries

### 11.2 Debug Mode

```bash
# Enable debug logging
LOG_LEVEL=DEBUG docker compose restart dcs-api

# View detailed logs
docker compose logs -f dcs-api
```

### 11.3 Getting Help

When reporting issues, include:
- DCS version
- Environment (Docker, Kubernetes)
- Operating system
- Complete logs (LOG_LEVEL=DEBUG)
- Steps to reproduce
- Expected vs actual behavior

---

## 12. Support & Resources

### 12.1 Documentation

- **API Documentation**: http://localhost:8002/api/v1/docs
- **Product Specification**: `docs/specs/product_specification.md`
- **System Architecture**: `docs/design_docs/system_architecture.md`
- **Database Schema**: `docs/design_docs/database_schema.md`
- **User Guide**: `docs/USER_GUIDE.md`
- **Runbook**: `docs/RUNBOOK.md`

### 12.2 Changelog

**Version 1.0.0** (December 2025)
- Initial release
- dbt and Airflow ingestion
- Web dashboard with 10+ pages
- PII compliance tracking
- Conformance scoring
- Graph export (5 formats)
- REST API with 60+ endpoints
- CLI tool

### 12.3 License

MIT License - see LICENSE file for details

---

## Appendix A: Quick Reference

### Common Commands

```bash
# Start services
make up

# Stop services
make down

# View logs
make logs

# Run migrations
make migrate

# Ingest dbt
make ingest-dbt MANIFEST=/path/to/manifest.json

# Check health
curl http://localhost:8002/api/v1/health
```

### Environment Variables

```bash
# Backend
DATABASE_URL=postgresql+asyncpg://dcs:password@localhost:5433/dcs
API_KEY=dcs_your_secure_key
LOG_LEVEL=INFO

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8002
NEXT_PUBLIC_API_KEY=dcs_your_secure_key
```

---

## Appendix B: URN Format

**Format**: `urn:dcs:{source}:{type}:{namespace}:{name}`

**Examples:**
- `urn:dcs:dbt:model:jaffle_shop:dim_customers`
- `urn:dcs:dbt:source:jaffle_shop:raw_orders`
- `urn:dcs:dbt:column:jaffle_shop:dim_customers:email`
- `urn:dcs:airflow:dag:production:customer_pipeline`

---

## Appendix C: Glossary

- **Capsule**: A data asset (table, view, model, source)
- **URN**: Uniform Resource Name - unique identifier
- **Lineage**: Data flow relationships between capsules
- **PII**: Personally Identifiable Information
- **Conformance**: Architecture compliance with rules
- **Layer**: Medallion architecture layer (bronze/silver/gold)
- **Semantic Type**: Business meaning (PII, key, metric)
- **Violation**: Detected breach of conformance rule
- **Data Product**: Logical grouping with SLOs
- **SLO**: Service Level Objective - quality target

---

**End of Manual**

For questions or support, please refer to the documentation or contact the Data Capsule Server team.

*Version 1.0.0 - December 2025*
