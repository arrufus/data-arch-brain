"""Unit tests for the Airflow parser."""

import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio

from src.parsers import (
    AirflowParser,
    AirflowParserConfig,
    ParseResult,
    get_parser,
    available_parsers,
)


class TestParserRegistry:
    """Tests for the parser registry with Airflow."""

    def test_airflow_parser_registered(self):
        """Test that airflow parser is registered."""
        assert "airflow" in available_parsers()

    def test_get_airflow_parser(self):
        """Test getting airflow parser from registry."""
        parser = get_parser("airflow")
        assert isinstance(parser, AirflowParser)


class TestAirflowParserConfig:
    """Tests for Airflow parser configuration."""

    def test_from_dict_minimal(self):
        """Test creating config with minimal options."""
        config = AirflowParserConfig.from_dict({"base_url": "https://airflow.example.com"})
        assert config.base_url == "https://airflow.example.com"
        assert config.instance_name == "airflow-example-com"
        assert config.auth_mode == "none"

    def test_from_dict_with_instance_name(self):
        """Test creating config with explicit instance name."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "instance_name": "prod-airflow",
        })
        assert config.instance_name == "prod-airflow"

    def test_from_dict_with_auth(self):
        """Test creating config with authentication."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "auth_mode": "bearer_env",
            "token_env": "MY_TOKEN",
        })
        assert config.auth_mode == "bearer_env"
        assert config.token_env == "MY_TOKEN"

    def test_from_dict_with_filters(self):
        """Test creating config with DAG filters."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "dag_id_allowlist": ["dag1", "dag2"],
            "include_paused": True,
        })
        assert config.dag_id_allowlist == ["dag1", "dag2"]
        assert config.include_paused is True

    def test_from_dict_with_regex(self):
        """Test creating config with regex filter."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "dag_id_regex": "customer_.*",
        })
        assert config.dag_id_regex == "customer_.*"
        assert config._dag_id_pattern is not None

    def test_validate_missing_base_url(self):
        """Test validation fails for missing base_url."""
        config = AirflowParserConfig.from_dict({"base_url": ""})
        errors = config.validate()
        assert len(errors) > 0
        assert any("base_url is required" in e for e in errors)

    def test_validate_invalid_base_url(self):
        """Test validation fails for invalid base_url."""
        config = AirflowParserConfig.from_dict({"base_url": "not-a-url"})
        errors = config.validate()
        assert len(errors) > 0
        assert any("http://" in e or "https://" in e for e in errors)

    def test_validate_conflicting_filters(self):
        """Test validation fails for conflicting allowlist and denylist."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "dag_id_allowlist": ["dag1"],
            "dag_id_denylist": ["dag2"],
        })
        errors = config.validate()
        assert len(errors) > 0
        assert any("allowlist and dag_id_denylist" in e for e in errors)

    def test_validate_invalid_page_limit(self):
        """Test validation fails for invalid page_limit."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "page_limit": 2000,
        })
        errors = config.validate()
        assert len(errors) > 0
        assert any("page_limit" in e for e in errors)

    @patch.dict(os.environ, {"MY_TOKEN": "test-token"})
    def test_validate_bearer_auth_with_env(self):
        """Test validation succeeds for bearer auth with env var."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "auth_mode": "bearer_env",
            "token_env": "MY_TOKEN",
        })
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_bearer_auth_without_env(self):
        """Test validation fails for bearer auth without env var."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "auth_mode": "bearer_env",
            "token_env": "NONEXISTENT_TOKEN",
        })
        errors = config.validate()
        assert len(errors) > 0
        assert any("NONEXISTENT_TOKEN" in e for e in errors)

    @patch.dict(os.environ, {"MY_TOKEN": "test-token"})
    def test_get_auth_headers_bearer(self):
        """Test getting bearer token auth headers."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "auth_mode": "bearer_env",
            "token_env": "MY_TOKEN",
        })
        headers = config.get_auth_headers()
        assert headers["Authorization"] == "Bearer test-token"

    @patch.dict(os.environ, {"MY_USER": "admin", "MY_PASS": "secret"})
    def test_get_auth_headers_basic(self):
        """Test getting basic auth headers."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "auth_mode": "basic_env",
            "username_env": "MY_USER",
            "password_env": "MY_PASS",
        })
        headers = config.get_auth_headers()
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

    def test_get_auth_headers_none(self):
        """Test getting auth headers when auth is disabled."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "auth_mode": "none",
        })
        headers = config.get_auth_headers()
        assert headers == {}

    def test_should_include_dag_allowlist(self):
        """Test DAG inclusion with allowlist."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "dag_id_allowlist": ["dag1", "dag2"],
        })
        assert config.should_include_dag("dag1", False, True) is True
        assert config.should_include_dag("dag3", False, True) is False

    def test_should_include_dag_denylist(self):
        """Test DAG inclusion with denylist."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "dag_id_denylist": ["dag2"],
        })
        assert config.should_include_dag("dag1", False, True) is True
        assert config.should_include_dag("dag2", False, True) is False

    def test_should_include_dag_paused_filter(self):
        """Test DAG inclusion with paused filter."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "include_paused": False,
        })
        assert config.should_include_dag("dag1", False, True) is True
        assert config.should_include_dag("dag1", True, True) is False

    def test_should_include_dag_inactive_filter(self):
        """Test DAG inclusion with inactive filter."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "include_inactive": False,
        })
        assert config.should_include_dag("dag1", False, True) is True
        assert config.should_include_dag("dag1", False, False) is False

    def test_should_include_dag_regex(self):
        """Test DAG inclusion with regex filter."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "dag_id_regex": "customer_.*",
        })
        assert config.should_include_dag("customer_daily", False, True) is True
        assert config.should_include_dag("internal_daily", False, True) is False

    def test_extract_domain_from_tags(self):
        """Test extracting domain from tags."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow.example.com",
            "domain_tag_prefix": "domain:",
        })
        assert config.extract_domain_from_tags(["production", "domain:customer"]) == "customer"
        assert config.extract_domain_from_tags(["production", "staging"]) is None
        assert config.extract_domain_from_tags([]) is None

    def test_instance_name_derived_from_url(self):
        """Test instance name is derived from base_url."""
        config = AirflowParserConfig.from_dict({
            "base_url": "https://airflow-prod.example.com:8080"
        })
        assert "airflow-prod" in config.instance_name or "example" in config.instance_name


class TestAirflowParser:
    """Tests for Airflow parser."""

    @pytest.fixture
    def airflow_parser(self):
        """Create an Airflow parser instance."""
        return AirflowParser()

    @pytest.fixture
    def basic_config(self):
        """Create a basic parser config."""
        return {
            "base_url": "https://airflow.example.com",
            "instance_name": "test-airflow",
        }

    def test_source_type(self, airflow_parser):
        """Test parser source type."""
        assert airflow_parser.source_type == "airflow"

    def test_validate_config_minimal(self, airflow_parser):
        """Test config validation with minimal config."""
        errors = airflow_parser.validate_config({"base_url": "https://airflow.example.com"})
        assert len(errors) == 0

    def test_validate_config_missing_base_url(self, airflow_parser):
        """Test config validation fails without base_url."""
        errors = airflow_parser.validate_config({})
        assert len(errors) > 0
        assert any("base_url is required" in e for e in errors)

    def test_validate_config_invalid_auth(self, airflow_parser):
        """Test config validation fails with invalid auth."""
        errors = airflow_parser.validate_config({
            "base_url": "https://airflow.example.com",
            "auth_mode": "invalid",
        })
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_parse_with_invalid_config(self, airflow_parser):
        """Test parsing with invalid config returns errors."""
        result = await airflow_parser.parse({})
        assert result.has_errors
        assert result.error_count > 0

    @pytest.mark.asyncio
    async def test_parse_with_mock_api(self, airflow_parser, basic_config):
        """Test parsing with mocked Airflow API responses."""
        # Helper to create mock response
        def create_mock_response(json_data):
            mock_response = AsyncMock()
            mock_response.json = lambda: json_data
            mock_response.raise_for_status = lambda: None
            return mock_response

        # Mock API responses
        mock_version_response = create_mock_response({"version": "2.7.0"})

        mock_dags_response = create_mock_response({
            "dags": [
                {
                    "dag_id": "test_dag",
                    "is_paused": False,
                    "is_active": True,
                    "description": "Test DAG",
                    "schedule_interval": "0 0 * * *",
                    "owners": ["admin"],
                    "tags": [{"name": "test"}, {"name": "domain:analytics"}],
                }
            ],
            "total_entries": 1,
        })

        mock_dag_detail_response = create_mock_response({
            "dag_id": "test_dag",
            "catchup": True,
            "max_active_runs": 1,
        })

        mock_tasks_response = create_mock_response({
            "tasks": [
                {
                    "task_id": "task1",
                    "operator_name": "BashOperator",
                    "downstream_task_ids": ["task2"],
                },
                {
                    "task_id": "task2",
                    "operator_name": "PythonOperator",
                    "downstream_task_ids": [],
                },
            ]
        })

        # Mock the HTTP client
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            # Configure mock responses based on URL
            async def mock_get(url, **kwargs):
                if "/version" in url:
                    return mock_version_response
                elif "/tasks" in url:
                    return mock_tasks_response
                elif "/dags/test_dag" in url:
                    return mock_dag_detail_response
                elif "/dags" in url:
                    return mock_dags_response
                raise ValueError(f"Unexpected URL: {url}")

            mock_client.get = mock_get
            mock_client_class.return_value = mock_client

            # Run parser
            result = await airflow_parser.parse(basic_config)

            # Verify results
            assert result.source_type == "airflow"
            assert result.source_name == "test-airflow"
            assert result.source_version == "2.7.0"

            # Should have 1 pipeline + 2 tasks (NOT capsules)
            assert len(result.pipelines) == 1
            assert len(result.pipeline_tasks) == 2

            # Check DAG pipeline (NOT capsule)
            dag_pipeline = result.pipelines[0]
            assert dag_pipeline.pipeline_type == "airflow_dag"
            assert dag_pipeline.name == "test_dag"
            assert dag_pipeline.urn == "urn:dcs:pipeline:airflow:test-airflow:test_dag"
            assert dag_pipeline.domain_name == "analytics"

            # Check pipeline tasks (NOT capsules)
            assert len(result.pipeline_tasks) == 2

            task1 = next(t for t in result.pipeline_tasks if t.name == "task1")
            assert task1.operator == "BashOperator"
            assert task1.task_type == "bash"

            # Should have orchestration edges: pipeline→task1, pipeline→task2, task1→task2 = 3 edges
            assert len(result.orchestration_edges) == 3  # 2 CONTAINS + 1 DEPENDS_ON

            # Check containment edges
            contains_edges = [e for e in result.orchestration_edges if e.edge_type == "contains"]
            assert len(contains_edges) == 2

            # Check dependency edges
            depends_on_edges = [e for e in result.orchestration_edges if e.edge_type == "depends_on"]
            assert len(depends_on_edges) == 1
            assert "task1" in depends_on_edges[0].source_urn
            assert "task2" in depends_on_edges[0].target_urn

    @pytest.mark.asyncio
    async def test_parse_with_api_error(self, airflow_parser, basic_config):
        """Test parsing handles API errors gracefully."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            # Simulate API error
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "404 Not Found",
                request=AsyncMock(),
                response=AsyncMock(status_code=404, text="Not Found"),
            )
            mock_client_class.return_value = mock_client

            result = await airflow_parser.parse(basic_config)

            # Should have warnings/errors but not crash
            assert result.error_count > 0 or result.warning_count > 0
            assert len(result.pipelines) == 0  # No data extracted
            assert len(result.pipeline_tasks) == 0  # No data extracted

    @pytest.mark.asyncio
    async def test_parse_urn_construction(self, airflow_parser):
        """Test URN construction for DAGs and tasks."""
        config = {
            "base_url": "https://airflow.example.com",
            "instance_name": "prod",
        }

        # Helper to create mock response
        def create_mock_response(json_data):
            mock_response = AsyncMock()
            mock_response.json = lambda: json_data
            mock_response.raise_for_status = lambda: None
            return mock_response

        # Mock minimal API response
        mock_dags_response = create_mock_response({
            "dags": [
                {
                    "dag_id": "customer_pipeline",
                    "is_paused": False,
                    "is_active": True,
                }
            ]
        })

        mock_tasks_response = create_mock_response({
            "tasks": [
                {
                    "task_id": "extract",
                    "operator_name": "BashOperator",
                    "downstream_task_ids": [],
                }
            ]
        })

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            async def mock_get(url, **kwargs):
                if "/tasks" in url:
                    return mock_tasks_response
                elif "/dags" in url:
                    return mock_dags_response
                return create_mock_response({})

            mock_client.get = mock_get
            mock_client_class.return_value = mock_client

            result = await airflow_parser.parse(config)

            # Check URN format for pipelines and tasks
            dag_pipeline = result.pipelines[0]
            assert dag_pipeline.urn == "urn:dcs:pipeline:airflow:prod:customer_pipeline"

            task = result.pipeline_tasks[0]
            assert task.urn == "urn:dcs:task:airflow:prod:customer_pipeline.extract"
