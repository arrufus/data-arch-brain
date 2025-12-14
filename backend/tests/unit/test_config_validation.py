"""Unit tests for configuration validation."""

import pytest
from unittest.mock import patch

from src.config import Settings, ConfigurationError, validate_config


class TestSettingsValidation:
    """Tests for Settings validation methods."""

    def test_validation_passes_for_development(self):
        """Test validation passes for development settings."""
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
            environment="development",
        )
        
        issues = settings.validate_for_startup()
        
        # In development, critical issues become warnings
        critical = [i for i in issues if i.startswith("CRITICAL")]
        assert len(critical) == 0

    def test_validation_fails_default_db_in_production(self):
        """Test validation fails with default DB in production."""
        settings = Settings(
            database_url="postgresql+asyncpg://dab:dab_password@localhost:5433/dab",
            environment="production",
            api_keys=["secure-production-key"],
        )
        
        issues = settings.validate_for_startup()
        
        critical = [i for i in issues if "default database URL" in i]
        assert len(critical) > 0

    def test_validation_fails_default_api_key_in_production(self):
        """Test validation fails with default API key in production."""
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@prod-db:5432/db",
            environment="production",
            api_keys=["dev-api-key-change-in-prod"],
        )
        
        issues = settings.validate_for_startup()
        
        critical = [i for i in issues if "default API key" in i]
        assert len(critical) > 0

    def test_validation_fails_auth_disabled_in_production(self):
        """Test validation fails with auth disabled in production."""
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@prod-db:5432/db",
            environment="production",
            api_keys=["secure-key"],
            auth_enabled=False,
        )
        
        issues = settings.validate_for_startup()
        
        critical = [i for i in issues if "Authentication is disabled" in i]
        assert len(critical) > 0

    def test_warning_cache_without_redis(self):
        """Test warning when cache enabled without Redis."""
        settings = Settings(
            database_url="sqlite:///:memory:",
            environment="development",
            cache_enabled=True,
            cache_redis_url=None,
        )
        
        issues = settings.validate_for_startup()
        
        warnings = [i for i in issues if "Caching enabled but no Redis URL" in i]
        assert len(warnings) > 0

    def test_warning_rate_limit_without_storage(self):
        """Test warning when rate limiting without storage URI."""
        settings = Settings(
            database_url="sqlite:///:memory:",
            environment="development",
            rate_limit_enabled=True,
            rate_limit_storage_uri=None,
        )
        
        issues = settings.validate_for_startup()
        
        warnings = [i for i in issues if "Rate limiting enabled but no storage URI" in i]
        assert len(warnings) > 0

    def test_warning_tracing_without_endpoint(self):
        """Test warning when tracing enabled without OTLP endpoint."""
        settings = Settings(
            database_url="sqlite:///:memory:",
            environment="development",
            tracing_enabled=True,
            tracing_otlp_endpoint=None,
        )
        
        issues = settings.validate_for_startup()
        
        warnings = [i for i in issues if "Tracing enabled but no OTLP endpoint" in i]
        assert len(warnings) > 0

    def test_warning_cors_wildcard_in_production(self):
        """Test warning for CORS wildcard in production."""
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@prod-db:5432/db",
            environment="production",
            api_keys=["secure-key"],
            auth_enabled=True,
            cors_origins=["*"],
        )
        
        issues = settings.validate_for_startup()
        
        warnings = [i for i in issues if "CORS allows all origins" in i]
        assert len(warnings) > 0


class TestValidateConfigFunction:
    """Tests for validate_config function."""

    def test_validate_config_logs_warnings(self):
        """Test that validate_config logs warnings."""
        settings = Settings(
            database_url="sqlite:///:memory:",
            environment="development",
            cache_enabled=True,
            cache_redis_url=None,
        )
        
        # Should not raise
        validate_config(settings, strict=False)

    def test_validate_config_strict_raises_on_critical(self):
        """Test that strict mode raises on critical issues."""
        settings = Settings(
            database_url="postgresql+asyncpg://dab:dab_password@localhost:5433/dab",
            environment="production",
            api_keys=["dev-api-key-change-in-prod"],
        )
        
        with pytest.raises(ConfigurationError) as exc_info:
            validate_config(settings, strict=True)
        
        assert len(exc_info.value.issues) > 0

    def test_validate_config_non_strict_doesnt_raise(self):
        """Test that non-strict mode doesn't raise on critical issues."""
        settings = Settings(
            database_url="postgresql+asyncpg://dab:dab_password@localhost:5433/dab",
            environment="production",
            api_keys=["dev-api-key-change-in-prod"],
        )
        
        # Should not raise
        validate_config(settings, strict=False)


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_configuration_error_message(self):
        """Test ConfigurationError message formatting."""
        issues = [
            "CRITICAL: Issue 1",
            "WARNING: Issue 2",
        ]
        
        error = ConfigurationError(issues)
        
        assert "Issue 1" in str(error)
        assert "Issue 2" in str(error)
        assert error.issues == issues

    def test_configuration_error_empty_issues(self):
        """Test ConfigurationError with empty issues."""
        error = ConfigurationError([])
        
        assert error.issues == []


class TestSettingsProperties:
    """Tests for Settings property methods."""

    def test_is_development(self):
        """Test is_development property."""
        settings = Settings(
            database_url="sqlite:///:memory:",
            environment="development",
        )
        
        assert settings.is_development is True
        assert settings.is_production is False

    def test_is_production(self):
        """Test is_production property."""
        settings = Settings(
            database_url="sqlite:///:memory:",
            environment="production",
        )
        
        assert settings.is_production is True
        assert settings.is_development is False

    def test_auth_required_development_disabled(self):
        """Test auth_required in development with auth disabled."""
        settings = Settings(
            database_url="sqlite:///:memory:",
            environment="development",
            auth_enabled=False,
        )
        
        assert settings.auth_required is False

    def test_auth_required_production_always_true(self):
        """Test auth_required is always True in production."""
        settings = Settings(
            database_url="sqlite:///:memory:",
            environment="production",
            auth_enabled=False,  # This should be ignored in production
        )
        
        assert settings.auth_required is True


class TestSettingsDefaults:
    """Tests for Settings default values."""

    def test_default_values(self):
        """Test default configuration values."""
        settings = Settings(database_url="sqlite:///:memory:")
        
        # API defaults
        assert settings.api_prefix == "/api/v1"
        assert settings.api_version == "0.1.0"
        
        # Auth defaults
        assert settings.auth_enabled is True
        assert settings.api_key_header == "X-API-Key"
        
        # Rate limiting defaults
        assert settings.rate_limit_enabled is True
        assert settings.rate_limit_default == "100/minute"
        
        # Caching defaults
        assert settings.cache_enabled is True
        assert settings.cache_default_ttl == 300
        
        # Tracing defaults
        assert settings.tracing_enabled is False
        assert settings.tracing_service_name == "data-architecture-brain"

    def test_database_defaults(self):
        """Test database configuration defaults."""
        settings = Settings(database_url="sqlite:///:memory:")
        
        assert settings.database_pool_size == 5
        assert settings.database_max_overflow == 10
        assert settings.database_echo is False

    def test_feature_defaults(self):
        """Test feature flag defaults."""
        settings = Settings(database_url="sqlite:///:memory:")
        
        assert settings.max_lineage_depth == 10
        assert settings.pii_detection_enabled is True
        assert settings.conformance_on_ingest is True
