"""Airflow metadata parser for DAG definitions via REST API."""

import asyncio
import logging
from typing import Any, Optional
from urllib.parse import urljoin

import httpx

from src.parsers.base import (
    MetadataParser,
    ParseErrorSeverity,
    ParseResult,
    RawCapsule,
    RawEdge,
)
from src.parsers.airflow_config import AirflowParserConfig

logger = logging.getLogger(__name__)


class AirflowParser(MetadataParser):
    """Parser for Airflow DAG and task metadata via REST API.

    This parser connects to an Airflow REST API (v1) endpoint and extracts:
    - DAG definitions (metadata, schedule, owners, tags)
    - Task definitions (operator types, dependencies)
    - Task dependencies (upstream/downstream relationships)

    The parser is read-only and does not modify Airflow state.
    """

    @property
    def source_type(self) -> str:
        """Return source type identifier."""
        return "airflow"

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate Airflow parser configuration.

        Args:
            config: Configuration dictionary

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        if "base_url" not in config:
            errors.append("base_url is required")
            return errors

        try:
            parser_config = AirflowParserConfig.from_dict(config)
            errors.extend(parser_config.validate())
        except Exception as e:
            errors.append(f"Invalid configuration: {e}")

        return errors

    async def parse(self, config: dict[str, Any]) -> ParseResult:
        """Parse Airflow metadata via REST API.

        Args:
            config: Parser configuration dictionary

        Returns:
            ParseResult containing DAGs, tasks, and relationships
        """
        result = ParseResult(source_type=self.source_type)

        # Create typed configuration
        try:
            parser_config = AirflowParserConfig.from_dict(config)
        except Exception as e:
            result.add_error(
                f"Invalid configuration: {e}",
                severity=ParseErrorSeverity.ERROR,
            )
            return result

        # Validate configuration
        validation_errors = parser_config.validate()
        if validation_errors:
            for error in validation_errors:
                result.add_error(error, severity=ParseErrorSeverity.ERROR)
            return result

        # Set source name
        result.source_name = parser_config.instance_name

        # Fetch metadata via REST API
        async with httpx.AsyncClient(
            timeout=parser_config.timeout_seconds,
            follow_redirects=True,
        ) as client:
            # Get Airflow version (optional)
            version = await self._get_version(client, parser_config, result)
            if version:
                result.source_version = version
                logger.info(f"Connected to Airflow {version} at {parser_config.base_url}")

            # Fetch DAGs
            dags = await self._fetch_all_dags(client, parser_config, result)
            logger.info(f"Found {len(dags)} DAGs from {parser_config.instance_name}")

            # Process each DAG
            for dag_data in dags:
                await self._process_dag(client, parser_config, dag_data, result)

        logger.info(
            f"Parsed {len(result.capsules)} capsules and {len(result.edges)} edges "
            f"from Airflow instance: {parser_config.instance_name}"
        )

        return result

    async def _get_version(
        self,
        client: httpx.AsyncClient,
        config: AirflowParserConfig,
        result: ParseResult,
    ) -> Optional[str]:
        """Get Airflow version from API.

        Args:
            client: HTTP client
            config: Parser configuration
            result: Parse result for error reporting

        Returns:
            Airflow version string or None
        """
        try:
            url = urljoin(config.base_url, "/api/v1/version")
            response = await client.get(url, headers=config.get_auth_headers())
            response.raise_for_status()
            data = response.json()
            return data.get("version")
        except Exception as e:
            result.add_error(
                f"Failed to get Airflow version: {e}",
                severity=ParseErrorSeverity.WARNING,
            )
            return None

    async def _fetch_all_dags(
        self,
        client: httpx.AsyncClient,
        config: AirflowParserConfig,
        result: ParseResult,
    ) -> list[dict[str, Any]]:
        """Fetch all DAGs from Airflow API with pagination.

        Args:
            client: HTTP client
            config: Parser configuration
            result: Parse result for error reporting

        Returns:
            List of DAG data dictionaries
        """
        all_dags: list[dict[str, Any]] = []
        offset = 0

        try:
            while True:
                url = urljoin(
                    config.base_url,
                    f"/api/v1/dags?limit={config.page_limit}&offset={offset}",
                )
                response = await client.get(url, headers=config.get_auth_headers())
                response.raise_for_status()
                data = response.json()

                dags = data.get("dags", [])
                if not dags:
                    break

                # Filter DAGs based on configuration
                for dag in dags:
                    dag_id = dag.get("dag_id", "")
                    is_paused = dag.get("is_paused", False)
                    is_active = dag.get("is_active", True)

                    if config.should_include_dag(dag_id, is_paused, is_active):
                        all_dags.append(dag)

                # Check if we've reached the end
                if len(dags) < config.page_limit:
                    break

                offset += config.page_limit

        except httpx.HTTPStatusError as e:
            result.add_error(
                f"HTTP error fetching DAGs: {e.response.status_code} - {e.response.text}",
                severity=ParseErrorSeverity.ERROR,
            )
        except Exception as e:
            result.add_error(
                f"Error fetching DAGs: {e}",
                severity=ParseErrorSeverity.ERROR,
            )

        return all_dags

    async def _process_dag(
        self,
        client: httpx.AsyncClient,
        config: AirflowParserConfig,
        dag_data: dict[str, Any],
        result: ParseResult,
    ) -> None:
        """Process a single DAG and its tasks.

        Args:
            client: HTTP client
            config: Parser configuration
            dag_data: DAG metadata from API
            result: Parse result to populate
        """
        dag_id = dag_data.get("dag_id")
        if not dag_id:
            result.add_error(
                "DAG missing dag_id field",
                severity=ParseErrorSeverity.WARNING,
                context={"dag_data": dag_data},
            )
            return

        try:
            # Fetch detailed DAG info
            dag_detail = await self._fetch_dag_detail(client, config, dag_id)
            if dag_detail:
                # Merge list-view data with detail-view data
                dag_data = {**dag_data, **dag_detail}

            # Create DAG capsule
            dag_capsule = self._create_dag_capsule(config, dag_data)
            result.capsules.append(dag_capsule)

            # Extract domain from tags
            tags = dag_data.get("tags", [])
            if isinstance(tags, list):
                tag_dicts = []
                for tag in tags:
                    if isinstance(tag, dict):
                        tag_name = tag.get("name", "")
                    else:
                        tag_name = str(tag)
                    if tag_name:
                        tag_dicts.append(tag_name)

                domain_name = config.extract_domain_from_tags(tag_dicts)
                if domain_name:
                    dag_capsule.domain_name = domain_name

            # Fetch tasks for this DAG
            tasks = await self._fetch_dag_tasks(client, config, dag_id, result)

            # Create task capsules and relationships
            for task_data in tasks:
                task_capsule = self._create_task_capsule(config, dag_id, task_data)
                result.capsules.append(task_capsule)

                # Create DAG → Task containment edge
                contains_edge = RawEdge(
                    source_urn=dag_capsule.urn,
                    target_urn=task_capsule.urn,
                    edge_type="contains",
                    meta={"dag_id": dag_id, "relationship": "dag_contains_task"},
                )
                result.edges.append(contains_edge)

                # Create Task → Task dependency edges
                downstream_task_ids = task_data.get("downstream_task_ids", [])
                for downstream_id in downstream_task_ids:
                    downstream_urn = self._build_task_urn(config, dag_id, downstream_id)
                    dependency_edge = RawEdge(
                        source_urn=task_capsule.urn,
                        target_urn=downstream_urn,
                        edge_type="flows_to",
                        meta={
                            "dag_id": dag_id,
                            "dependency_type": "direct",
                        },
                    )
                    result.edges.append(dependency_edge)

        except Exception as e:
            result.add_error(
                f"Error processing DAG {dag_id}: {e}",
                severity=ParseErrorSeverity.WARNING,
                location=dag_id,
            )

    async def _fetch_dag_detail(
        self,
        client: httpx.AsyncClient,
        config: AirflowParserConfig,
        dag_id: str,
    ) -> Optional[dict[str, Any]]:
        """Fetch detailed DAG information.

        Args:
            client: HTTP client
            config: Parser configuration
            dag_id: DAG identifier

        Returns:
            DAG detail dictionary or None
        """
        try:
            url = urljoin(config.base_url, f"/api/v1/dags/{dag_id}")
            response = await client.get(url, headers=config.get_auth_headers())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.debug(f"Failed to fetch detail for DAG {dag_id}: {e}")
            return None

    async def _fetch_dag_tasks(
        self,
        client: httpx.AsyncClient,
        config: AirflowParserConfig,
        dag_id: str,
        result: ParseResult,
    ) -> list[dict[str, Any]]:
        """Fetch all tasks for a DAG.

        Args:
            client: HTTP client
            config: Parser configuration
            dag_id: DAG identifier
            result: Parse result for error reporting

        Returns:
            List of task data dictionaries
        """
        try:
            # Note: The /dags/{dag_id}/tasks endpoint does not support pagination
            # parameters (limit/offset) and returns all tasks at once
            url = urljoin(
                config.base_url,
                f"/api/v1/dags/{dag_id}/tasks",
            )
            response = await client.get(url, headers=config.get_auth_headers())
            response.raise_for_status()
            data = response.json()

            return data.get("tasks", [])

        except Exception as e:
            result.add_error(
                f"Error fetching tasks for DAG {dag_id}: {e}",
                severity=ParseErrorSeverity.WARNING,
                location=dag_id,
            )
            return []

    def _create_dag_capsule(
        self,
        config: AirflowParserConfig,
        dag_data: dict[str, Any],
    ) -> RawCapsule:
        """Create a capsule for an Airflow DAG.

        Args:
            config: Parser configuration
            dag_data: DAG metadata from API

        Returns:
            RawCapsule for the DAG
        """
        dag_id = dag_data["dag_id"]
        urn = f"{config.urn_prefix}:dag:{config.instance_name}:{dag_id}"

        # Extract metadata
        description = dag_data.get("description") or ""
        owners = dag_data.get("owners", [])
        schedule_interval = dag_data.get("schedule_interval")
        is_paused = dag_data.get("is_paused", False)
        is_active = dag_data.get("is_active", True)

        # Extract tags
        tags = []
        tag_list = dag_data.get("tags", [])
        if isinstance(tag_list, list):
            for tag in tag_list:
                if isinstance(tag, dict):
                    tag_name = tag.get("name", "")
                else:
                    tag_name = str(tag)
                if tag_name:
                    tags.append(tag_name)

        # Build metadata dictionary
        meta = {
            "dag_id": dag_id,
            "schedule_interval": schedule_interval,
            "is_paused": is_paused,
            "is_active": is_active,
            "owners": owners,
            "fileloc": dag_data.get("fileloc"),
            "file_token": dag_data.get("file_token"),
            "start_date": dag_data.get("start_date"),
            "end_date": dag_data.get("end_date"),
            "catchup": dag_data.get("catchup"),
            "max_active_runs": dag_data.get("max_active_runs"),
            "max_active_tasks": dag_data.get("max_active_tasks"),
            "last_parsed_time": dag_data.get("last_parsed_time"),
            "last_pickled": dag_data.get("last_pickled"),
            "last_expired": dag_data.get("last_expired"),
        }

        # Remove None values
        meta = {k: v for k, v in meta.items() if v is not None}

        return RawCapsule(
            urn=urn,
            name=dag_id,
            capsule_type="airflow_dag",
            unique_id=f"{config.instance_name}:{dag_id}",
            description=description,
            tags=tags,
            meta=meta,
        )

    def _create_task_capsule(
        self,
        config: AirflowParserConfig,
        dag_id: str,
        task_data: dict[str, Any],
    ) -> RawCapsule:
        """Create a capsule for an Airflow task.

        Args:
            config: Parser configuration
            dag_id: Parent DAG identifier
            task_data: Task metadata from API

        Returns:
            RawCapsule for the task
        """
        task_id = task_data["task_id"]
        urn = self._build_task_urn(config, dag_id, task_id)

        # Extract metadata
        operator = task_data.get("operator_name") or task_data.get("task_type", "")

        # Build metadata dictionary
        meta = {
            "dag_id": dag_id,
            "task_id": task_id,
            "operator": operator,
            "retries": task_data.get("retries"),
            "retry_delay": task_data.get("retry_delay"),
            "execution_timeout": task_data.get("execution_timeout"),
            "queue": task_data.get("queue"),
            "pool": task_data.get("pool"),
            "priority_weight": task_data.get("priority_weight"),
            "trigger_rule": task_data.get("trigger_rule"),
            "weight_rule": task_data.get("weight_rule"),
        }

        # Remove None values
        meta = {k: v for k, v in meta.items() if v is not None}

        # Get documentation
        doc_md = task_data.get("doc_md") or task_data.get("doc") or ""

        return RawCapsule(
            urn=urn,
            name=task_id,
            capsule_type="airflow_task",
            unique_id=f"{config.instance_name}:{dag_id}.{task_id}",
            description=doc_md,
            meta=meta,
        )

    def _build_task_urn(
        self,
        config: AirflowParserConfig,
        dag_id: str,
        task_id: str,
    ) -> str:
        """Build a URN for a task.

        Args:
            config: Parser configuration
            dag_id: Parent DAG identifier
            task_id: Task identifier

        Returns:
            Task URN string
        """
        return f"{config.urn_prefix}:task:{config.instance_name}:{dag_id}.{task_id}"
