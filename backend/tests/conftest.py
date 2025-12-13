"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.main import app
from src.config import Settings, get_settings
from src.database import Base, get_db


# Test database URL (use in-memory SQLite for unit tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Test API key for authenticated requests
TEST_API_KEY = "test-api-key-12345"


def get_test_settings() -> Settings:
    """Override settings for testing."""
    return Settings(
        database_url=TEST_DATABASE_URL,
        api_keys=[TEST_API_KEY],
        auth_enabled=False,  # Disable auth for most tests
        rate_limit_enabled=False,  # Disable rate limiting for tests
        environment="test",
        log_level="WARNING",
    )


def get_test_settings_with_auth() -> Settings:
    """Override settings for testing with authentication enabled."""
    return Settings(
        database_url=TEST_DATABASE_URL,
        api_keys=[TEST_API_KEY],
        auth_enabled=True,
        rate_limit_enabled=False,
        environment="test",
        log_level="WARNING",
    )


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def _create_schema_tables(connection):
    """Create tables without schema prefix for SQLite compatibility."""
    # For SQLite, we create tables without the schema prefix
    # This is handled by SQLAlchemy when dialect is sqlite
    for table in Base.metadata.sorted_tables:
        # Remove schema from table for SQLite
        original_schema = table.schema
        table.schema = None
        table.create(connection, checkfirst=True)
        table.schema = original_schema


def _drop_schema_tables(connection):
    """Drop tables without schema prefix for SQLite compatibility."""
    for table in reversed(Base.metadata.sorted_tables):
        original_schema = table.schema
        table.schema = None
        table.drop(connection, checkfirst=True)
        table.schema = original_schema


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(_create_schema_tables)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(_drop_schema_tables)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client without authentication."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = get_test_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with authentication enabled."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = get_test_settings_with_auth

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-API-Key": TEST_API_KEY},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def api_key() -> str:
    """Return the test API key."""
    return TEST_API_KEY


@pytest.fixture
def sample_capsule_data() -> dict[str, Any]:
    """Sample capsule data for testing."""
    return {
        "urn": "urn:dab:dbt:model:test_project.staging:stg_customers",
        "name": "stg_customers",
        "capsule_type": "model",
        "layer": "silver",
        "schema_name": "staging",
        "description": "Staged customer data",
        "materialization": "view",
        "tags": ["customer", "staging"],
        "meta": {"unique_id": "model.test_project.stg_customers"},
    }


@pytest.fixture
def sample_column_data() -> dict[str, Any]:
    """Sample column data for testing."""
    return {
        "urn": "urn:dab:dbt:column:test_project.staging:stg_customers.email",
        "name": "email",
        "data_type": "VARCHAR",
        "ordinal_position": 1,
        "semantic_type": "pii",
        "pii_type": "email",
        "pii_detected_by": "pattern",
        "description": "Customer email address",
    }
