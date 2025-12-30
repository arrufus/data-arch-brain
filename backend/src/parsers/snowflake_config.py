"""Configuration for Snowflake metadata parser."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class SnowflakeParserConfig:
    """Configuration for Snowflake metadata parser."""

    # Connection (required)
    account: str
    user: str
    warehouse: str = "COMPUTE_WH"
    role: str = "SYSADMIN"

    # Authentication (one required)
    password: Optional[str] = None
    private_key_path: Optional[Path] = None

    # Scope
    databases: list[str] = field(default_factory=list)
    schemas: list[str] = field(default_factory=list)
    include_views: bool = True
    include_materialized_views: bool = True
    include_external_tables: bool = True

    # Features
    enable_lineage: bool = True
    lineage_lookback_days: int = 7
    use_account_usage: bool = True
    enable_tag_extraction: bool = True

    # Tag mappings
    tag_mappings: dict[str, dict[str, str]] = field(default_factory=dict)

    # Layer inference patterns
    layer_patterns: dict[str, list[str]] = field(
        default_factory=lambda: {
            "bronze": [
                r"^(raw|landing|bronze|stage|l1).*",
                r".*_raw$",
                r".*_landing$",
            ],
            "silver": [
                r"^(staging|stg|silver|intermediate|int|l2).*",
                r".*_staging$",
                r".*_stg$",
            ],
            "gold": [
                r"^(mart|marts|gold|analytics|prod|l3|presentation).*",
                r".*_(mart|marts)$",
                r".*_analytics$",
            ],
        }
    )

    # Performance
    batch_size: int = 1000
    max_workers: int = 4
    query_timeout_seconds: int = 300
    parallel_execution: bool = True  # Enable parallel database extraction
    enable_query_cache: bool = True  # Cache query results
    max_lineage_rows: Optional[int] = 10000  # Limit lineage query results

    # Incremental sync
    last_sync_timestamp: Optional[str] = None

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> "SnowflakeParserConfig":
        """Create config from dictionary."""
        # Convert string paths to Path objects
        if "private_key_path" in config and config["private_key_path"]:
            if isinstance(config["private_key_path"], str):
                config["private_key_path"] = Path(config["private_key_path"])

        # Ensure lists for databases and schemas
        if "databases" in config and isinstance(config["databases"], str):
            config["databases"] = [db.strip() for db in config["databases"].split(",")]
        if "schemas" in config and isinstance(config["schemas"], str):
            config["schemas"] = [s.strip() for s in config["schemas"].split(",")]

        return cls(**config)

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # Required fields
        if not self.account:
            errors.append("account is required")
        if not self.user:
            errors.append("user is required")
        if not self.warehouse:
            errors.append("warehouse is required")

        # Authentication
        if not self.password and not self.private_key_path:
            errors.append("Either password or private_key_path must be provided")

        # Validate private key path exists
        if self.private_key_path:
            if not isinstance(self.private_key_path, Path):
                errors.append(f"private_key_path must be a Path object")
            elif not self.private_key_path.exists():
                errors.append(f"private_key_path does not exist: {self.private_key_path}")

        # Validate lineage settings
        if self.enable_lineage:
            if self.lineage_lookback_days < 1 or self.lineage_lookback_days > 365:
                errors.append("lineage_lookback_days must be between 1 and 365")
            # Note: View lineage works without ACCOUNT_USAGE (uses INFORMATION_SCHEMA)
            # ACCESS_HISTORY lineage requires ACCOUNT_USAGE but is optional

        # Validate tag extraction settings
        if self.enable_tag_extraction and not self.use_account_usage:
            errors.append(
                "enable_tag_extraction requires use_account_usage to be True "
                "(tags are only available in ACCOUNT_USAGE)"
            )

        # Validate performance settings
        if self.batch_size < 1:
            errors.append("batch_size must be at least 1")
        if self.max_workers < 1:
            errors.append("max_workers must be at least 1")
        if self.query_timeout_seconds < 1:
            errors.append("query_timeout_seconds must be at least 1")

        return errors
