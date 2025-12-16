"""Configuration for Airflow parser."""

import os
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Optional
from urllib.parse import urlparse


@dataclass
class AirflowParserConfig:
    """Configuration for the Airflow parser.

    This configuration supports reading Airflow DAG and task metadata via the
    Airflow REST API (v1). Authentication credentials are referenced via
    environment variables to avoid storing secrets in configuration.
    """

    # Required fields
    base_url: str

    # Instance identification (used in URN construction)
    instance_name: Optional[str] = None

    # DAG filtering
    dag_id_allowlist: Optional[list[str]] = None
    dag_id_denylist: Optional[list[str]] = None
    dag_id_regex: Optional[str] = None

    # Inclusion controls
    include_paused: bool = False
    include_inactive: bool = False

    # API pagination and timeouts
    page_limit: int = 100
    timeout_seconds: float = 30.0

    # Authentication (references to environment variables)
    auth_mode: Literal["none", "bearer_env", "basic_env"] = "none"
    token_env: str = "AIRFLOW_TOKEN"
    username_env: str = "AIRFLOW_USERNAME"
    password_env: str = "AIRFLOW_PASSWORD"

    # Domain inference (optional)
    domain_tag_prefix: str = "domain:"

    # URN configuration
    urn_prefix: str = "urn:dab:airflow"

    # Compiled regex pattern (internal)
    _dag_id_pattern: Optional[re.Pattern[str]] = field(default=None, repr=False, init=False)

    def __post_init__(self) -> None:
        """Post-initialization processing."""
        # Derive instance_name from base_url if not provided
        if not self.instance_name:
            parsed = urlparse(self.base_url)
            hostname = parsed.netloc or parsed.path
            # Clean up hostname for use in URN (remove port, special chars)
            self.instance_name = re.sub(r"[:\.]", "-", hostname).strip("-")

        # Compile dag_id_regex if provided
        if self.dag_id_regex:
            try:
                self._dag_id_pattern = re.compile(self.dag_id_regex)
            except re.error as e:
                raise ValueError(f"Invalid dag_id_regex pattern: {e}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AirflowParserConfig":
        """Create config from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            AirflowParserConfig instance
        """
        # Extract known fields
        return cls(
            base_url=data["base_url"],
            instance_name=data.get("instance_name"),
            dag_id_allowlist=data.get("dag_id_allowlist"),
            dag_id_denylist=data.get("dag_id_denylist"),
            dag_id_regex=data.get("dag_id_regex"),
            include_paused=data.get("include_paused", False),
            include_inactive=data.get("include_inactive", False),
            page_limit=data.get("page_limit", 100),
            timeout_seconds=data.get("timeout_seconds", 30.0),
            auth_mode=data.get("auth_mode", "none"),
            token_env=data.get("token_env", "AIRFLOW_TOKEN"),
            username_env=data.get("username_env", "AIRFLOW_USERNAME"),
            password_env=data.get("password_env", "AIRFLOW_PASSWORD"),
            domain_tag_prefix=data.get("domain_tag_prefix", "domain:"),
            urn_prefix=data.get("urn_prefix", "urn:dab:airflow"),
        )

    def validate(self) -> list[str]:
        """Validate the configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        # Validate base_url
        if not self.base_url:
            errors.append("base_url is required")
        else:
            parsed = urlparse(self.base_url)
            if not parsed.scheme or parsed.scheme not in ("http", "https"):
                errors.append(
                    f"base_url must start with http:// or https://, got: {self.base_url}"
                )
            if not (parsed.netloc or parsed.path):
                errors.append(f"base_url is invalid: {self.base_url}")

        # Validate instance_name (after __post_init__)
        if not self.instance_name:
            errors.append("instance_name could not be derived from base_url")

        # Validate filtering logic consistency
        if self.dag_id_allowlist and self.dag_id_denylist:
            errors.append(
                "Cannot specify both dag_id_allowlist and dag_id_denylist"
            )

        # Validate page_limit
        if self.page_limit < 1 or self.page_limit > 1000:
            errors.append(f"page_limit must be between 1 and 1000, got: {self.page_limit}")

        # Validate timeout
        if self.timeout_seconds <= 0:
            errors.append(f"timeout_seconds must be positive, got: {self.timeout_seconds}")

        # Validate auth mode
        if self.auth_mode not in ("none", "bearer_env", "basic_env"):
            errors.append(
                f"auth_mode must be one of: none, bearer_env, basic_env, got: {self.auth_mode}"
            )

        # Validate environment variables exist if auth is enabled
        if self.auth_mode == "bearer_env":
            if self.token_env not in os.environ:
                errors.append(
                    f"auth_mode=bearer_env requires {self.token_env} environment variable"
                )

        if self.auth_mode == "basic_env":
            if self.username_env not in os.environ:
                errors.append(
                    f"auth_mode=basic_env requires {self.username_env} environment variable"
                )
            if self.password_env not in os.environ:
                errors.append(
                    f"auth_mode=basic_env requires {self.password_env} environment variable"
                )

        return errors

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers based on auth_mode.

        Returns:
            Dictionary of HTTP headers for authentication
        """
        if self.auth_mode == "bearer_env":
            token = os.environ.get(self.token_env, "")
            if token:
                return {"Authorization": f"Bearer {token}"}

        elif self.auth_mode == "basic_env":
            import base64

            username = os.environ.get(self.username_env, "")
            password = os.environ.get(self.password_env, "")
            if username and password:
                credentials = f"{username}:{password}".encode("utf-8")
                encoded = base64.b64encode(credentials).decode("utf-8")
                return {"Authorization": f"Basic {encoded}"}

        return {}

    def should_include_dag(self, dag_id: str, is_paused: bool, is_active: bool) -> bool:
        """Determine if a DAG should be included based on filters.

        Args:
            dag_id: The DAG ID to check
            is_paused: Whether the DAG is paused
            is_active: Whether the DAG is active

        Returns:
            True if the DAG should be included, False otherwise
        """
        # Check paused/active filters
        if is_paused and not self.include_paused:
            return False
        if not is_active and not self.include_inactive:
            return False

        # Check allowlist (if specified, only these DAGs)
        if self.dag_id_allowlist:
            return dag_id in self.dag_id_allowlist

        # Check denylist (exclude these DAGs)
        if self.dag_id_denylist:
            if dag_id in self.dag_id_denylist:
                return False

        # Check regex pattern
        if self._dag_id_pattern:
            return bool(self._dag_id_pattern.match(dag_id))

        # No filters specified, include by default
        return True

    def extract_domain_from_tags(self, tags: list[str]) -> Optional[str]:
        """Extract domain name from DAG tags using domain_tag_prefix.

        Args:
            tags: List of DAG tags

        Returns:
            Domain name if found, None otherwise

        Example:
            >>> config = AirflowParserConfig(base_url="http://localhost")
            >>> config.extract_domain_from_tags(["production", "domain:customer"])
            'customer'
        """
        if not tags:
            return None

        for tag in tags:
            if tag.startswith(self.domain_tag_prefix):
                domain = tag[len(self.domain_tag_prefix):].strip()
                if domain:
                    return domain

        return None
