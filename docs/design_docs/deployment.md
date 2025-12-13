# Data Architecture Brain - Deployment Guide

**Version**: 1.0
**Status**: Draft
**Last Updated**: December 2024

---

## Table of Contents

1. [Overview](#1-overview)
2. [Local Development Setup](#2-local-development-setup)
3. [Docker Configuration](#3-docker-configuration)
4. [Environment Configuration](#4-environment-configuration)
5. [Database Migrations](#5-database-migrations)
6. [Health Checks & Monitoring](#6-health-checks--monitoring)
7. [Production Considerations](#7-production-considerations)

---

## 1. Overview

### 1.1 Deployment Targets

| Environment | Technology | Purpose |
|-------------|------------|---------|
| **Local Dev** | Docker Compose | Development and testing |
| **CI/CD** | Docker Compose | Automated testing |
| **Production** | Docker/Kubernetes | Future consideration |

### 1.2 Component Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Docker Compose Environment                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     docker-compose.yml                           │   │
│  │                                                                   │   │
│  │  ┌───────────────┐              ┌───────────────┐               │   │
│  │  │   dab-api     │              │   postgres    │               │   │
│  │  │               │              │               │               │   │
│  │  │  FastAPI      │─────────────▶│  PostgreSQL   │               │   │
│  │  │  Port: 8001   │              │  Port: 5432   │               │   │
│  │  │               │              │               │               │   │
│  │  └───────────────┘              └───────────────┘               │   │
│  │                                                                   │   │
│  │  Volumes:                                                        │   │
│  │  • ./data:/app/data (dbt artifacts)                             │   │
│  │  • postgres_data (persistent DB)                                 │   │
│  │                                                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Local Development Setup

### 2.1 Prerequisites

- Docker Desktop 4.0+
- Docker Compose 2.0+
- Python 3.11+ (for CLI development)
- uv or poetry (Python package manager)

### 2.2 Project Structure

```
data-arch-brain/
├── backend/
│   ├── src/
│   │   ├── api/                 # FastAPI routers
│   │   ├── services/            # Business logic
│   │   ├── repositories/        # Data access
│   │   ├── parsers/            # Metadata parsers
│   │   ├── models/             # Domain models
│   │   └── cli/                # CLI commands
│   ├── tests/
│   ├── alembic/                # Database migrations
│   ├── config/
│   │   └── rules/              # Conformance rules
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── alembic.ini
├── docker/
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   └── docker-compose.test.yml
├── data/                       # Mount point for dbt artifacts
├── docs/
└── README.md
```

### 2.3 Quick Start

```bash
# Clone and enter directory
cd data-arch-brain

# Start services
docker compose -f docker/docker-compose.yml up -d

# Run migrations
docker compose exec dab-api alembic upgrade head

# Verify API is running
curl http://localhost:8001/api/v1/health

# Ingest sample dbt project
docker compose exec dab-api dab ingest dbt \
    --manifest /app/data/jaffle_shop/manifest.json \
    --catalog /app/data/jaffle_shop/catalog.json

# Check conformance
docker compose exec dab-api dab conformance score
```

---

## 3. Docker Configuration

### 3.1 docker-compose.yml

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  dab-api:
    build:
      context: ../backend
      dockerfile: Dockerfile
    container_name: dab-api
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://dab:dab_password@postgres:5432/dab
      - LOG_LEVEL=INFO
      - API_KEY=dev-api-key-change-in-prod
      - ENVIRONMENT=development
    volumes:
      - ../data:/app/data:ro
      - ../backend/config:/app/config:ro
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    container_name: dab-postgres
    environment:
      - POSTGRES_USER=dab
      - POSTGRES_PASSWORD=dab_password
      - POSTGRES_DB=dab
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
    ports:
      - "5433:5432"  # Different port to avoid conflicts
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dab -d dab"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
    name: dab_postgres_data

networks:
  default:
    name: dab-network
```

### 3.2 Database Initialization Script

```sql
-- docker/init-db.sql
-- Create the dab schema
CREATE SCHEMA IF NOT EXISTS dab;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA dab TO dab;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA dab TO dab;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA dab TO dab;

-- Set default search path
ALTER USER dab SET search_path TO dab, public;
```

### 3.3 Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
FROM base as builder

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
RUN uv pip install --system --no-cache -r pyproject.toml

# Production image
FROM base as production

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY config/ ./config/

# Create non-root user
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run the application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.4 Development Compose Override

```yaml
# docker/docker-compose.dev.yml
version: '3.8'

services:
  dab-api:
    build:
      context: ../backend
      dockerfile: Dockerfile
      target: base  # Use base image without optimizations
    volumes:
      - ../backend/src:/app/src:rw  # Hot reload
      - ../backend/tests:/app/tests:ro
      - ../data:/app/data:ro
      - ../backend/config:/app/config:ro
    environment:
      - LOG_LEVEL=DEBUG
      - ENVIRONMENT=development
      - RELOAD=true
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

  # Add pgAdmin for development
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: dab-pgadmin
    environment:
      - PGADMIN_DEFAULT_EMAIL=admin@dab.local
      - PGADMIN_DEFAULT_PASSWORD=admin
    ports:
      - "5050:80"
    depends_on:
      - postgres
    profiles:
      - tools
```

### 3.5 Test Compose Configuration

```yaml
# docker/docker-compose.test.yml
version: '3.8'

services:
  dab-api:
    build:
      context: ../backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql+asyncpg://dab:dab_password@postgres:5432/dab_test
      - LOG_LEVEL=WARNING
      - ENVIRONMENT=test
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=dab
      - POSTGRES_PASSWORD=dab_password
      - POSTGRES_DB=dab_test
    tmpfs:
      - /var/lib/postgresql/data  # Use tmpfs for speed
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dab -d dab_test"]
      interval: 5s
      timeout: 3s
      retries: 5

  test-runner:
    build:
      context: ../backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql+asyncpg://dab:dab_password@postgres:5432/dab_test
      - ENVIRONMENT=test
    command: pytest tests/ -v --cov=src --cov-report=term-missing
    depends_on:
      - dab-api
      - postgres
```

---

## 4. Environment Configuration

### 4.1 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `API_KEY` | Yes | - | API authentication key |
| `LOG_LEVEL` | No | INFO | Logging level |
| `ENVIRONMENT` | No | production | Environment name |
| `CORS_ORIGINS` | No | * | Allowed CORS origins |
| `MAX_LINEAGE_DEPTH` | No | 10 | Maximum lineage traversal depth |

### 4.2 Configuration File

```python
# backend/src/config.py
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # API
    api_key: str
    api_prefix: str = "/api/v1"
    cors_origins: List[str] = ["*"]

    # Application
    environment: str = "production"
    log_level: str = "INFO"
    debug: bool = False

    # Features
    max_lineage_depth: int = 10
    pii_detection_enabled: bool = True
    conformance_on_ingest: bool = True

    # Paths
    rules_path: str = "/app/config/rules"
    templates_path: str = "/app/src/templates"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### 4.3 Sample .env File

```bash
# .env.example
# Database
DATABASE_URL=postgresql+asyncpg://dab:dab_password@localhost:5433/dab

# API Security
API_KEY=your-secure-api-key-here

# Application
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DEBUG=true

# Features
MAX_LINEAGE_DEPTH=10
PII_DETECTION_ENABLED=true
CONFORMANCE_ON_INGEST=true
```

---

## 5. Database Migrations

### 5.1 Alembic Configuration

```ini
# backend/alembic.ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -q

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### 5.2 Migration Commands

```bash
# Create a new migration
docker compose exec dab-api alembic revision --autogenerate -m "Description of changes"

# Apply all migrations
docker compose exec dab-api alembic upgrade head

# Rollback one migration
docker compose exec dab-api alembic downgrade -1

# Show current revision
docker compose exec dab-api alembic current

# Show migration history
docker compose exec dab-api alembic history
```

### 5.3 Initial Migration Script

```python
# backend/alembic/versions/001_initial_schema.py
"""Initial schema for Data Architecture Brain

Revision ID: 001
Revises:
Create Date: 2024-12-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create schema
    op.execute('CREATE SCHEMA IF NOT EXISTS dab')

    # Create source_systems table
    op.create_table(
        'source_systems',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('connection_info', postgresql.JSONB, server_default='{}'),
        sa.Column('meta', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema='dab'
    )

    # Create owners table
    op.create_table(
        'owners',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('owner_type', sa.String(50), nullable=False, server_default='team'),
        sa.Column('email', sa.String(255)),
        sa.Column('slack_channel', sa.String(100)),
        sa.Column('meta', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema='dab'
    )

    # Create domains table
    op.create_table(
        'domains',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.domains.id')),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.owners.id')),
        sa.Column('meta', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema='dab'
    )

    # Create ingestion_jobs table
    op.create_table(
        'ingestion_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_name', sa.String(255)),
        sa.Column('status', sa.String(20), nullable=False, server_default='running'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('stats', postgresql.JSONB, server_default='{}'),
        sa.Column('config', postgresql.JSONB, server_default='{}'),
        sa.Column('error_message', sa.Text),
        sa.Column('error_details', postgresql.JSONB),
        schema='dab'
    )

    # Create capsules table
    op.create_table(
        'capsules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('urn', sa.String(500), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('capsule_type', sa.String(50), nullable=False),
        sa.Column('source_system_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.source_systems.id')),
        sa.Column('database_name', sa.String(255)),
        sa.Column('schema_name', sa.String(255)),
        sa.Column('domain_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.domains.id')),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.owners.id')),
        sa.Column('layer', sa.String(50)),
        sa.Column('materialization', sa.String(50)),
        sa.Column('description', sa.Text),
        sa.Column('meta', postgresql.JSONB, server_default='{}'),
        sa.Column('tags', postgresql.JSONB, server_default='[]'),
        sa.Column('has_tests', sa.Boolean, server_default='false'),
        sa.Column('test_count', sa.Integer, server_default='0'),
        sa.Column('doc_coverage', sa.Float, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('ingestion_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.ingestion_jobs.id')),
        schema='dab'
    )

    # Create columns table
    op.create_table(
        'columns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('urn', sa.String(500), nullable=False, unique=True),
        sa.Column('capsule_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.capsules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('data_type', sa.String(100)),
        sa.Column('ordinal_position', sa.Integer),
        sa.Column('is_nullable', sa.Boolean, server_default='true'),
        sa.Column('semantic_type', sa.String(50)),
        sa.Column('pii_type', sa.String(50)),
        sa.Column('pii_detected_by', sa.String(50)),
        sa.Column('description', sa.Text),
        sa.Column('meta', postgresql.JSONB, server_default='{}'),
        sa.Column('tags', postgresql.JSONB, server_default='[]'),
        sa.Column('stats', postgresql.JSONB, server_default='{}'),
        sa.Column('has_tests', sa.Boolean, server_default='false'),
        sa.Column('test_count', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema='dab'
    )

    # Create capsule_lineage table
    op.create_table(
        'capsule_lineage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_urn', sa.String(500), nullable=False),
        sa.Column('target_urn', sa.String(500), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.capsules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.capsules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('edge_type', sa.String(50), nullable=False, server_default='flows_to'),
        sa.Column('transformation', sa.String(50)),
        sa.Column('meta', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('ingestion_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.ingestion_jobs.id')),
        schema='dab'
    )

    # Create column_lineage table
    op.create_table(
        'column_lineage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_urn', sa.String(500), nullable=False),
        sa.Column('target_urn', sa.String(500), nullable=False),
        sa.Column('source_column_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.columns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_column_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.columns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('transformation_type', sa.String(50)),
        sa.Column('transformation_expr', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('ingestion_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.ingestion_jobs.id')),
        schema='dab'
    )

    # Create rules table
    op.create_table(
        'rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('rule_id', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('severity', sa.String(20), nullable=False, server_default='warning'),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('rule_set', sa.String(50)),
        sa.Column('scope', sa.String(50), nullable=False),
        sa.Column('definition', postgresql.JSONB, nullable=False),
        sa.Column('enabled', sa.Boolean, server_default='true'),
        sa.Column('meta', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema='dab'
    )

    # Create violations table
    op.create_table(
        'violations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.rules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('capsule_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.capsules.id', ondelete='CASCADE')),
        sa.Column('column_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.columns.id', ondelete='CASCADE')),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('details', postgresql.JSONB, server_default='{}'),
        sa.Column('status', sa.String(20), server_default='open'),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('resolved_by', sa.String(255)),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('ingestion_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dab.ingestion_jobs.id')),
        schema='dab'
    )

    # Create indexes
    op.create_index('idx_capsules_urn', 'capsules', ['urn'], schema='dab', unique=True)
    op.create_index('idx_capsules_layer', 'capsules', ['layer'], schema='dab')
    op.create_index('idx_capsules_type', 'capsules', ['capsule_type'], schema='dab')
    op.create_index('idx_capsules_domain', 'capsules', ['domain_id'], schema='dab')
    op.create_index('idx_capsules_tags', 'capsules', ['tags'], schema='dab', postgresql_using='gin')

    op.create_index('idx_columns_urn', 'columns', ['urn'], schema='dab', unique=True)
    op.create_index('idx_columns_capsule', 'columns', ['capsule_id'], schema='dab')
    op.create_index('idx_columns_semantic_type', 'columns', ['semantic_type'], schema='dab')
    op.create_index('idx_columns_pii_type', 'columns', ['pii_type'], schema='dab')

    op.create_index('idx_capsule_lineage_source', 'capsule_lineage', ['source_id'], schema='dab')
    op.create_index('idx_capsule_lineage_target', 'capsule_lineage', ['target_id'], schema='dab')

    op.create_index('idx_violations_capsule', 'violations', ['capsule_id'], schema='dab')
    op.create_index('idx_violations_rule', 'violations', ['rule_id'], schema='dab')
    op.create_index('idx_violations_severity', 'violations', ['severity'], schema='dab')


def downgrade():
    # Drop tables in reverse order
    op.drop_table('violations', schema='dab')
    op.drop_table('rules', schema='dab')
    op.drop_table('column_lineage', schema='dab')
    op.drop_table('capsule_lineage', schema='dab')
    op.drop_table('columns', schema='dab')
    op.drop_table('capsules', schema='dab')
    op.drop_table('ingestion_jobs', schema='dab')
    op.drop_table('domains', schema='dab')
    op.drop_table('owners', schema='dab')
    op.drop_table('source_systems', schema='dab')

    # Drop schema
    op.execute('DROP SCHEMA dab')
```

---

## 6. Health Checks & Monitoring

### 6.1 Health Check Endpoint

```python
# backend/src/api/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime

from src.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check including database connectivity."""
    try:
        # Check database connection
        await db.execute(text("SELECT 1"))

        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": "ok",
            }
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": f"error: {str(e)}",
            }
        }


@router.get("/health/live")
async def liveness_check():
    """Liveness check - is the service running."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }
```

### 6.2 Logging Configuration

```python
# backend/src/logging_config.py
import logging
import sys
import structlog
from src.config import get_settings


def configure_logging():
    settings = get_settings()

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if settings.environment == "production"
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )
```

---

## 7. Production Considerations

### 7.1 Security Checklist

- [ ] Change default API key
- [ ] Enable HTTPS/TLS
- [ ] Restrict CORS origins
- [ ] Use secrets management for credentials
- [ ] Enable database connection encryption
- [ ] Set up network policies/firewalls
- [ ] Regular security updates

### 7.2 Performance Tuning

```yaml
# Production docker-compose overrides
services:
  dab-api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    environment:
      - DATABASE_POOL_SIZE=10
      - DATABASE_MAX_OVERFLOW=20
      - WORKERS=4

  postgres:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
    command:
      - "postgres"
      - "-c"
      - "shared_buffers=1GB"
      - "-c"
      - "effective_cache_size=3GB"
      - "-c"
      - "max_connections=200"
```

### 7.3 Backup Strategy

```bash
#!/bin/bash
# scripts/backup.sh

# Backup database
docker compose exec -T postgres pg_dump -U dab -Fc dab > backup_$(date +%Y%m%d_%H%M%S).dump

# Restore database
# docker compose exec -T postgres pg_restore -U dab -d dab < backup_file.dump
```

---

## Appendix: Makefile

```makefile
# Makefile
.PHONY: help up down logs test migrate shell

help:
	@echo "Available commands:"
	@echo "  make up        - Start all services"
	@echo "  make down      - Stop all services"
	@echo "  make logs      - View logs"
	@echo "  make test      - Run tests"
	@echo "  make migrate   - Run database migrations"
	@echo "  make shell     - Open shell in API container"

up:
	docker compose -f docker/docker-compose.yml up -d

up-dev:
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d

down:
	docker compose -f docker/docker-compose.yml down

logs:
	docker compose -f docker/docker-compose.yml logs -f

test:
	docker compose -f docker/docker-compose.test.yml run --rm test-runner

migrate:
	docker compose exec dab-api alembic upgrade head

shell:
	docker compose exec dab-api /bin/bash

clean:
	docker compose -f docker/docker-compose.yml down -v --remove-orphans
```

---

*End of Deployment Guide*
