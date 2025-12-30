"""Manual data flow annotations for Airflow tasks.

Allows users to specify PRODUCES/CONSUMES relationships between tasks and capsules
via YAML or JSON annotation files.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class DataFlowAnnotation:
    """Annotation for a single task's data flow."""

    task_urn: str
    consumes: list[str] = field(default_factory=list)  # List of capsule URNs
    produces: list[str] = field(default_factory=list)  # List of capsule URNs with optional metadata
    transforms: list[str] = field(default_factory=list)
    validates: list[str] = field(default_factory=list)

    # Operation metadata
    operations: dict[str, str] = field(default_factory=dict)  # capsule_urn -> operation type
    access_patterns: dict[str, str] = field(default_factory=dict)  # capsule_urn -> access pattern


class DataFlowAnnotationLoader:
    """Loader for manual data flow annotation files."""

    def __init__(self, annotation_file: Optional[str] = None):
        """Initialize loader.

        Args:
            annotation_file: Path to YAML or JSON annotation file
        """
        self.annotation_file = annotation_file
        self._annotations: dict[str, DataFlowAnnotation] = {}

    def load_annotations(self, annotation_file: Optional[str] = None) -> bool:
        """Load annotations from file.

        Args:
            annotation_file: Path to annotation file (overrides constructor)

        Returns:
            True if loaded successfully
        """
        file_path = annotation_file or self.annotation_file
        if not file_path:
            logger.warning("No annotation file provided")
            return False

        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"Annotation file not found: {file_path}")
                return False

            # Determine format from extension
            if path.suffix in [".yaml", ".yml"]:
                data = self._load_yaml(path)
            elif path.suffix == ".json":
                data = self._load_json(path)
            else:
                logger.error(f"Unsupported annotation file format: {path.suffix}")
                return False

            # Parse annotations
            self._parse_annotations(data)
            logger.info(f"Loaded {len(self._annotations)} task annotations from {file_path}")
            return True

        except Exception as e:
            logger.exception(f"Error loading annotations: {e}")
            return False

    def _load_yaml(self, path: Path) -> dict:
        """Load YAML file."""
        with open(path) as f:
            return yaml.safe_load(f)

    def _load_json(self, path: Path) -> dict:
        """Load JSON file."""
        with open(path) as f:
            return json.load(f)

    def _parse_annotations(self, data: dict) -> None:
        """Parse annotation data structure.

        Expected format:
        {
            "pipelines": [
                {
                    "pipeline_id": "finance_gl_pipeline",
                    "instance": "prod",  # optional
                    "tasks": [
                        {
                            "task_id": "load_gl_transactions",
                            "consumes": ["urn:dcs:..."],
                            "produces": [
                                "urn:dcs:...",
                                {"urn": "urn:dcs:...", "operation": "insert"}
                            ]
                        }
                    ]
                }
            ]
        }
        """
        pipelines = data.get("pipelines", [])

        for pipeline in pipelines:
            pipeline_id = pipeline.get("pipeline_id")
            instance = pipeline.get("instance", "default")

            if not pipeline_id:
                logger.warning("Pipeline missing pipeline_id, skipping")
                continue

            # Process tasks
            tasks = pipeline.get("tasks", [])
            for task in tasks:
                task_id = task.get("task_id")
                if not task_id:
                    logger.warning(f"Task in pipeline {pipeline_id} missing task_id, skipping")
                    continue

                # Build task URN
                # Format: urn:dcs:task:airflow:{instance}:{pipeline_id}.{task_id}
                task_urn = f"urn:dcs:task:airflow:{instance}:{pipeline_id}.{task_id}"

                # Parse data flow edges
                annotation = DataFlowAnnotation(task_urn=task_urn)

                # CONSUMES edges
                consumes_list = task.get("consumes", [])
                for item in consumes_list:
                    if isinstance(item, str):
                        annotation.consumes.append(item)
                    elif isinstance(item, dict):
                        urn = item.get("urn")
                        if urn:
                            annotation.consumes.append(urn)
                            if "access_pattern" in item:
                                annotation.access_patterns[urn] = item["access_pattern"]

                # PRODUCES edges
                produces_list = task.get("produces", [])
                for item in produces_list:
                    if isinstance(item, str):
                        annotation.produces.append(item)
                    elif isinstance(item, dict):
                        urn = item.get("urn")
                        if urn:
                            annotation.produces.append(urn)
                            if "operation" in item:
                                annotation.operations[urn] = item["operation"]

                # TRANSFORMS edges
                transforms_list = task.get("transforms", [])
                for item in transforms_list:
                    if isinstance(item, str):
                        annotation.transforms.append(item)
                    elif isinstance(item, dict):
                        urn = item.get("urn")
                        if urn:
                            annotation.transforms.append(urn)

                # VALIDATES edges
                validates_list = task.get("validates", [])
                for item in validates_list:
                    if isinstance(item, str):
                        annotation.validates.append(item)
                    elif isinstance(item, dict):
                        urn = item.get("urn")
                        if urn:
                            annotation.validates.append(urn)

                self._annotations[task_urn] = annotation

    def get_annotation(self, task_urn: str) -> Optional[DataFlowAnnotation]:
        """Get annotation for a task.

        Args:
            task_urn: Task URN

        Returns:
            DataFlowAnnotation or None
        """
        return self._annotations.get(task_urn)

    def has_annotation(self, task_urn: str) -> bool:
        """Check if task has annotation.

        Args:
            task_urn: Task URN

        Returns:
            True if annotation exists
        """
        return task_urn in self._annotations

    def get_all_annotations(self) -> dict[str, DataFlowAnnotation]:
        """Get all loaded annotations.

        Returns:
            Dict mapping task URN to DataFlowAnnotation
        """
        return self._annotations.copy()

    def validate_urns(self, valid_capsule_urns: set[str]) -> list[str]:
        """Validate that referenced capsule URNs exist.

        Args:
            valid_capsule_urns: Set of known capsule URNs

        Returns:
            List of warning messages for invalid URNs
        """
        warnings = []

        for task_urn, annotation in self._annotations.items():
            # Check all referenced capsule URNs
            all_refs = (
                annotation.consumes
                + annotation.produces
                + annotation.transforms
                + annotation.validates
            )

            for capsule_urn in all_refs:
                if capsule_urn not in valid_capsule_urns:
                    warnings.append(
                        f"Task {task_urn} references unknown capsule: {capsule_urn}"
                    )

        return warnings
