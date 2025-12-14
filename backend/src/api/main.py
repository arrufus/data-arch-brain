"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import APIKeyAuthMiddleware
from src.api.exceptions import register_exception_handlers
from src.api.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from src.api.rate_limit import configure_rate_limiting
from src.api.routers import capsules, columns, compliance, conformance, domains, graph, health, ingest, products, reports, tags, violations
from src.cache import close_cache, init_cache
from src.config import get_settings, validate_config
from src.database import close_db, init_db, engine
from src.logging_config import configure_logging, get_logger
from src.metrics import configure_prometheus_metrics

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    configure_logging()
    logger.info("Starting Data Architecture Brain", environment=settings.environment)
    
    # Validate configuration (strict mode in production)
    validate_config(settings, strict=settings.is_production)
    logger.info("Configuration validated")
    
    await init_db()
    logger.info("Database initialized")
    await init_cache()
    logger.info("Cache initialized")

    # Initialize distributed tracing if enabled
    if settings.tracing_enabled:
        from src.tracing import setup_tracing
        setup_tracing(
            app=app,
            service_name=settings.tracing_service_name,
            otlp_endpoint=settings.tracing_otlp_endpoint,
            enable_console_export=settings.tracing_console_export,
            engine=engine,
        )
        logger.info("Distributed tracing initialized", 
                   endpoint=settings.tracing_otlp_endpoint)

    yield

    # Shutdown
    logger.info("Shutting down Data Architecture Brain")

    # Shutdown tracing
    if settings.tracing_enabled:
        from src.tracing import shutdown_tracing
        shutdown_tracing()
        logger.info("Tracing shutdown complete")

    await close_cache()
    logger.info("Cache connections closed")
    await close_db()
    logger.info("Database connections closed")


API_DESCRIPTION = """
# Data Architecture Brain API

A read-only architecture intelligence platform for analyzing your data landscape.

## Features

- **Metadata Ingestion**: Ingest metadata from dbt projects (manifest.json, catalog.json)
- **Data Capsules**: Browse and search your data assets (models, sources, seeds)
- **PII Compliance**: Track sensitive data across your architecture
- **Architecture Conformance**: Validate against best practices (Medallion, dbt conventions)
- **Lineage Tracking**: Trace data flow at model and column level
- **Reports**: Generate downloadable reports in JSON, CSV, or HTML format

## Core Concepts

- **Data Capsule**: An atomic unit representing a data asset (table, view, model)
- **URN**: Uniform Resource Name uniquely identifying each asset
- **Conformance Rule**: A validation rule checking architecture best practices
- **PII**: Personally Identifiable Information that requires special handling

## Authentication

API key authentication is required for most endpoints. Include your API key in the `X-API-Key` header.

Exempt endpoints (no auth required):
- Health checks (`/health`, `/health/live`, `/health/ready`)
- Documentation (`/docs`, `/redoc`, `/openapi.json`)

## Rate Limits

Rate limits are enforced per API key (or IP address if no key provided):
- **Default**: 100 requests/minute
- **Expensive operations** (conformance evaluation): 10 requests/minute

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in window
- `X-RateLimit-Reset`: Time until limit resets
"""

OPENAPI_TAGS = [
    {
        "name": "health",
        "description": "Health check endpoints for monitoring"
    },
    {
        "name": "ingestion",
        "description": "Metadata ingestion from dbt and other sources"
    },
    {
        "name": "capsules",
        "description": "Data Capsule (data asset) operations - browse, search, and inspect"
    },
    {
        "name": "columns",
        "description": "Column-level operations including lineage"
    },
    {
        "name": "compliance",
        "description": "PII compliance - inventory, exposure detection, and lineage tracing"
    },
    {
        "name": "conformance",
        "description": "Architecture conformance - rules, scoring, and violations"
    },
    {
        "name": "violations",
        "description": "Conformance violation management - list, acknowledge, resolve"
    },
    {
        "name": "domains",
        "description": "Business domain organization and ownership"
    },
    {
        "name": "products",
        "description": "Data Products - logical groupings of capsules with SLOs"
    },
    {
        "name": "tags",
        "description": "Tag management - create, search, and associate tags with capsules and columns"
    },
    {
        "name": "graph",
        "description": "Graph export - export property graph in GraphML, DOT, Cypher, Mermaid, and JSON-LD formats"
    },
    {
        "name": "reports",
        "description": "Report generation in various formats (JSON, CSV, HTML)"
    },
]


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description=API_DESCRIPTION,
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
        contact={
            "name": "Data Architecture Team",
            "email": "data-arch@example.com",
        },
        license_info={
            "name": "MIT",
        },
    )

    # Configure middleware (order matters - first added = last executed)
    # Security headers (runs last)
    app.add_middleware(SecurityHeadersMiddleware)

    # API Key Authentication (runs after logging, before handlers)
    if settings.auth_required:
        app.add_middleware(APIKeyAuthMiddleware, settings=settings)
        logger.info("API key authentication enabled")

    # Request logging (runs early to capture all requests)
    app.add_middleware(RequestLoggingMiddleware)

    # CORS (runs first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Configure rate limiting
    configure_rate_limiting(app)

    # Configure Prometheus metrics
    configure_prometheus_metrics(app)

    # Include routers
    app.include_router(health.router, prefix=settings.api_prefix, tags=["health"])
    app.include_router(ingest.router, prefix=settings.api_prefix, tags=["ingestion"])
    app.include_router(capsules.router, prefix=settings.api_prefix, tags=["capsules"])
    app.include_router(columns.router, prefix=settings.api_prefix, tags=["columns"])
    app.include_router(compliance.router, prefix=settings.api_prefix, tags=["compliance"])
    app.include_router(conformance.router, prefix=settings.api_prefix, tags=["conformance"])
    app.include_router(violations.router, prefix=settings.api_prefix, tags=["violations"])
    app.include_router(domains.router, prefix=settings.api_prefix, tags=["domains"])
    app.include_router(products.router, prefix=settings.api_prefix, tags=["products"])
    app.include_router(tags.router, prefix=settings.api_prefix, tags=["tags"])
    app.include_router(tags.capsule_tags_router, prefix=settings.api_prefix, tags=["tags"])
    app.include_router(tags.column_tags_router, prefix=settings.api_prefix, tags=["tags"])
    app.include_router(graph.router, prefix=settings.api_prefix, tags=["graph"])
    app.include_router(reports.router, prefix=settings.api_prefix, tags=["reports"])

    # Register exception handlers
    register_exception_handlers(app)

    return app


# Create the app instance
app = create_app()
