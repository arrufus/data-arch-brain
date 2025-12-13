# Data Architecture Brain - Backend

A read-only architecture intelligence platform for analyzing data landscapes, tracking PII lineage, and detecting architecture anti-patterns.

## Features

- **Metadata Ingestion**: Parse and normalize metadata from various data infrastructure sources
  - dbt (manifest.json, catalog.json)
  - More sources coming soon (Snowflake, Databricks, OpenLineage)

- **Data Capsule Model**: Unified representation of data assets with URN-based identification

- **PII Detection**: Automatic detection of personally identifiable information through:
  - Explicit metadata tags
  - Column name pattern matching
  - Configurable detection rules

- **Architecture Layer Inference**: Automatic classification into medallion architecture layers (Bronze/Silver/Gold)

- **Lineage Tracking**: Build and query data lineage graphs

- **Conformance Rules**: Define and check architecture conformance rules

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose (optional)

### Installation

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn src.api.main:app --reload
```

### Using Docker

```bash
# From the project root
make up

# Run migrations
make migrate

# View logs
make logs
```

## Project Structure

```
backend/
├── src/
│   ├── api/           # FastAPI application and routers
│   ├── cli/           # Typer CLI commands
│   ├── models/        # SQLAlchemy ORM models
│   ├── parsers/       # Metadata parsers (dbt, etc.)
│   ├── repositories/  # Data access layer
│   ├── services/      # Business logic
│   └── config.py      # Application configuration
├── alembic/           # Database migrations
├── tests/             # Test suite
└── pyproject.toml     # Project configuration
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/parsers/test_dbt_parser.py -v
```

### Code Quality

```bash
# Format code
black src tests
isort src tests

# Lint
ruff check src tests

# Type check
mypy src
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

MIT
