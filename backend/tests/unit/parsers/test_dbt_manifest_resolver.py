"""Tests for dbt manifest resolver."""

import json
import tempfile
from pathlib import Path

import pytest

from src.parsers.dbt_manifest_resolver import DbtManifestResolver, DbtModelReference


@pytest.fixture
def sample_manifest():
    """Create a sample dbt manifest structure."""
    return {
        "metadata": {
            "dbt_version": "1.5.0",
            "project_name": "analytics"
        },
        "nodes": {
            "model.analytics.customers": {
                "unique_id": "model.analytics.customers",
                "name": "customers",
                "schema": "marts",
                "database": "analytics_db",
                "package_name": "analytics",
                "tags": ["core", "customers"],
                "config": {
                    "materialized": "table"
                },
                "depends_on": {
                    "nodes": ["source.analytics.raw_customers"]
                }
            },
            "model.analytics.orders": {
                "unique_id": "model.analytics.orders",
                "name": "orders",
                "schema": "marts",
                "database": "analytics_db",
                "package_name": "analytics",
                "tags": ["core", "orders"],
                "config": {
                    "materialized": "incremental"
                },
                "depends_on": {
                    "nodes": ["source.analytics.raw_orders", "model.analytics.customers"]
                }
            },
            "model.analytics.revenue_by_month": {
                "unique_id": "model.analytics.revenue_by_month",
                "name": "revenue_by_month",
                "schema": "finance",
                "database": "analytics_db",
                "package_name": "analytics",
                "tags": ["finance", "reporting"],
                "config": {
                    "materialized": "table"
                },
                "depends_on": {
                    "nodes": ["model.analytics.orders"]
                }
            },
            "source.analytics.raw_customers": {
                "unique_id": "source.analytics.raw_customers",
                "name": "raw_customers",
                "source_name": "raw"
            }
        }
    }


@pytest.fixture
def manifest_file(sample_manifest, tmp_path):
    """Create a temporary manifest file."""
    manifest_path = tmp_path / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(sample_manifest, f)
    return str(manifest_path)


class TestDbtManifestResolver:
    """Test dbt manifest resolver."""

    def test_load_manifest(self, manifest_file):
        """Test loading manifest file."""
        resolver = DbtManifestResolver()
        success = resolver.load_manifest(manifest_file)

        assert success
        assert len(resolver._models_cache) == 3  # Only models, not sources

    def test_load_manifest_missing_file(self):
        """Test loading missing manifest file."""
        resolver = DbtManifestResolver()
        success = resolver.load_manifest("/nonexistent/manifest.json")

        assert not success

    def test_resolve_selector_by_tag(self, manifest_file):
        """Test resolving selector by tag."""
        resolver = DbtManifestResolver(manifest_file)
        resolver.load_manifest()

        # Tag: finance
        models = resolver.resolve_selector("tag:finance")
        assert len(models) == 1
        assert models[0].name == "revenue_by_month"

        # Tag: core
        models = resolver.resolve_selector("tag:core")
        assert len(models) == 2
        model_names = {m.name for m in models}
        assert "customers" in model_names
        assert "orders" in model_names

    def test_resolve_selector_by_name(self, manifest_file):
        """Test resolving selector by model name."""
        resolver = DbtManifestResolver(manifest_file)
        resolver.load_manifest()

        models = resolver.resolve_selector("customers")
        assert len(models) == 1
        assert models[0].name == "customers"
        assert models[0].schema == "marts"

    def test_resolve_selector_by_package_model(self, manifest_file):
        """Test resolving selector by package.model format."""
        resolver = DbtManifestResolver(manifest_file)
        resolver.load_manifest()

        models = resolver.resolve_selector("analytics.customers")
        assert len(models) == 1
        assert models[0].name == "customers"
        assert models[0].package_name == "analytics"

    def test_get_model_by_name(self, manifest_file):
        """Test getting single model by name."""
        resolver = DbtManifestResolver(manifest_file)
        resolver.load_manifest()

        model = resolver.get_model_by_name("orders")
        assert model is not None
        assert model.name == "orders"
        assert model.materialization == "incremental"

        # Non-existent model
        model = resolver.get_model_by_name("nonexistent")
        assert model is None

    def test_model_to_capsule_urn(self, manifest_file):
        """Test converting model to capsule URN."""
        resolver = DbtManifestResolver(manifest_file)
        resolver.load_manifest()

        model = resolver.get_model_by_name("customers")
        urn = resolver.model_to_capsule_urn(model, project_name="analytics")

        assert urn == "urn:dcs:dbt:model:analytics.marts:customers"

    def test_extract_from_operator_config_with_select(self, manifest_file):
        """Test extracting dbt config from operator with select."""
        resolver = DbtManifestResolver(manifest_file)
        resolver.load_manifest()

        operator_config = {
            "select": "tag:finance"
        }

        result = resolver.extract_from_operator_config(operator_config)
        assert result["selector"] == "tag:finance"
        assert "revenue_by_month" in result["models"]
        assert result["operation_type"] == "merge"  # Default

    def test_extract_from_operator_config_with_models_list(self):
        """Test extracting dbt config with models list."""
        resolver = DbtManifestResolver()

        operator_config = {
            "models": ["customers", "orders"]
        }

        result = resolver.extract_from_operator_config(operator_config)
        assert result["models"] == ["customers", "orders"]

    def test_dbt_model_reference_fqn(self):
        """Test fully qualified name property."""
        model = DbtModelReference(
            unique_id="model.analytics.customers",
            name="customers",
            schema="marts",
            database="analytics_db"
        )

        assert model.fqn == "analytics_db.marts.customers"

    def test_dbt_model_reference_fqn_no_database(self):
        """Test fully qualified name without database."""
        model = DbtModelReference(
            unique_id="model.analytics.customers",
            name="customers",
            schema="marts"
        )

        assert model.fqn == "marts.customers"

    def test_build_models_cache_filters_sources(self, manifest_file):
        """Test that sources are not included in models cache."""
        resolver = DbtManifestResolver(manifest_file)
        resolver.load_manifest()

        # Should only have models, not sources
        assert len(resolver._models_cache) == 3

        # Verify all cached items are models
        for unique_id in resolver._models_cache.keys():
            assert unique_id.startswith("model.")

    def test_incremental_materialization_detection(self, manifest_file):
        """Test detecting incremental materialization."""
        resolver = DbtManifestResolver(manifest_file)
        resolver.load_manifest()

        model = resolver.get_model_by_name("orders")
        assert model.materialization == "incremental"

        # When operator config references incremental model
        operator_config = {
            "select": "orders"
        }
        result = resolver.extract_from_operator_config(operator_config)
        assert result["operation_type"] == "merge"
