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
    RawOrchestrationEdge,
    RawPipeline,
    RawPipelineTask,
)
from src.parsers.airflow_config import AirflowParserConfig
from src.parsers.data_flow_annotations import DataFlowAnnotationLoader
from src.parsers.dbt_manifest_resolver import DbtManifestResolver
from src.parsers.sql_parser import parse_sql, match_table_to_capsule_urn

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

        # Initialize Phase 3 data flow loaders
        annotation_loader: Optional[DataFlowAnnotationLoader] = None
        logger.info(f"Parser config annotation_file: {parser_config.annotation_file}")
        if parser_config.annotation_file:
            logger.info(f"Loading annotations from: {parser_config.annotation_file}")
            annotation_loader = DataFlowAnnotationLoader(parser_config.annotation_file)
            if not annotation_loader.load_annotations():
                result.add_error(
                    f"Failed to load annotation file: {parser_config.annotation_file}",
                    severity=ParseErrorSeverity.WARNING,
                )
                annotation_loader = None
            else:
                logger.info(f"Successfully loaded {len(annotation_loader.get_all_annotations())} task annotations")

        dbt_resolver: Optional[DbtManifestResolver] = None
        if parser_config.dbt_manifest_path:
            dbt_resolver = DbtManifestResolver(parser_config.dbt_manifest_path)
            if not dbt_resolver.load_manifest():
                result.add_error(
                    f"Failed to load dbt manifest: {parser_config.dbt_manifest_path}",
                    severity=ParseErrorSeverity.WARNING,
                )
                dbt_resolver = None

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
                await self._process_dag(
                    client,
                    parser_config,
                    dag_data,
                    result,
                    annotation_loader,
                    dbt_resolver,
                )

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
        annotation_loader: Optional[DataFlowAnnotationLoader] = None,
        dbt_resolver: Optional[DbtManifestResolver] = None,
    ) -> None:
        """Process a single DAG and its tasks.

        Args:
            client: HTTP client
            config: Parser configuration
            dag_data: DAG metadata from API
            result: Parse result to populate
            annotation_loader: Manual annotation loader (Phase 3)
            dbt_resolver: dbt manifest resolver (Phase 3)
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

            # Create DAG pipeline (NOT a capsule)
            dag_pipeline = self._create_dag_pipeline(config, dag_data)
            result.pipelines.append(dag_pipeline)

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
                    dag_pipeline.domain_name = domain_name

            # Fetch tasks for this DAG
            tasks = await self._fetch_dag_tasks(client, config, dag_id, result)

            # Create pipeline tasks and relationships
            for task_data in tasks:
                # Create pipeline task (NOT a capsule)
                pipeline_task = self._create_task(config, dag_id, task_data, dag_pipeline.urn)
                result.pipeline_tasks.append(pipeline_task)

                # Create Pipeline → Task CONTAINS edge (orchestration-to-orchestration)
                contains_edge = RawOrchestrationEdge(
                    source_urn=dag_pipeline.urn,
                    target_urn=pipeline_task.urn,
                    edge_category="task_dependency",
                    edge_type="contains",
                    meta={"dag_id": dag_id, "relationship": "pipeline_contains_task"},
                )
                result.orchestration_edges.append(contains_edge)

                # Create Task → Task DEPENDS_ON edges (orchestration-to-orchestration)
                downstream_task_ids = task_data.get("downstream_task_ids", [])
                for downstream_id in downstream_task_ids:
                    downstream_urn = f"urn:dcs:task:airflow:{config.instance_name}:{dag_id}.{downstream_id}"
                    dependency_edge = RawOrchestrationEdge(
                        source_urn=pipeline_task.urn,
                        target_urn=downstream_urn,
                        edge_category="task_dependency",
                        edge_type="depends_on",
                        meta={
                            "dag_id": dag_id,
                            "dependency_type": "direct",
                        },
                    )
                    result.orchestration_edges.append(dependency_edge)

                # Phase 3: Extract data flow (Task → DataCapsule edges)
                self._extract_data_flow(
                    task_data=task_data,
                    config=config,
                    task=pipeline_task,
                    result=result,
                    annotation_loader=annotation_loader,
                    dbt_resolver=dbt_resolver,
                )

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

    def _create_dag_pipeline(
        self,
        config: AirflowParserConfig,
        dag_data: dict[str, Any],
    ) -> RawPipeline:
        """Create a RawPipeline for an Airflow DAG.

        Args:
            config: Parser configuration
            dag_data: DAG metadata from API

        Returns:
            RawPipeline for the DAG
        """
        dag_id = dag_data["dag_id"]
        urn = f"urn:dcs:pipeline:airflow:{config.instance_name}:{dag_id}"

        # Extract metadata
        description = dag_data.get("description") or ""
        owners = dag_data.get("owners", [])

        # Handle schedule_interval (can be string or dict with __type/value)
        schedule_interval_raw = dag_data.get("schedule_interval")
        if isinstance(schedule_interval_raw, dict):
            schedule_interval = schedule_interval_raw.get("value")
        else:
            schedule_interval = schedule_interval_raw

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

        # Build metadata dictionary for additional fields
        meta = {
            "dag_id": dag_id,
            "file_token": dag_data.get("file_token"),
            "fileloc": dag_data.get("fileloc"),
            "catchup": dag_data.get("catchup"),
            "max_active_tasks": dag_data.get("max_active_tasks"),
            "max_active_runs": dag_data.get("max_active_runs"),
            "has_task_concurrency_limits": dag_data.get("has_task_concurrency_limits"),
            "has_import_errors": dag_data.get("has_import_errors"),
            "next_dagrun": dag_data.get("next_dagrun"),
            "next_dagrun_data_interval_start": dag_data.get("next_dagrun_data_interval_start"),
            "next_dagrun_data_interval_end": dag_data.get("next_dagrun_data_interval_end"),
            "next_dagrun_create_after": dag_data.get("next_dagrun_create_after"),
        }
        # Remove None values
        meta = {k: v for k, v in meta.items() if v is not None}

        # Build config dictionary
        config_dict = {
            "catchup": dag_data.get("catchup"),
            "max_active_tasks": dag_data.get("max_active_tasks"),
            "max_active_runs": dag_data.get("max_active_runs"),
            "has_task_concurrency_limits": dag_data.get("has_task_concurrency_limits"),
        }
        config_dict = {k: v for k, v in config_dict.items() if v is not None}

        return RawPipeline(
            urn=urn,
            name=dag_id,
            pipeline_type="airflow_dag",
            source_system_identifier=dag_id,
            description=description,
            schedule_interval=schedule_interval,
            owners=owners,
            is_paused=is_paused,
            is_active=is_active,
            tags=tags,
            meta=meta,
            config=config_dict,
        )

    def _create_task(
        self,
        config: AirflowParserConfig,
        dag_id: str,
        task_data: dict[str, Any],
        pipeline_urn: str,
    ) -> RawPipelineTask:
        """Create a RawPipelineTask for an Airflow task.

        Args:
            config: Parser configuration
            dag_id: DAG identifier
            task_data: Task metadata from API
            pipeline_urn: URN of parent pipeline

        Returns:
            RawPipelineTask for the task
        """
        task_id = task_data["task_id"]
        urn = f"urn:dcs:task:airflow:{config.instance_name}:{dag_id}.{task_id}"

        # Extract operator class
        operator = task_data.get("operator_name") or task_data.get("class_ref", {}).get("class_name", "")

        # Map operator to task type
        task_type = self._map_operator_to_task_type(operator)

        # Map operator to operation type
        operation_type = self._infer_operation_type(operator, task_id)

        # Extract retry configuration
        retries = task_data.get("retries", 0)
        retry_delay_dict = task_data.get("retry_delay")
        retry_delay_seconds = None
        if retry_delay_dict and isinstance(retry_delay_dict, dict):
            # Airflow returns retry_delay as {"__type": "TimeDelta", "__var": {"days": 0, "seconds": 300}}
            var_dict = retry_delay_dict.get("__var", {})
            retry_delay_seconds = var_dict.get("days", 0) * 86400 + var_dict.get("seconds", 0)

        # Extract timeout
        timeout_dict = task_data.get("execution_timeout")
        timeout_seconds = None
        if timeout_dict and isinstance(timeout_dict, dict):
            var_dict = timeout_dict.get("__var", {})
            timeout_seconds = var_dict.get("days", 0) * 86400 + var_dict.get("seconds", 0)

        # Build metadata dictionary
        meta = {
            "task_id": task_id,
            "dag_id": dag_id,
            "operator": operator,
            "owner": task_data.get("owner"),
            "start_date": task_data.get("start_date"),
            "end_date": task_data.get("end_date"),
            "depends_on_past": task_data.get("depends_on_past"),
            "wait_for_downstream": task_data.get("wait_for_downstream"),
            "priority_weight": task_data.get("priority_weight"),
            "weight_rule": task_data.get("weight_rule"),
            "queue": task_data.get("queue"),
            "pool": task_data.get("pool"),
            "pool_slots": task_data.get("pool_slots"),
            "trigger_rule": task_data.get("trigger_rule"),
        }
        # Remove None values
        meta = {k: v for k, v in meta.items() if v is not None}

        # Extract UI color/fgcolor
        ui_color = task_data.get("ui_color")
        ui_fgcolor = task_data.get("ui_fgcolor")
        if ui_color:
            meta["ui_color"] = ui_color
        if ui_fgcolor:
            meta["ui_fgcolor"] = ui_fgcolor

        return RawPipelineTask(
            urn=urn,
            name=task_id,
            task_type=task_type,
            pipeline_urn=pipeline_urn,
            description=None,  # Airflow API doesn't provide task descriptions
            operator=operator,
            operation_type=operation_type,
            retries=retries,
            retry_delay_seconds=retry_delay_seconds,
            timeout_seconds=timeout_seconds,
            tool_reference=None,  # TODO: Could be enhanced for DbtOperator, etc.
            meta=meta,
        )

    def _map_operator_to_task_type(self, operator: str) -> str:
        """Map Airflow operator to task type.

        Args:
            operator: Airflow operator class name

        Returns:
            Task type string
        """
        operator_lower = operator.lower()
        if "python" in operator_lower:
            return "python"
        elif "bash" in operator_lower:
            return "bash"
        elif any(sql_op in operator_lower for sql_op in ["sql", "postgres", "mysql", "snowflake", "bigquery"]):
            return "sql"
        elif "dbt" in operator_lower:
            return "dbt"
        elif "spark" in operator_lower:
            return "spark"
        elif "sensor" in operator_lower:
            return "sensor"
        elif "trigger" in operator_lower:
            return "trigger"
        else:
            return "custom"

    def _infer_operation_type(self, operator: str, task_id: str) -> str:
        """Infer operation type from operator and task_id.

        Args:
            operator: Airflow operator class name
            task_id: Task identifier

        Returns:
            Operation type string
        """
        combined = f"{operator.lower()} {task_id.lower()}"

        if any(keyword in combined for keyword in ["extract", "fetch", "get", "read", "pull"]):
            return "extract"
        elif any(keyword in combined for keyword in ["load", "write", "insert", "upload", "push"]):
            return "load"
        elif any(keyword in combined for keyword in ["transform", "process", "compute", "calculate", "dbt"]):
            return "transform"
        elif any(keyword in combined for keyword in ["validate", "check", "test", "quality"]):
            return "validate"
        elif any(keyword in combined for keyword in ["aggregate", "sum", "count", "group"]):
            return "aggregate"
        elif any(keyword in combined for keyword in ["join", "merge"]):
            return "join"
        elif any(keyword in combined for keyword in ["filter", "where"]):
            return "filter"
        else:
            return "unknown"

    # Phase 3: Data Flow Mapping Methods

    def _extract_data_flow(
        self,
        task_data: dict[str, Any],
        config: AirflowParserConfig,
        task: RawPipelineTask,
        result: ParseResult,
        annotation_loader: Optional[DataFlowAnnotationLoader],
        dbt_resolver: Optional[DbtManifestResolver],
    ) -> None:
        """Extract data flow edges for a task (Phase 3).

        Attempts data flow detection in priority order:
        1. Manual annotations (highest priority)
        2. dbt integration for DbtOperator
        3. SQL parsing for SQL operators

        Args:
            task_data: Task metadata from Airflow API
            config: Parser configuration
            task: RawPipelineTask object
            result: Parse result to populate
            annotation_loader: Manual annotation loader
            dbt_resolver: dbt manifest resolver
        """
        operator = task.operator or ""

        try:
            # 1. Check manual annotations first (highest priority)
            if annotation_loader and annotation_loader.has_annotation(task.urn):
                annotation = annotation_loader.get_annotation(task.urn)
                self._create_edges_from_annotations(task, annotation, result)
                logger.debug(f"Created data flow from annotations for task: {task.urn}")
                return

            # 2. Try dbt integration
            if "dbt" in operator.lower() and dbt_resolver:
                self._extract_dbt_data_flow(task_data, config, task, result, dbt_resolver)
                return

            # 3. Try SQL parsing
            if config.enable_sql_parsing and any(
                op in operator.lower()
                for op in ["sql", "postgres", "mysql", "snowflake", "bigquery", "redshift"]
            ):
                self._extract_sql_data_flow(task_data, config, task, result)
                return

        except Exception as e:
            result.add_error(
                f"Error extracting data flow for task {task.urn}: {e}",
                severity=ParseErrorSeverity.WARNING,
                location=task.urn,
            )

    def _create_edges_from_annotations(
        self,
        task: RawPipelineTask,
        annotation: Any,  # DataFlowAnnotation type
        result: ParseResult,
    ) -> None:
        """Create data flow edges from manual annotations.

        Args:
            task: Pipeline task
            annotation: DataFlowAnnotation with consumes/produces/etc.
            result: Parse result to populate
        """
        # CONSUMES edges (capsule → task)
        for capsule_urn in annotation.consumes:
            edge = RawOrchestrationEdge(
                source_urn=capsule_urn,
                target_urn=task.urn,
                edge_category="task_data",
                edge_type="consumes",
                meta={
                    "source": "manual_annotation",
                    "access_pattern": annotation.access_patterns.get(capsule_urn),
                },
            )
            result.orchestration_edges.append(edge)

        # PRODUCES edges
        for capsule_urn in annotation.produces:
            edge = RawOrchestrationEdge(
                source_urn=task.urn,
                target_urn=capsule_urn,
                edge_category="task_data",
                edge_type="produces",
                meta={
                    "source": "manual_annotation",
                    "operation": annotation.operations.get(capsule_urn),
                },
            )
            result.orchestration_edges.append(edge)

        # TRANSFORMS edges
        for capsule_urn in annotation.transforms:
            edge = RawOrchestrationEdge(
                source_urn=task.urn,
                target_urn=capsule_urn,
                edge_category="task_data",
                edge_type="transforms",
                meta={"source": "manual_annotation"},
            )
            result.orchestration_edges.append(edge)

        # VALIDATES edges
        for capsule_urn in annotation.validates:
            edge = RawOrchestrationEdge(
                source_urn=task.urn,
                target_urn=capsule_urn,
                edge_category="task_data",
                edge_type="validates",
                meta={"source": "manual_annotation"},
            )
            result.orchestration_edges.append(edge)

    def _extract_dbt_data_flow(
        self,
        task_data: dict[str, Any],
        config: AirflowParserConfig,
        task: RawPipelineTask,
        result: ParseResult,
        dbt_resolver: DbtManifestResolver,
    ) -> None:
        """Extract data flow from dbt operator configuration.

        Args:
            task_data: Task metadata from Airflow API
            config: Parser configuration
            task: Pipeline task
            result: Parse result to populate
            dbt_resolver: dbt manifest resolver
        """
        try:
            # Extract dbt configuration from task metadata
            # Note: Airflow API doesn't expose full operator config, so we'll try to infer
            # In practice, this would work better with DAG file parsing or custom metadata
            operator_config = {}

            # Try to get select/models from task metadata if available
            # This is a simplified version - real implementation may need DAG file access
            task_meta = task_data.get("params") or task_data.get("extra_links") or {}

            if "select" in task_meta:
                operator_config["select"] = task_meta["select"]
            elif "models" in task_meta:
                operator_config["models"] = task_meta["models"]

            # If we can't extract config, try to use task_id as model name
            if not operator_config:
                # Attempt to use task_id as model selector
                task_id = task.name
                # Remove common prefixes like "dbt_run_", "dbt_test_"
                model_name = task_id.replace("dbt_run_", "").replace("dbt_test_", "").replace("dbt_", "")
                operator_config["select"] = model_name

            # Extract dbt models from config
            dbt_info = dbt_resolver.extract_from_operator_config(operator_config)
            models = dbt_info.get("models", [])
            operation_type = dbt_info.get("operation_type", "merge")

            # Create PRODUCES edges for each dbt model
            project_name = config.dbt_project_name or "default"
            for model_name in models:
                model = dbt_resolver.get_model_by_name(model_name)
                if model:
                    capsule_urn = dbt_resolver.model_to_capsule_urn(model, project_name)
                    edge = RawOrchestrationEdge(
                        source_urn=task.urn,
                        target_urn=capsule_urn,
                        edge_category="task_data",
                        edge_type="produces",
                        meta={
                            "source": "dbt_manifest",
                            "operation": operation_type,
                            "dbt_model": model_name,
                            "materialization": model.materialization,
                        },
                    )
                    result.orchestration_edges.append(edge)
                    logger.debug(f"Created dbt PRODUCES edge: {task.urn} -> {capsule_urn}")

                    # Create CONSUMES edges for upstream dbt dependencies
                    for upstream_id in model.depends_on:
                        if upstream_id.startswith("model."):
                            # This is another dbt model - create CONSUMES edge
                            upstream_model = dbt_resolver._models_cache.get(upstream_id)
                            if upstream_model:
                                upstream_urn = dbt_resolver.model_to_capsule_urn(upstream_model, project_name)
                                consumes_edge = RawOrchestrationEdge(
                                    source_urn=upstream_urn,
                                    target_urn=task.urn,
                                    edge_category="task_data",
                                    edge_type="consumes",
                                    meta={
                                        "source": "dbt_manifest",
                                        "dbt_dependency": upstream_id,
                                    },
                                )
                                result.orchestration_edges.append(consumes_edge)

        except Exception as e:
            logger.debug(f"Failed to extract dbt data flow for task {task.urn}: {e}")

    def _extract_sql_data_flow(
        self,
        task_data: dict[str, Any],
        config: AirflowParserConfig,
        task: RawPipelineTask,
        result: ParseResult,
    ) -> None:
        """Extract data flow from SQL operator using SQL parsing.

        Args:
            task_data: Task metadata from Airflow API
            config: Parser configuration
            task: Pipeline task
            result: Parse result to populate
        """
        try:
            # Try to extract SQL from task metadata
            # Note: Airflow API doesn't always expose full SQL, this is best-effort
            sql_text = None

            # Check various possible locations for SQL
            if "sql" in task_data:
                sql_text = task_data["sql"]
            elif "params" in task_data and isinstance(task_data["params"], dict):
                sql_text = task_data["params"].get("sql")

            if not sql_text or not isinstance(sql_text, str):
                # Can't extract SQL from API - would need DAG file access
                logger.debug(f"No SQL found in task metadata for {task.urn}")
                return

            # Parse SQL to extract table references (capsule-level lineage)
            parse_result = parse_sql(sql_text, dialect=config.sql_parser_dialect)

            if not parse_result.is_valid:
                logger.debug(f"Failed to parse SQL for task {task.urn}: {parse_result.errors}")
                return

            # Create CONSUMES edges for tables read
            for table_ref in parse_result.reads:
                capsule_urn = match_table_to_capsule_urn(
                    table_ref,
                    known_urns=[],  # TODO: Could pass known capsule URNs for matching
                    default_source="postgres",  # Use source from operator name if available
                )
                if capsule_urn:
                    edge = RawOrchestrationEdge(
                        source_urn=capsule_urn,
                        target_urn=task.urn,
                        edge_category="task_data",
                        edge_type="consumes",
                        meta={
                            "source": "sql_parsing",
                            "table_name": table_ref.qualified_name,
                            "sql_dialect": config.sql_parser_dialect,
                        },
                    )
                    result.orchestration_edges.append(edge)
                    logger.debug(f"Created SQL CONSUMES edge: {capsule_urn} -> {task.urn}")

            # Create PRODUCES edges for tables written
            for table_ref in parse_result.writes:
                capsule_urn = match_table_to_capsule_urn(
                    table_ref,
                    known_urns=[],
                    default_source="postgres",
                )
                if capsule_urn:
                    edge = RawOrchestrationEdge(
                        source_urn=task.urn,
                        target_urn=capsule_urn,
                        edge_category="task_data",
                        edge_type="produces",
                        meta={
                            "source": "sql_parsing",
                            "operation": parse_result.operation_type,
                            "table_name": table_ref.qualified_name,
                            "sql_dialect": config.sql_parser_dialect,
                        },
                    )
                    result.orchestration_edges.append(edge)
                    logger.debug(f"Created SQL PRODUCES edge: {task.urn} -> {capsule_urn}")

            # Phase 6: Extract column-level lineage from SQL
            self._extract_column_lineage_from_sql(
                sql_text=sql_text,
                task_urn=task.urn,
                dialect=config.sql_parser_dialect,
                result=result,
            )

        except Exception as e:
            logger.debug(f"Failed to extract SQL data flow for task {task.urn}: {e}")

    def _extract_column_lineage_from_sql(
        self,
        sql_text: str,
        task_urn: str,
        dialect: str,
        result: ParseResult,
    ) -> None:
        """Extract column-level lineage from SQL using SQL Column Parser (Phase 6).

        Args:
            sql_text: SQL query text
            task_urn: URN of the task executing this SQL
            dialect: SQL dialect (postgres, mysql, snowflake, etc.)
            result: Parse result to populate
        """
        try:
            from src.parsers.sql_column_parser import SQLColumnParser
            from src.parsers.base import RawColumnMapping

            # Initialize column parser
            column_parser = SQLColumnParser(dialect=dialect)

            # Parse SELECT statements for column mappings
            column_mappings = column_parser.parse_select_statement(sql_text)

            # If no SELECT mappings, try INSERT
            if not column_mappings:
                column_mappings = column_parser.parse_insert_statement(sql_text)

            # If still no mappings, try UPDATE
            if not column_mappings:
                column_mappings = column_parser.parse_update_statement(sql_text)

            # Convert ColumnMapping objects to RawColumnMapping and add to result
            for mapping in column_mappings:
                raw_mapping = RawColumnMapping(
                    source_columns=mapping.source_columns,
                    target_column=mapping.target_column,
                    transformation_type=mapping.transformation_type,
                    transformation_logic=mapping.transformation_logic,
                    confidence=mapping.confidence,
                    detected_by=mapping.detected_by,
                    task_urn=task_urn,
                    meta={
                        "sql_dialect": dialect,
                    },
                )
                result.column_mappings.append(raw_mapping)

            if column_mappings:
                logger.debug(
                    f"Extracted {len(column_mappings)} column mappings from SQL for task: {task_urn}"
                )

        except Exception as e:
            logger.debug(f"Failed to extract column lineage from SQL for task {task_urn}: {e}")
