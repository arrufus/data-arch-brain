"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://dcs:dcs_password@localhost:5433/dcs"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False

    # API
    api_prefix: str = "/api/v1"
    api_title: str = "Data Capsule Server"
    api_version: str = "0.2.0"
    cors_origins: List[str] = ["*"]

    # Authentication
    auth_enabled: bool = True
    api_keys: List[str] = ["dev-api-key-change-in-prod"]  # List of valid API keys
    api_key_header: str = "X-API-Key"
    # Endpoints that don't require authentication (supports wildcards)
    auth_exempt_paths: List[str] = [
        "/api/v1/health",
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/api/v1/docs",
        "/api/v1/redoc",
        "/api/v1/openapi.json",
    ]

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_default: str = "100/minute"  # Default rate limit
    rate_limit_burst: str = "200/minute"  # Burst limit for short periods
    rate_limit_expensive: str = "10/minute"  # Limit for expensive operations (conformance)
    rate_limit_storage_uri: Optional[str] = None  # Redis URI for distributed rate limiting

    # Caching
    cache_enabled: bool = True
    cache_redis_url: Optional[str] = None  # Redis URL (e.g., redis://localhost:6379/0)
    cache_default_ttl: int = 300  # Default cache TTL in seconds (5 minutes)
    cache_conformance_ttl: int = 600  # Conformance scores cache TTL (10 minutes)
    cache_pii_ttl: int = 300  # PII inventory cache TTL (5 minutes)
    cache_lineage_ttl: int = 900  # Lineage queries cache TTL (15 minutes)

    # Metrics & Observability
    metrics_enabled: bool = True
    metrics_prefix: str = "dcs"  # Prometheus metrics prefix

    # Distributed Tracing (OpenTelemetry)
    tracing_enabled: bool = False  # Enable OpenTelemetry tracing
    tracing_otlp_endpoint: Optional[str] = None  # OTLP collector endpoint (e.g., "http://localhost:4317")
    tracing_service_name: str = "data-capsule-server"
    tracing_console_export: bool = False  # Enable console export for debugging

    # Application
    environment: str = "development"
    log_level: str = "INFO"
    debug: bool = False

    # Features
    max_lineage_depth: int = 10
    pii_detection_enabled: bool = True
    conformance_on_ingest: bool = True

    # Paths
    rules_path: str = "config/rules"
    templates_path: str = "src/templates"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    @property
    def auth_required(self) -> bool:
        """Check if authentication is required (enabled and not in development)."""
        # In development, auth can be optionally disabled
        if self.is_development and not self.auth_enabled:
            return False
        # In production, auth is always required
        if self.is_production:
            return True
        return self.auth_enabled

    def validate_for_startup(self) -> list[str]:
        """
        Validate configuration for production readiness.
        
        Returns a list of warnings/errors. Empty list means all validations passed.
        Raises ConfigurationError for critical issues that should prevent startup.
        """
        issues: list[str] = []
        
        # Critical validations (would prevent startup in production)
        if self.is_production:
            # Database URL must be set and not default
            if "localhost" in self.database_url and "5433" in self.database_url:
                issues.append(
                    "CRITICAL: Using default database URL in production. "
                    "Set DATABASE_URL environment variable."
                )
            
            # API keys must be changed from default
            if "dev-api-key-change-in-prod" in self.api_keys:
                issues.append(
                    "CRITICAL: Using default API key in production. "
                    "Set API_KEYS environment variable with secure keys."
                )
            
            # Auth must be enabled in production
            if not self.auth_enabled:
                issues.append(
                    "CRITICAL: Authentication is disabled in production. "
                    "Set AUTH_ENABLED=true."
                )
        
        # Warnings (logged but don't prevent startup)
        if self.cache_enabled and not self.cache_redis_url:
            issues.append(
                "WARNING: Caching enabled but no Redis URL configured. "
                "Using in-memory cache (not suitable for multi-instance deployments)."
            )
        
        if self.rate_limit_enabled and not self.rate_limit_storage_uri:
            issues.append(
                "WARNING: Rate limiting enabled but no storage URI configured. "
                "Using in-memory storage (not suitable for multi-instance deployments)."
            )
        
        if self.tracing_enabled and not self.tracing_otlp_endpoint:
            issues.append(
                "WARNING: Tracing enabled but no OTLP endpoint configured. "
                "Traces will not be exported unless TRACING_CONSOLE_EXPORT=true."
            )
        
        # Validate database URL format
        if not self.database_url.startswith(("postgresql", "sqlite")):
            issues.append(
                "WARNING: Database URL should start with 'postgresql' or 'sqlite'. "
                f"Current: {self.database_url[:20]}..."
            )
        
        # Validate CORS origins in production
        if self.is_production and "*" in self.cors_origins:
            issues.append(
                "WARNING: CORS allows all origins (*) in production. "
                "Consider restricting to specific origins."
            )
        
        return issues


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    
    def __init__(self, issues: list[str]):
        self.issues = issues
        message = "Configuration validation failed:\n" + "\n".join(f"  - {i}" for i in issues)
        super().__init__(message)


def validate_config(settings: Settings, strict: bool = False) -> None:
    """
    Validate configuration and log/raise issues.
    
    Args:
        settings: Settings instance to validate
        strict: If True, raise ConfigurationError on any critical issues
    
    Raises:
        ConfigurationError: If strict=True and critical issues found
    """
    import logging
    logger = logging.getLogger(__name__)
    
    issues = settings.validate_for_startup()
    
    critical_issues = [i for i in issues if i.startswith("CRITICAL")]
    warnings = [i for i in issues if i.startswith("WARNING")]
    
    for warning in warnings:
        logger.warning(warning.replace("WARNING: ", ""))
    
    for critical in critical_issues:
        logger.error(critical.replace("CRITICAL: ", ""))
    
    if strict and critical_issues:
        raise ConfigurationError(critical_issues)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
