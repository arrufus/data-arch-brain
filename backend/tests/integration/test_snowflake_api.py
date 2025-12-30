"""Integration tests for Snowflake ingestion API endpoint."""

import os
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from src.api.main import app
from src.services.ingestion import IngestionResult, IngestionStats, IngestionStatus


@pytest.mark.asyncio
async def test_snowflake_ingest_with_password(test_db):
    """Test Snowflake ingestion endpoint with password authentication."""
    # Mock the ingestion service
    with patch("src.api.routers.ingest.IngestionService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service

        # Mock successful ingestion result
        mock_result = IngestionResult(
            job_id="12345678-1234-1234-1234-123456789abc",
            status=IngestionStatus.COMPLETED,
            source_type="snowflake",
            source_name="PROD, ANALYTICS",
            stats=IngestionStats(
                capsules_created=10,
                capsules_updated=5,
                columns_created=100,
                columns_updated=20,
                edges_created=15,
            ),
        )
        mock_service.ingest_snowflake = AsyncMock(return_value=mock_result)

        # Set environment variable
        os.environ["SNOWFLAKE_PASSWORD"] = "test-password"

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/ingest/snowflake",
                json={
                    "account": "test-account",
                    "user": "test_user",
                    "warehouse": "METADATA_WH",
                    "databases": ["PROD", "ANALYTICS"],
                    "enable_lineage": False,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["source_type"] == "snowflake"
        assert data["source_name"] == "PROD, ANALYTICS"
        assert data["stats"]["capsules_created"] == 10
        assert data["stats"]["columns_created"] == 100

        # Verify service was called correctly
        mock_service.ingest_snowflake.assert_called_once()
        call_kwargs = mock_service.ingest_snowflake.call_args.kwargs
        assert call_kwargs["account"] == "test-account"
        assert call_kwargs["user"] == "test_user"
        assert call_kwargs["password"] == "test-password"
        assert call_kwargs["databases"] == ["PROD", "ANALYTICS"]


@pytest.mark.asyncio
async def test_snowflake_ingest_with_key_pair(test_db):
    """Test Snowflake ingestion endpoint with key-pair authentication."""
    with patch("src.api.routers.ingest.IngestionService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service

        mock_result = IngestionResult(
            job_id="12345678-1234-1234-1234-123456789abc",
            status=IngestionStatus.COMPLETED,
            source_type="snowflake",
            source_name="PROD",
            stats=IngestionStats(capsules_created=5),
        )
        mock_service.ingest_snowflake = AsyncMock(return_value=mock_result)

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/ingest/snowflake",
                json={
                    "account": "test-account",
                    "user": "test_user",
                    "private_key_path": "/path/to/key.p8",
                    "databases": ["PROD"],
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

        # Verify key-pair path was passed
        call_kwargs = mock_service.ingest_snowflake.call_args.kwargs
        assert call_kwargs["private_key_path"] == "/path/to/key.p8"
        assert call_kwargs["password"] is None


@pytest.mark.asyncio
async def test_snowflake_ingest_missing_credentials(test_db):
    """Test Snowflake ingestion fails when no credentials provided."""
    # Ensure no password in environment
    if "SNOWFLAKE_PASSWORD" in os.environ:
        del os.environ["SNOWFLAKE_PASSWORD"]

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ingest/snowflake",
            json={
                "account": "test-account",
                "user": "test_user",
                # No password and no private_key_path
            },
        )

    assert response.status_code == 400  # or 422 depending on exception handling
    assert "password" in response.text.lower() or "environment" in response.text.lower()


@pytest.mark.asyncio
async def test_snowflake_ingest_with_lineage_options(test_db):
    """Test Snowflake ingestion with lineage enabled."""
    with patch("src.api.routers.ingest.IngestionService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service

        mock_result = IngestionResult(
            job_id="12345678-1234-1234-1234-123456789abc",
            status=IngestionStatus.COMPLETED,
            source_type="snowflake",
            source_name="PROD",
            stats=IngestionStats(
                capsules_created=10,
                edges_created=25,
            ),
        )
        mock_service.ingest_snowflake = AsyncMock(return_value=mock_result)

        os.environ["SNOWFLAKE_PASSWORD"] = "test-password"

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/ingest/snowflake",
                json={
                    "account": "test-account",
                    "user": "test_user",
                    "databases": ["PROD"],
                    "enable_lineage": True,
                    "lineage_lookback_days": 14,
                    "use_account_usage": True,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["stats"]["edges_created"] == 25

        # Verify lineage options were passed
        call_kwargs = mock_service.ingest_snowflake.call_args.kwargs
        assert call_kwargs["enable_lineage"] is True
        assert call_kwargs["lineage_lookback_days"] == 14
        assert call_kwargs["use_account_usage"] is True


@pytest.mark.asyncio
async def test_snowflake_ingest_with_filters(test_db):
    """Test Snowflake ingestion with database and schema filters."""
    with patch("src.api.routers.ingest.IngestionService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service

        mock_result = IngestionResult(
            job_id="12345678-1234-1234-1234-123456789abc",
            status=IngestionStatus.COMPLETED,
            source_type="snowflake",
            source_name="PROD",
            stats=IngestionStats(capsules_created=5),
        )
        mock_service.ingest_snowflake = AsyncMock(return_value=mock_result)

        os.environ["SNOWFLAKE_PASSWORD"] = "test-password"

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/ingest/snowflake",
                json={
                    "account": "test-account",
                    "user": "test_user",
                    "databases": ["PROD", "ANALYTICS"],
                    "schemas": ["RAW_*", "STAGING_*"],
                    "include_views": True,
                    "include_materialized_views": False,
                    "include_external_tables": True,
                },
            )

        assert response.status_code == 200

        # Verify filters were passed
        call_kwargs = mock_service.ingest_snowflake.call_args.kwargs
        assert call_kwargs["databases"] == ["PROD", "ANALYTICS"]
        assert call_kwargs["schemas"] == ["RAW_*", "STAGING_*"]
        assert call_kwargs["include_views"] is True
        assert call_kwargs["include_materialized_views"] is False
        assert call_kwargs["include_external_tables"] is True


@pytest.mark.asyncio
async def test_snowflake_ingest_with_cleanup_orphans(test_db):
    """Test Snowflake ingestion with cleanup_orphans flag."""
    with patch("src.api.routers.ingest.IngestionService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service

        mock_result = IngestionResult(
            job_id="12345678-1234-1234-1234-123456789abc",
            status=IngestionStatus.COMPLETED,
            source_type="snowflake",
            source_name="PROD",
            stats=IngestionStats(
                capsules_created=5,
                capsules_deleted=2,
            ),
        )
        mock_service.ingest_snowflake = AsyncMock(return_value=mock_result)

        os.environ["SNOWFLAKE_PASSWORD"] = "test-password"

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/ingest/snowflake",
                json={
                    "account": "test-account",
                    "user": "test_user",
                    "databases": ["PROD"],
                    "cleanup_orphans": True,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["stats"]["capsules_deleted"] == 2

        # Verify cleanup_orphans was passed
        call_kwargs = mock_service.ingest_snowflake.call_args.kwargs
        assert call_kwargs["cleanup_orphans"] is True
