# Data Capsule Server

A read-only architecture intelligence platform that ingests metadata from data infrastructure sources, constructs a unified graph representation of your data landscape, and provides intelligent insights for data governance, architecture conformance, and sensitive data tracking.

## Features

### Web Dashboard (React + Next.js)
- **Modern UI**: Full-featured web dashboard with 10+ pages and responsive design
- **Data Capsule Browser**: Search, filter, and explore all data assets with pagination
- **Capsule Detail View**: Comprehensive metadata, columns, lineage visualization, and violations
- **Interactive Lineage Visualization**: React Flow-based graph with type-ahead search and deep linking
- **PII Compliance Dashboard**: Inventory, exposure detection, and lineage tracing
- **Conformance Scoring**: Real-time architecture conformance monitoring with violation drill-down
- **Impact Analysis View**: Assess downstream effects of changes with configurable depth
- **Redundancy Detection UI**: Find similar capsules with multi-algorithm similarity scoring
- **Settings/Configuration**: Centralized management for domains, tags, products, and rules
- **Domains, Products, Tags**: Browse and manage organizational data structures
- **Reports & Export**: Generate downloadable reports in JSON, CSV, or HTML

### Core Platform
- **Metadata Ingestion**: Parse dbt artifacts and Airflow DAG metadata with secret redaction
- **PII Lineage Tracking**: Trace sensitive data through transformation pipelines, detect exposure risks
- **Architecture Conformance**: Validate data models against defined standards (Medallion, naming conventions, etc.)
- **Graph-Based Analysis**: Query lineage, impact analysis, and redundancy detection
- **Data Products**: Group capsules into logical data products with SLO tracking (Data Mesh pattern)
- **Tag Management**: Apply and query tags as graph edges (TAGGED_WITH relationships)
- **Graph Export**: Export property graph in multiple formats (GraphML, DOT, Cypher, Mermaid, JSON-LD)
- **REST API**: 60+ endpoints across 10 routers with OpenAPI documentation

## Quick Start

### Prerequisites

- Docker Desktop 4.0+
- Docker Compose 2.0+
- Make (optional, for convenience commands)

### Start Services

```bash
# Clone the repository
git clone <repository-url>
cd data-capsule-server

# Start all services
make up

# Or without make:
docker compose -f docker/docker-compose.yml up -d

# Run database migrations
make migrate

# Verify the API is running
curl http://localhost:8001/api/v1/health
```

### Development Mode

```bash
# Start with hot reload enabled
make up-dev

# Start with pgAdmin (accessible at http://localhost:5050)
make up-tools
```

## Web Dashboard

The Data Capsule Server includes a modern React web dashboard for visual exploration and management of your data architecture.

### Access the Dashboard

- **URL**: http://localhost:3000 (after running `docker-compose up` or `npm run dev` in frontend/)
- **API Backend**: http://localhost:8002 (FastAPI REST API)
- **Authentication**: Uses API key configured in `frontend/.env.local`

### Dashboard Pages

- **Data Capsule Browser** (`/capsules`): Search, filter, and explore all data assets with advanced filtering
- **Capsule Detail View** (`/capsules/[urn]`): Comprehensive metadata, columns, lineage visualization, and violations
- **Interactive Lineage** (`/lineage`): React Flow-based graph with capsule selection and depth control
- **PII Compliance** (`/compliance`): Inventory, exposure detection, and lineage tracing
- **Conformance Scoring** (`/conformance`): Real-time monitoring with violation tracking
- **Impact Analysis** (`/impact`): Assess downstream effects with depth configuration
- **Redundancy Detection** (`/redundancy`): Find similar capsules and duplicate candidates
- **Domains** (`/domains`): Browse and manage business domains
- **Data Products** (`/products`): Manage data products with SLO tracking
- **Tags** (`/tags`): Tag management and exploration
- **Settings** (`/settings`): Centralized configuration for domains, tags, products, rules, and system info
- **Reports** (`/reports`): Generate and download reports in JSON, CSV, or HTML

### Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local and set NEXT_PUBLIC_API_URL and NEXT_PUBLIC_API_KEY

# Run development server
npm run dev

# Build for production
npm run build
npm start
```

For detailed documentation, see [docs/DASHBOARD.md](docs/DASHBOARD.md).

## Project Structure

```
data-capsule-server/
├── backend/
│   ├── src/
│   │   ├── api/           # FastAPI routers and endpoints
│   │   ├── services/      # Business logic
│   │   ├── repositories/  # Data access layer
│   │   ├── parsers/       # Metadata parsers (dbt, etc.)
│   │   ├── models/        # SQLAlchemy models
│   │   └── cli/           # Command-line interface
│   ├── tests/
│   ├── alembic/           # Database migrations
│   └── config/
│       └── rules/         # Conformance rules (YAML)
├── frontend/              # React web dashboard
│   ├── src/
│   │   ├── app/           # Next.js pages (App Router)
│   │   ├── components/    # React components
│   │   └── lib/           # API client, hooks, utilities
│   ├── public/            # Static assets
│   └── .env.local         # Frontend environment variables
├── docker/
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   └── init-db.sql
├── data/                  # Mount point for dbt artifacts
├── docs/
│   ├── specs/             # Product specification
│   ├── design_docs/       # Technical design documents
│   └── DASHBOARD.md       # Web dashboard user guide
└── Makefile
```

## API Endpoints

### Core Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/health` | Health check |
| `POST /api/v1/ingest/dbt` | Ingest dbt artifacts |
| `GET /api/v1/capsules` | List data capsules |
| `GET /api/v1/capsules/{urn}/lineage` | Get capsule lineage |
| `GET /api/v1/columns` | List columns |
| `GET /api/v1/compliance/pii-inventory` | PII inventory report |
| `GET /api/v1/compliance/pii-exposure` | PII exposure analysis |
| `GET /api/v1/conformance/score` | Conformance score |
| `GET /api/v1/conformance/violations` | List violations |

### Data Products

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/products` | List all data products |
| `POST /api/v1/products` | Create a data product |
| `GET /api/v1/products/{id}` | Get data product details |
| `POST /api/v1/products/{id}/capsules/{capsule_id}` | Add capsule to product (PART_OF edge) |
| `GET /api/v1/products/{id}/slo-status` | Get SLO compliance status |

### Tag Management

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/tags` | List all tags |
| `POST /api/v1/tags` | Create a tag |
| `POST /api/v1/tags/capsules/{id}/{tag_id}` | Tag a capsule (TAGGED_WITH edge) |
| `POST /api/v1/tags/columns/{id}/{tag_id}` | Tag a column |
| `GET /api/v1/tags/{tag_id}/capsules` | Get capsules with tag |

### Graph Export

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/graph/formats` | List available export formats |
| `GET /api/v1/graph/export` | Export full property graph |
| `GET /api/v1/graph/export/lineage/{urn}` | Export lineage subgraph |

API documentation available at:
- Swagger UI: http://localhost:8001/api/v1/docs
- ReDoc: http://localhost:8001/api/v1/redoc

### Graph Export Formats

| Format | Use Cases |
|--------|----------|
| `graphml` | yEd, Gephi, Cytoscape, NetworkX |
| `dot` | Graphviz visualization |
| `cypher` | Neo4j, Amazon Neptune import |
| `mermaid` | GitHub, GitLab, Notion diagrams |
| `json-ld` | Semantic web, RDF tools |

## CLI Usage

```bash
# Ingest dbt project
make ingest-dbt MANIFEST=./data/jaffle_shop/manifest.json

# Show PII inventory
make pii-inventory

# Check conformance score
make conformance-score
```

## Development

### Local Development Setup

```bash
# Install dependencies
cd backend
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/ -v

# Run linting
ruff check src/ tests/

# Run type checking
mypy src/
```

### Running Tests

```bash
# All tests
make test

# With coverage
make test-cov

# Unit tests only
make test-unit
```

### Database Migrations

```bash
# Apply migrations
make migrate

# Create new migration
make migrate-new MSG="Add new column"

# Rollback
make migrate-down
```

## Configuration

Environment variables (see `backend/.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://dab:dab_password@localhost:5433/dab` |
| `API_KEY` | API authentication key | `dev-api-key-change-in-prod` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ENVIRONMENT` | Environment name | `development` |
| `MAX_LINEAGE_DEPTH` | Maximum lineage traversal depth | `10` |

## Documentation

- [User Guide](docs/USER_GUIDE.md) - CLI and API usage guide
- [Runbook](docs/RUNBOOK.md) - Operational guide for running the service
- [Product Specification](docs/specs/product_specification.md)
- [System Architecture](docs/design_docs/system_architecture.md)
- [Database Schema](docs/design_docs/database_schema.md)
- [API Specification](docs/design_docs/api_specification.md)
- [Component Design](docs/design_docs/component_design.md)
- [Deployment Guide](docs/design_docs/deployment.md)
- [Implementation Gaps](docs/IMPLEMENTATION_GAPS.md) - Feature status tracking

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0
- **Database**: PostgreSQL 15
- **CLI**: Typer
- **Testing**: pytest, pytest-asyncio
- **Deployment**: Docker, Docker Compose

## License

MIT
