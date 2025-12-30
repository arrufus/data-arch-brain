"""dbt manifest resolver for linking Airflow DbtOperator tasks to dbt models."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DbtModelReference:
    """Reference to a dbt model from manifest."""

    unique_id: str  # e.g., "model.my_project.customers"
    name: str  # e.g., "customers"
    schema: str  # e.g., "analytics"
    database: Optional[str] = None
    package_name: Optional[str] = None
    materialization: str = "table"  # table, view, incremental, ephemeral
    tags: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)

    @property
    def fqn(self) -> str:
        """Get fully qualified name."""
        parts = []
        if self.database:
            parts.append(self.database)
        if self.schema:
            parts.append(self.schema)
        parts.append(self.name)
        return ".".join(parts)


class DbtManifestResolver:
    """Resolver for querying dbt manifest.json files."""

    def __init__(self, manifest_path: Optional[str] = None):
        """Initialize resolver.

        Args:
            manifest_path: Path to dbt manifest.json file
        """
        self.manifest_path = manifest_path
        self._manifest_data: Optional[dict] = None
        self._models_cache: dict[str, DbtModelReference] = {}

    def load_manifest(self, manifest_path: Optional[str] = None) -> bool:
        """Load dbt manifest from file.

        Args:
            manifest_path: Path to manifest.json (overrides constructor path)

        Returns:
            True if loaded successfully
        """
        path = manifest_path or self.manifest_path
        if not path:
            logger.warning("No manifest path provided")
            return False

        try:
            manifest_file = Path(path)
            if not manifest_file.exists():
                logger.warning(f"Manifest file not found: {path}")
                return False

            with open(manifest_file) as f:
                self._manifest_data = json.load(f)

            # Build models cache
            self._build_models_cache()
            logger.info(f"Loaded dbt manifest with {len(self._models_cache)} models")
            return True

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in manifest file: {e}")
            return False
        except Exception as e:
            logger.exception(f"Error loading manifest: {e}")
            return False

    def _build_models_cache(self) -> None:
        """Build cache of models from manifest."""
        if not self._manifest_data:
            return

        nodes = self._manifest_data.get("nodes", {})
        for unique_id, node_data in nodes.items():
            # Only process model nodes
            if not unique_id.startswith("model."):
                continue

            try:
                model = DbtModelReference(
                    unique_id=unique_id,
                    name=node_data.get("name", ""),
                    schema=node_data.get("schema", ""),
                    database=node_data.get("database"),
                    package_name=node_data.get("package_name"),
                    materialization=node_data.get("config", {}).get("materialized", "table"),
                    tags=node_data.get("tags", []),
                    depends_on=node_data.get("depends_on", {}).get("nodes", []),
                )
                self._models_cache[unique_id] = model
            except Exception as e:
                logger.warning(f"Failed to parse model {unique_id}: {e}")

    def resolve_selector(self, selector: str) -> list[DbtModelReference]:
        """Resolve dbt selector to list of models.

        Supports:
        - tag:tagname (e.g., "tag:finance")
        - model_name (e.g., "customers")
        - path/to/models/* (e.g., "marts/finance/*")
        - package.model_name

        Args:
            selector: dbt selector string

        Returns:
            List of matching models
        """
        if not self._models_cache:
            logger.warning("No manifest loaded")
            return []

        # Parse selector
        if selector.startswith("tag:"):
            # Tag selector
            tag_name = selector[4:]  # Remove "tag:" prefix
            return self._filter_by_tag(tag_name)

        elif "." in selector and not selector.endswith("*"):
            # Package.model selector
            return self._filter_by_package_model(selector)

        elif "*" in selector:
            # Path selector
            return self._filter_by_path(selector)

        else:
            # Single model name
            return self._filter_by_name(selector)

    def _filter_by_tag(self, tag_name: str) -> list[DbtModelReference]:
        """Filter models by tag."""
        return [
            model
            for model in self._models_cache.values()
            if tag_name in model.tags
        ]

    def _filter_by_name(self, model_name: str) -> list[DbtModelReference]:
        """Filter models by name."""
        return [
            model
            for model in self._models_cache.values()
            if model.name == model_name
        ]

    def _filter_by_package_model(self, selector: str) -> list[DbtModelReference]:
        """Filter models by package.model format."""
        parts = selector.split(".", 1)
        if len(parts) != 2:
            return []

        package_name, model_name = parts
        return [
            model
            for model in self._models_cache.values()
            if model.package_name == package_name and model.name == model_name
        ]

    def _filter_by_path(self, path_pattern: str) -> list[DbtModelReference]:
        """Filter models by path pattern (simplified glob)."""
        # Simplified: just check if path prefix matches
        # Full implementation would use fnmatch or similar
        path_prefix = path_pattern.rstrip("/*")

        matches = []
        for unique_id, model in self._models_cache.items():
            # Extract path from unique_id (e.g., "model.project.marts_finance_customers")
            # This is a simplification - real path info is in manifest
            if path_prefix.lower() in unique_id.lower():
                matches.append(model)

        return matches

    def get_model_by_name(self, model_name: str) -> Optional[DbtModelReference]:
        """Get single model by name.

        Args:
            model_name: Model name

        Returns:
            DbtModelReference or None
        """
        matches = self._filter_by_name(model_name)
        if not matches:
            return None
        if len(matches) > 1:
            logger.warning(f"Multiple models found for name '{model_name}', returning first")
        return matches[0]

    def model_to_capsule_urn(
        self,
        model: DbtModelReference,
        project_name: Optional[str] = None,
    ) -> str:
        """Convert dbt model to DataCapsule URN.

        Args:
            model: dbt model reference
            project_name: dbt project name (for URN)

        Returns:
            Capsule URN string
        """
        # dbt model URN format: urn:dcs:dbt:model:{project}.{schema}:{model_name}
        project = project_name or model.package_name or "default"
        schema = model.schema or "unknown"

        return f"urn:dcs:dbt:model:{project}.{schema}:{model.name}"

    def extract_from_operator_config(self, operator_config: dict) -> dict:
        """Extract dbt references from Airflow operator config.

        Args:
            operator_config: Airflow task operator configuration

        Returns:
            Dict with 'selector', 'models', 'operation_type'
        """
        result = {
            "selector": None,
            "models": [],
            "operation_type": "merge",  # Default for dbt
        }

        # Try to extract dbt selector from various config fields
        # DbtRunOperator might have: select, models, exclude, etc.
        if "select" in operator_config:
            result["selector"] = operator_config["select"]
        elif "models" in operator_config:
            models_value = operator_config["models"]
            if isinstance(models_value, str):
                result["selector"] = models_value
            elif isinstance(models_value, list):
                result["models"] = models_value

        # Determine operation type from materialization
        # If selector is provided, resolve it
        if result["selector"] and self._manifest_data:
            models = self.resolve_selector(result["selector"])
            result["models"] = [model.name for model in models]

            # Check materialization types
            for model in models:
                if model.materialization == "incremental":
                    result["operation_type"] = "merge"
                    break

        return result
