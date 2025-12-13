# Data Architecture Brain

A read-only architecture intelligence platform that ingests metadata from data infrastructure sources, constructs a unified graph representation of your data landscape, and provides intelligent insights for data governance, architecture conformance, and sensitive data tracking.

## Features

- **Metadata Ingestion**: Parse dbt artifacts (manifest.json, catalog.json) with support for future integrations (Snowflake, BigQuery, Databricks)
- **PII Lineage Tracking**: Trace sensitive data through transformation pipelines, detect exposure risks
- **Architecture Conformance**: Validate data models against defined standards (Medallion, naming conventions, etc.)
- **Graph-Based Analysis**: Query lineage, impact analysis, and redundancy detection

## Quick Start

### Prerequisites

- Docker Desktop 4.0+
- Docker Compose 2.0+
- Make (optional, for convenience commands)

### Start Services

```bash
# Clone the repository
git clone <repository-url>
cd data-arch-brain

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

## Project Structure

```
data-arch-brain/
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
├── docker/
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   └── init-db.sql
├── data/                  # Mount point for dbt artifacts
├── docs/
│   ├── specs/             # Product specification
│   └── design_docs/       # Technical design documents
└── Makefile
```

## API Endpoints

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

API documentation available at:
- Swagger UI: http://localhost:8001/api/v1/docs
- ReDoc: http://localhost:8001/api/v1/redoc

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

- [Product Specification](docs/specs/product_specification.md)
- [System Architecture](docs/design_docs/system_architecture.md)
- [Database Schema](docs/design_docs/database_schema.md)
- [API Specification](docs/design_docs/api_specification.md)
- [Component Design](docs/design_docs/component_design.md)
- [Deployment Guide](docs/design_docs/deployment.md)

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0
- **Database**: PostgreSQL 15
- **CLI**: Typer
- **Testing**: pytest, pytest-asyncio
- **Deployment**: Docker, Docker Compose

## License

MIT
