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
    database_url: str = "postgresql+asyncpg://dab:dab_password@localhost:5433/dab"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False

    # API
    api_prefix: str = "/api/v1"
    api_title: str = "Data Architecture Brain"
    api_version: str = "0.1.0"
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
    metrics_prefix: str = "dab"  # Prometheus metrics prefix

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


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
