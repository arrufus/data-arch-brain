"""Ingestion service for orchestrating metadata parsing and persistence."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.capsule import Capsule
from src.models.column import Column
from src.models.ingestion import IngestionJob, IngestionStatus
from src.models.lineage import CapsuleLineage, ColumnLineage
from src.models.orchestration_edge import (
    OrchestrationEdgeType,
    PipelineTriggerEdge,
    TaskDataEdge,
    TaskDependencyEdge,
)
from src.models.pipeline import (
    Pipeline,
    PipelineRun,
    PipelineTask,
    PipelineType,
    TaskRun,
)
from src.parsers import DbtParser, ParseResult, get_parser
from src.repositories import (
    CapsuleLineageRepository,
    CapsuleRepository,
    ColumnLineageRepository,
    ColumnRepository,
    DomainRepository,
    IngestionJobRepository,
    SourceSystemRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class ProcessedUrns:
    """URNs processed during ingestion for orphan detection."""
    capsule_urns: set[str] = field(default_factory=set)
    column_urns: set[str] = field(default_factory=set)
    edge_keys: set[tuple[str, str]] = field(default_factory=set)  # (source_urn, target_urn)
    column_edge_keys: set[tuple[str, str]] = field(default_factory=set)  # (source_col_urn, target_col_urn)
    # Orchestration metadata (Airflow Integration)
    pipeline_urns: set[str] = field(default_factory=set)
    pipeline_task_urns: set[str] = field(default_factory=set)
    orchestration_edge_keys: set[tuple[str, str]] = field(default_factory=set)  # (source_urn, target_urn)


@dataclass
class IngestionStats:
    """Statistics from an ingestion run."""

    capsules_created: int = 0
    capsules_updated: int = 0
    capsules_unchanged: int = 0
    capsules_deleted: int = 0
    columns_created: int = 0
    columns_updated: int = 0
    columns_deleted: int = 0
    edges_created: int = 0
    edges_updated: int = 0
    edges_deleted: int = 0
    column_edges_created: int = 0
    column_edges_updated: int = 0
    column_edges_deleted: int = 0
    domains_created: int = 0
    pii_columns_detected: int = 0
    # Orchestration metadata (Airflow Integration)
    pipelines_created: int = 0
    pipelines_updated: int = 0
    pipelines_deleted: int = 0
    pipeline_tasks_created: int = 0
    pipeline_tasks_updated: int = 0
    pipeline_tasks_deleted: int = 0
    orchestration_edges_created: int = 0
    orchestration_edges_updated: int = 0
    orchestration_edges_deleted: int = 0
    warnings: int = 0
    errors: int = 0

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary."""
        return {
            "capsules_created": self.capsules_created,
            "capsules_updated": self.capsules_updated,
            "capsules_unchanged": self.capsules_unchanged,
            "capsules_deleted": self.capsules_deleted,
            "columns_created": self.columns_created,
            "columns_updated": self.columns_updated,
            "columns_deleted": self.columns_deleted,
            "edges_created": self.edges_created,
            "edges_updated": self.edges_updated,
            "edges_deleted": self.edges_deleted,
            "column_edges_created": self.column_edges_created,
            "column_edges_updated": self.column_edges_updated,
            "column_edges_deleted": self.column_edges_deleted,
            "domains_created": self.domains_created,
            "pii_columns_detected": self.pii_columns_detected,
            "pipelines_created": self.pipelines_created,
            "pipelines_updated": self.pipelines_updated,
            "pipelines_deleted": self.pipelines_deleted,
            "pipeline_tasks_created": self.pipeline_tasks_created,
            "pipeline_tasks_updated": self.pipeline_tasks_updated,
            "pipeline_tasks_deleted": self.pipeline_tasks_deleted,
            "orchestration_edges_created": self.orchestration_edges_created,
            "orchestration_edges_updated": self.orchestration_edges_updated,
            "orchestration_edges_deleted": self.orchestration_edges_deleted,
            "warnings": self.warnings,
            "errors": self.errors,
        }

    @property
    def total_changes(self) -> int:
        """Total number of changes (creates + updates + deletes)."""
        return (
            self.capsules_created + self.capsules_updated + self.capsules_deleted +
            self.columns_created + self.columns_updated + self.columns_deleted +
            self.edges_created + self.edges_updated + self.edges_deleted +
            self.column_edges_created + self.column_edges_updated + self.column_edges_deleted +
            self.pipelines_created + self.pipelines_updated + self.pipelines_deleted +
            self.pipeline_tasks_created + self.pipeline_tasks_updated + self.pipeline_tasks_deleted +
            self.orchestration_edges_created + self.orchestration_edges_updated + self.orchestration_edges_deleted
        )

    def delta_summary(self) -> dict[str, dict[str, int]]:
        """Get delta summary grouped by entity type."""
        return {
            "capsules": {
                "created": self.capsules_created,
                "updated": self.capsules_updated,
                "deleted": self.capsules_deleted,
            },
            "columns": {
                "created": self.columns_created,
                "updated": self.columns_updated,
                "deleted": self.columns_deleted,
            },
            "edges": {
                "created": self.edges_created,
                "updated": self.edges_updated,
                "deleted": self.edges_deleted,
            },
            "column_edges": {
                "created": self.column_edges_created,
                "updated": self.column_edges_updated,
                "deleted": self.column_edges_deleted,
            },
            "pipelines": {
                "created": self.pipelines_created,
                "updated": self.pipelines_updated,
                "deleted": self.pipelines_deleted,
            },
            "pipeline_tasks": {
                "created": self.pipeline_tasks_created,
                "updated": self.pipeline_tasks_updated,
                "deleted": self.pipeline_tasks_deleted,
            },
            "orchestration_edges": {
                "created": self.orchestration_edges_created,
                "updated": self.orchestration_edges_updated,
                "deleted": self.orchestration_edges_deleted,
            },
        }


@dataclass
class IngestionResult:
    """Result of an ingestion operation."""

    job_id: UUID
    status: IngestionStatus
    source_type: str
    source_name: Optional[str] = None
    stats: IngestionStats = field(default_factory=IngestionStats)
    error_message: Optional[str] = None
    error_details: Optional[dict] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get duration in seconds."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class IngestionService:
    """Service for ingesting metadata from various sources."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.job_repo = IngestionJobRepository(session)
        self.capsule_repo = CapsuleRepository(session)
        self.column_repo = ColumnRepository(session)
        self.lineage_repo = CapsuleLineageRepository(session)
        self.column_lineage_repo = ColumnLineageRepository(session)
        self.domain_repo = DomainRepository(session)
        self.source_system_repo = SourceSystemRepository(session)

    async def ingest_dbt(
        self,
        manifest_path: str,
        catalog_path: Optional[str] = None,
        project_name: Optional[str] = None,
        cleanup_orphans: bool = False,
    ) -> IngestionResult:
        """
        Ingest dbt metadata from manifest and catalog files.

        Args:
            manifest_path: Path to manifest.json
            catalog_path: Optional path to catalog.json
            project_name: Optional project name override
            cleanup_orphans: If True, delete capsules/columns not in current parse

        Returns:
            IngestionResult with job details and statistics
        """
        config = {
            "manifest_path": manifest_path,
            "catalog_path": catalog_path,
            "project_name": project_name,
        }

        return await self.ingest("dbt", config, cleanup_orphans=cleanup_orphans)

    async def ingest_airflow(
        self,
        base_url: str,
        instance_name: Optional[str] = None,
        auth_mode: str = "none",
        dag_id_allowlist: Optional[list[str]] = None,
        dag_id_denylist: Optional[list[str]] = None,
        dag_id_regex: Optional[str] = None,
        include_paused: bool = False,
        include_inactive: bool = False,
        cleanup_orphans: bool = False,
        **kwargs: Any,
    ) -> IngestionResult:
        """
        Ingest Airflow DAG and task metadata from REST API.

        Args:
            base_url: Airflow instance base URL (e.g., "https://airflow.example.com")
            instance_name: Optional instance name for URN construction
            auth_mode: Authentication mode ("none", "bearer_env", "basic_env")
            dag_id_allowlist: Optional list of DAG IDs to include
            dag_id_denylist: Optional list of DAG IDs to exclude
            dag_id_regex: Optional regex pattern for DAG ID filtering
            include_paused: Whether to include paused DAGs
            include_inactive: Whether to include inactive DAGs
            cleanup_orphans: If True, delete capsules/edges not in current parse
            **kwargs: Additional configuration options (e.g., token_env, page_limit)

        Returns:
            IngestionResult with job details and statistics
        """
        config = {
            "base_url": base_url,
            "instance_name": instance_name,
            "auth_mode": auth_mode,
            "dag_id_allowlist": dag_id_allowlist,
            "dag_id_denylist": dag_id_denylist,
            "dag_id_regex": dag_id_regex,
            "include_paused": include_paused,
            "include_inactive": include_inactive,
            **kwargs,
        }

        # Remove None values
        config = {k: v for k, v in config.items() if v is not None}

        return await self.ingest("airflow", config, cleanup_orphans=cleanup_orphans)

    async def ingest_snowflake(
        self,
        account: str,
        user: str,
        warehouse: str = "COMPUTE_WH",
        role: str = "SYSADMIN",
        password: Optional[str] = None,
        private_key_path: Optional[str] = None,
        databases: Optional[list[str]] = None,
        schemas: Optional[list[str]] = None,
        include_views: bool = True,
        include_materialized_views: bool = True,
        include_external_tables: bool = True,
        enable_lineage: bool = False,
        lineage_lookback_days: int = 7,
        use_account_usage: bool = False,
        enable_tag_extraction: bool = False,
        cleanup_orphans: bool = False,
        **kwargs: Any,
    ) -> IngestionResult:
        """
        Ingest Snowflake metadata from INFORMATION_SCHEMA and ACCOUNT_USAGE.

        Args:
            account: Snowflake account identifier (e.g., "myorg-account123")
            user: Snowflake username
            warehouse: Warehouse for metadata queries
            role: Role for querying metadata
            password: Password for authentication (use password OR private_key_path)
            private_key_path: Path to private key file for key-pair authentication
            databases: List of databases to scan (empty = all accessible)
            schemas: List of schema patterns to include (e.g., ["PROD.*"])
            include_views: Include views in ingestion
            include_materialized_views: Include materialized views
            include_external_tables: Include external tables
            enable_lineage: Extract lineage from ACCESS_HISTORY (requires use_account_usage)
            lineage_lookback_days: Days to look back for lineage (1-365)
            use_account_usage: Use ACCOUNT_USAGE views (required for lineage & tags)
            enable_tag_extraction: Extract Snowflake tags (requires use_account_usage)
            cleanup_orphans: If True, delete capsules/columns from same source not in current parse
            **kwargs: Additional configuration options (e.g., tag_mappings, layer_patterns)

        Returns:
            IngestionResult with job details and statistics

        Example:
            # With password authentication
            await service.ingest_snowflake(
                account="myorg-account123",
                user="dcs_service_user",
                password=os.environ["SNOWFLAKE_PASSWORD"],
                databases=["PROD", "ANALYTICS"],
            )

            # With key-pair authentication
            await service.ingest_snowflake(
                account="myorg-account123",
                user="dcs_service_user",
                private_key_path="/path/to/rsa_key.p8",
                databases=["PROD"],
                enable_lineage=True,
                use_account_usage=True,
            )
        """
        config = {
            "account": account,
            "user": user,
            "warehouse": warehouse,
            "role": role,
            "password": password,
            "private_key_path": private_key_path,
            "databases": databases or [],
            "schemas": schemas or [],
            "include_views": include_views,
            "include_materialized_views": include_materialized_views,
            "include_external_tables": include_external_tables,
            "enable_lineage": enable_lineage,
            "lineage_lookback_days": lineage_lookback_days,
            "use_account_usage": use_account_usage,
            "enable_tag_extraction": enable_tag_extraction,
            **kwargs,
        }

        # Remove None values
        config = {k: v for k, v in config.items() if v is not None}

        return await self.ingest("snowflake", config, cleanup_orphans=cleanup_orphans)

    async def ingest(
        self,
        source_type: str,
        config: dict[str, Any],
        cleanup_orphans: bool = False,
    ) -> IngestionResult:
        """
        Ingest metadata from any supported source.

        Args:
            source_type: Type of source (e.g., "dbt")
            config: Parser-specific configuration
            cleanup_orphans: If True, delete capsules/columns from same source not in current parse

        Returns:
            IngestionResult with job details and statistics
        """
        # Start ingestion job
        job = await self.job_repo.start_job(
            source_type=source_type,
            source_name=config.get("project_name"),
            config=config,
        )

        stats = IngestionStats()
        result = IngestionResult(
            job_id=job.id,
            status=IngestionStatus.RUNNING,
            source_type=source_type,
            started_at=job.started_at,
        )

        try:
            # Get parser
            parser = get_parser(source_type)

            # Validate config
            validation_errors = parser.validate_config(config)
            if validation_errors:
                raise ValueError(f"Invalid configuration: {'; '.join(validation_errors)}")

            # Parse metadata
            logger.info(f"Parsing {source_type} metadata...")
            parse_result = await parser.parse(config)

            # Update source name if discovered
            if parse_result.source_name:
                job.source_name = parse_result.source_name
                result.source_name = parse_result.source_name

            # Check for parse errors
            stats.warnings = parse_result.warning_count
            stats.errors = parse_result.error_count

            if parse_result.has_errors:
                error_msgs = [str(e) for e in parse_result.errors if e.severity.value == "error"]
                raise ValueError(f"Parse errors: {'; '.join(error_msgs[:5])}")

            # Get or create source system
            source_system, _ = await self.source_system_repo.get_or_create(
                name=result.source_name or source_type,
                source_type=source_type,
            )

            # Persist parsed data (returns sets of URNs that were processed)
            processed_urns = await self._persist_parse_result(
                parse_result=parse_result,
                job=job,
                source_system_id=source_system.id,
                stats=stats,
            )

            # Cleanup orphans if requested
            if cleanup_orphans:
                await self._cleanup_orphans(
                    source_system_id=source_system.id,
                    processed_urns=processed_urns,
                    stats=stats,
                )

            # Complete job
            await self.job_repo.complete_job(job, stats.to_dict())

            result.status = IngestionStatus.COMPLETED
            result.stats = stats
            result.completed_at = job.completed_at

            # Build log message
            log_parts = [
                f"Ingestion completed: {stats.capsules_created} capsules created, "
                f"{stats.capsules_updated} updated, {stats.capsules_deleted} deleted, "
                f"{stats.columns_created} columns, {stats.edges_created} edges"
            ]

            # Add orchestration stats if any exist
            if stats.pipelines_created > 0 or stats.pipeline_tasks_created > 0:
                log_parts.append(
                    f"; {stats.pipelines_created} pipelines, "
                    f"{stats.pipeline_tasks_created} tasks, "
                    f"{stats.orchestration_edges_created} orchestration edges"
                )

            logger.info("".join(log_parts))

        except Exception as e:
            logger.exception(f"Ingestion failed: {e}")
            await self.job_repo.fail_job(
                job,
                error_message=str(e),
                error_details={"type": type(e).__name__},
            )
            result.status = IngestionStatus.FAILED
            result.error_message = str(e)
            result.completed_at = job.completed_at

        return result

    async def _persist_parse_result(
        self,
        parse_result: ParseResult,
        job: IngestionJob,
        source_system_id: UUID,
        stats: IngestionStats,
    ) -> ProcessedUrns:
        """Persist parsed metadata to database. Returns URNs that were processed."""
        processed = ProcessedUrns()
        
        # Build URN to capsule mapping for lineage
        urn_to_capsule: dict[str, Capsule] = {}
        # Build URN to column mapping for column lineage
        urn_to_column: dict[str, Column] = {}

        # Create/update domains first
        domain_map: dict[str, UUID] = {}
        for raw_domain in parse_result.domains:
            domain, created = await self.domain_repo.get_or_create(
                name=raw_domain.name,
                description=raw_domain.description,
            )
            domain_map[raw_domain.name] = domain.id
            if created:
                stats.domains_created += 1

        # Create/update capsules
        for raw_capsule in parse_result.capsules:
            # Merge config into meta for storage
            merged_meta = {**raw_capsule.meta}
            if raw_capsule.config:
                merged_meta["config"] = raw_capsule.config

            capsule = Capsule(
                urn=raw_capsule.urn,
                name=raw_capsule.name,
                capsule_type=raw_capsule.capsule_type,
                database_name=raw_capsule.database_name,
                schema_name=raw_capsule.schema_name,
                layer=raw_capsule.layer,
                materialization=raw_capsule.materialization,
                description=raw_capsule.description,
                has_tests=raw_capsule.has_tests,
                test_count=raw_capsule.test_count,
                meta=merged_meta,
                tags=raw_capsule.tags,
                source_system_id=source_system_id,
                ingestion_id=job.id,
            )

            # Set domain if specified
            if raw_capsule.domain_name and raw_capsule.domain_name in domain_map:
                capsule.domain_id = domain_map[raw_capsule.domain_name]

            persisted_capsule, created = await self.capsule_repo.upsert_by_urn(capsule)
            urn_to_capsule[raw_capsule.urn] = persisted_capsule
            processed.capsule_urns.add(raw_capsule.urn)

            if created:
                stats.capsules_created += 1
            else:
                stats.capsules_updated += 1

        # Create/update columns
        for raw_column in parse_result.columns:
            # Get parent capsule
            parent_capsule = urn_to_capsule.get(raw_column.capsule_urn)
            if not parent_capsule:
                # Try to find existing capsule
                parent_capsule = await self.capsule_repo.get_by_urn(raw_column.capsule_urn)
                if not parent_capsule:
                    logger.warning(f"Parent capsule not found for column: {raw_column.urn}")
                    continue

            column = Column(
                urn=raw_column.urn,
                capsule_id=parent_capsule.id,
                name=raw_column.name,
                data_type=raw_column.data_type,
                ordinal_position=raw_column.ordinal_position,
                is_nullable=raw_column.is_nullable,
                semantic_type=raw_column.semantic_type,
                pii_type=raw_column.pii_type,
                pii_detected_by=raw_column.pii_detected_by,
                description=raw_column.description,
                meta=raw_column.meta,
                tags=raw_column.tags,
                stats=raw_column.stats,
                has_tests=raw_column.has_tests,
                test_count=raw_column.test_count,
            )

            persisted_column, created = await self.column_repo.upsert_by_urn(column)
            # Track the column for column lineage lookup
            urn_to_column[raw_column.urn] = persisted_column
            processed.column_urns.add(raw_column.urn)

            if created:
                stats.columns_created += 1
            else:
                stats.columns_updated += 1

            if raw_column.pii_type:
                stats.pii_columns_detected += 1

        # Create lineage edges
        for raw_edge in parse_result.edges:
            source_capsule = urn_to_capsule.get(raw_edge.source_urn)
            target_capsule = urn_to_capsule.get(raw_edge.target_urn)

            if not source_capsule:
                source_capsule = await self.capsule_repo.get_by_urn(raw_edge.source_urn)
            if not target_capsule:
                target_capsule = await self.capsule_repo.get_by_urn(raw_edge.target_urn)

            if not source_capsule or not target_capsule:
                logger.warning(
                    f"Could not create edge: {raw_edge.source_urn} -> {raw_edge.target_urn}"
                )
                continue

            edge = CapsuleLineage(
                source_urn=raw_edge.source_urn,
                target_urn=raw_edge.target_urn,
                source_id=source_capsule.id,
                target_id=target_capsule.id,
                edge_type=raw_edge.edge_type,
                transformation=raw_edge.transformation,
                meta=raw_edge.meta,
                ingestion_id=job.id,
            )

            _, created = await self.lineage_repo.upsert(edge)
            processed.edge_keys.add((raw_edge.source_urn, raw_edge.target_urn))

            if created:
                stats.edges_created += 1
            else:
                stats.edges_updated += 1

        # Create column lineage edges
        for raw_col_edge in parse_result.column_edges:
            source_column = urn_to_column.get(raw_col_edge.source_column_urn)
            target_column = urn_to_column.get(raw_col_edge.target_column_urn)

            if not source_column:
                source_column = await self.column_repo.get_by_urn(raw_col_edge.source_column_urn)
                if source_column:
                    urn_to_column[source_column.urn] = source_column
            if not target_column:
                target_column = await self.column_repo.get_by_urn(raw_col_edge.target_column_urn)
                if target_column:
                    urn_to_column[target_column.urn] = target_column

            if not source_column or not target_column:
                logger.debug(
                    f"Could not create column edge: {raw_col_edge.source_column_urn} -> {raw_col_edge.target_column_urn}"
                )
                continue

            col_edge = ColumnLineage(
                source_urn=raw_col_edge.source_column_urn,
                target_urn=raw_col_edge.target_column_urn,
                source_column_id=source_column.id,
                target_column_id=target_column.id,
                transformation_type=raw_col_edge.transformation_type,
                transformation_expr=raw_col_edge.transformation_expr,
                ingestion_id=job.id,
            )

            _, created = await self.column_lineage_repo.upsert(col_edge)
            processed.column_edge_keys.add(
                (raw_col_edge.source_column_urn, raw_col_edge.target_column_urn)
            )

            if created:
                stats.column_edges_created += 1
            else:
                stats.column_edges_updated += 1

        # Create/update orchestration metadata (Airflow pipelines and tasks)
        urn_to_pipeline: dict[str, Pipeline] = {}

        # Create/update pipelines
        for raw_pipeline in parse_result.pipelines:
            # Get domain_id if domain_name is provided
            domain_id = None
            if raw_pipeline.domain_name:
                domain_id = domain_map.get(raw_pipeline.domain_name)

            pipeline = Pipeline(
                urn=raw_pipeline.urn,
                name=raw_pipeline.name,
                pipeline_type=raw_pipeline.pipeline_type,
                source_system_id=source_system_id,
                source_system_identifier=raw_pipeline.source_system_identifier,
                schedule_interval=raw_pipeline.schedule_interval,
                owners=raw_pipeline.owners,
                description=raw_pipeline.description,
                is_paused=raw_pipeline.is_paused,
                is_active=raw_pipeline.is_active,
                config=raw_pipeline.config,
                meta=raw_pipeline.meta,
                ingestion_id=job.id,
            )

            # Check if pipeline already exists
            result = await self.session.execute(
                select(Pipeline).where(Pipeline.urn == raw_pipeline.urn)
            )
            existing_pipeline = result.scalar_one_or_none()
            if existing_pipeline:
                # Update existing
                for key, value in pipeline.__dict__.items():
                    if key not in ["_sa_instance_state", "id", "created_at"]:
                        setattr(existing_pipeline, key, value)
                existing_pipeline.updated_at = datetime.utcnow()
                existing_pipeline.last_seen = datetime.utcnow()
                pipeline = existing_pipeline
                stats.pipelines_updated += 1
            else:
                # Create new
                self.session.add(pipeline)
                await self.session.flush()  # Flush to get ID
                stats.pipelines_created += 1

            urn_to_pipeline[raw_pipeline.urn] = pipeline
            processed.pipeline_urns.add(raw_pipeline.urn)

        # Create/update pipeline tasks
        urn_to_task: dict[str, PipelineTask] = {}
        for raw_task in parse_result.pipeline_tasks:
            # Get pipeline_id from parent pipeline URN
            parent_pipeline = urn_to_pipeline.get(raw_task.pipeline_urn)
            if not parent_pipeline:
                # Try to find in database
                existing = await self.session.execute(
                    select(Pipeline).where(Pipeline.urn == raw_task.pipeline_urn)
                )
                parent_pipeline = existing.scalar_one_or_none()

            if not parent_pipeline:
                logger.warning(
                    f"Could not create task {raw_task.urn}: parent pipeline {raw_task.pipeline_urn} not found"
                )
                continue

            # Convert retry_delay_seconds to timedelta
            retry_delay = None
            if raw_task.retry_delay_seconds:
                from datetime import timedelta
                retry_delay = timedelta(seconds=raw_task.retry_delay_seconds)

            # Convert timeout_seconds to timedelta
            timeout = None
            if raw_task.timeout_seconds:
                from datetime import timedelta
                timeout = timedelta(seconds=raw_task.timeout_seconds)

            task = PipelineTask(
                urn=raw_task.urn,
                name=raw_task.name,
                task_type=raw_task.task_type,
                pipeline_id=parent_pipeline.id,
                pipeline_urn=raw_task.pipeline_urn,
                operator=raw_task.operator,
                operation_type=raw_task.operation_type,
                retries=raw_task.retries,
                retry_delay=retry_delay,
                timeout=timeout,
                tool_reference=raw_task.tool_reference,
                description=raw_task.description,
                meta=raw_task.meta,
                ingestion_id=job.id,
            )

            # Check if task already exists
            result = await self.session.execute(
                select(PipelineTask).where(PipelineTask.urn == raw_task.urn)
            )
            existing_task = result.scalar_one_or_none()
            if existing_task:
                # Update existing
                for key, value in task.__dict__.items():
                    if key not in ["_sa_instance_state", "id", "created_at"]:
                        setattr(existing_task, key, value)
                existing_task.updated_at = datetime.utcnow()
                task = existing_task
                stats.pipeline_tasks_updated += 1
            else:
                # Create new
                self.session.add(task)
                await self.session.flush()  # Flush to get ID
                stats.pipeline_tasks_created += 1

            urn_to_task[raw_task.urn] = task
            processed.pipeline_task_urns.add(raw_task.urn)

        # Create orchestration edges
        for raw_orch_edge in parse_result.orchestration_edges:
            edge_category = raw_orch_edge.edge_category
            edge_type = raw_orch_edge.edge_type

            # Determine which edge table to use based on category
            if edge_category == "task_dependency":
                # TaskDependencyEdge (task→task)
                if edge_type == "contains":
                    # Pipeline CONTAINS Task - Skip creating edge as this relationship
                    # is already established via pipeline_id foreign key in PipelineTask
                    logger.debug(
                        f"Skipping CONTAINS edge (handled by FK): {raw_orch_edge.source_urn} -> {raw_orch_edge.target_urn}"
                    )
                    continue

                else:
                    # Task DEPENDS_ON Task
                    source_task = urn_to_task.get(raw_orch_edge.source_urn)
                    target_task = urn_to_task.get(raw_orch_edge.target_urn)

                    if not source_task:
                        result = await self.session.execute(
                            select(PipelineTask).where(PipelineTask.urn == raw_orch_edge.source_urn)
                        )
                        source_task = result.scalar_one_or_none()
                    if not target_task:
                        result = await self.session.execute(
                            select(PipelineTask).where(PipelineTask.urn == raw_orch_edge.target_urn)
                        )
                        target_task = result.scalar_one_or_none()

                    if not source_task or not target_task:
                        logger.debug(
                            f"Could not create DEPENDS_ON edge: {raw_orch_edge.source_urn} -> {raw_orch_edge.target_urn}"
                        )
                        continue

                    # Check if edge already exists
                    result = await self.session.execute(
                        select(TaskDependencyEdge).where(
                            and_(
                                TaskDependencyEdge.source_task_urn == raw_orch_edge.source_urn,
                                TaskDependencyEdge.target_task_urn == raw_orch_edge.target_urn,
                            )
                        )
                    )
                    existing_edge = result.scalar_one_or_none()

                    if not existing_edge:
                        edge = TaskDependencyEdge(
                            source_task_urn=raw_orch_edge.source_urn,
                            target_task_urn=raw_orch_edge.target_urn,
                            source_task_id=source_task.id,
                            target_task_id=target_task.id,
                            edge_type=edge_type,
                            meta=raw_orch_edge.meta,
                            ingestion_id=job.id,
                        )
                        self.session.add(edge)
                        stats.orchestration_edges_created += 1
                    else:
                        # Update existing
                        existing_edge.meta = raw_orch_edge.meta
                        existing_edge.ingestion_id = job.id
                        stats.orchestration_edges_updated += 1

                processed.orchestration_edge_keys.add((raw_orch_edge.source_urn, raw_orch_edge.target_urn))

            elif edge_category == "task_data":
                # TaskDataEdge (task↔capsule) - handles PRODUCES, CONSUMES, TRANSFORMS, VALIDATES
                # For PRODUCES/TRANSFORMS/VALIDATES: source=task, target=capsule
                # For CONSUMES: source=capsule, target=task

                # Determine task and capsule URNs based on edge type
                if edge_type == "consumes":
                    # CONSUMES: capsule → task
                    task_urn = raw_orch_edge.target_urn
                    capsule_urn = raw_orch_edge.source_urn
                else:
                    # PRODUCES/TRANSFORMS/VALIDATES: task → capsule
                    task_urn = raw_orch_edge.source_urn
                    capsule_urn = raw_orch_edge.target_urn

                # Look up task
                task = urn_to_task.get(task_urn)
                if not task:
                    result = await self.session.execute(
                        select(PipelineTask).where(PipelineTask.urn == task_urn)
                    )
                    task = result.scalar_one_or_none()

                # Look up capsule
                capsule = urn_to_capsule.get(capsule_urn)
                if not capsule:
                    capsule = await self.capsule_repo.get_by_urn(capsule_urn)

                if not task or not capsule:
                    logger.debug(
                        f"Could not create task_data edge ({edge_type}): task={task_urn}, capsule={capsule_urn}"
                    )
                    continue

                # Check if edge already exists
                result = await self.session.execute(
                    select(TaskDataEdge).where(
                        and_(
                            TaskDataEdge.task_urn == task_urn,
                            TaskDataEdge.capsule_urn == capsule_urn,
                            TaskDataEdge.edge_type == edge_type,
                        )
                    )
                )
                existing_edge = result.scalar_one_or_none()

                if not existing_edge:
                    edge = TaskDataEdge(
                        task_urn=task_urn,
                        capsule_urn=capsule_urn,
                        task_id=task.id,
                        capsule_id=capsule.id,
                        edge_type=edge_type,  # produces, consumes, transforms, validates
                        operation=raw_orch_edge.operation,
                        access_pattern=raw_orch_edge.access_pattern,
                        transformation_type=raw_orch_edge.transformation_type,
                        validation_type=raw_orch_edge.validation_type,
                        meta=raw_orch_edge.meta,
                        ingestion_id=job.id,
                    )
                    self.session.add(edge)
                    stats.orchestration_edges_created += 1
                    logger.debug(f"Created TaskDataEdge: {edge_type} task={task_urn} capsule={capsule_urn}")
                else:
                    # Update existing
                    existing_edge.operation = raw_orch_edge.operation
                    existing_edge.access_pattern = raw_orch_edge.access_pattern
                    existing_edge.transformation_type = raw_orch_edge.transformation_type
                    existing_edge.validation_type = raw_orch_edge.validation_type
                    existing_edge.meta = raw_orch_edge.meta
                    existing_edge.ingestion_id = job.id
                    stats.orchestration_edges_updated += 1

                processed.orchestration_edge_keys.add((raw_orch_edge.source_urn, raw_orch_edge.target_urn))

            elif edge_category == "pipeline_trigger":
                # PipelineTriggerEdge (pipeline→pipeline)
                source_pipeline = urn_to_pipeline.get(raw_orch_edge.source_urn)
                target_pipeline = urn_to_pipeline.get(raw_orch_edge.target_urn)

                if not source_pipeline:
                    result = await self.session.execute(
                        select(Pipeline).where(Pipeline.urn == raw_orch_edge.source_urn)
                    )
                    source_pipeline = result.scalar_one_or_none()
                if not target_pipeline:
                    result = await self.session.execute(
                        select(Pipeline).where(Pipeline.urn == raw_orch_edge.target_urn)
                    )
                    target_pipeline = result.scalar_one_or_none()

                if not source_pipeline or not target_pipeline:
                    logger.debug(
                        f"Could not create pipeline_trigger edge: {raw_orch_edge.source_urn} -> {raw_orch_edge.target_urn}"
                    )
                    continue

                # Check if edge already exists
                result = await self.session.execute(
                    select(PipelineTriggerEdge).where(
                        and_(
                            PipelineTriggerEdge.source_pipeline_urn == raw_orch_edge.source_urn,
                            PipelineTriggerEdge.target_pipeline_urn == raw_orch_edge.target_urn,
                        )
                    )
                )
                existing_edge = result.scalar_one_or_none()

                if not existing_edge:
                    edge = PipelineTriggerEdge(
                        source_pipeline_urn=raw_orch_edge.source_urn,
                        target_pipeline_urn=raw_orch_edge.target_urn,
                        source_pipeline_id=source_pipeline.id,
                        target_pipeline_id=target_pipeline.id,
                        edge_type=edge_type,  # triggers
                        meta=raw_orch_edge.meta,
                        ingestion_id=job.id,
                    )
                    self.session.add(edge)
                    stats.orchestration_edges_created += 1
                else:
                    # Update existing
                    existing_edge.meta = raw_orch_edge.meta
                    existing_edge.ingestion_id = job.id
                    stats.orchestration_edges_updated += 1

                processed.orchestration_edge_keys.add((raw_orch_edge.source_urn, raw_orch_edge.target_urn))

        # Phase 6: Store column-level lineage mappings
        for raw_mapping in parse_result.column_mappings:
            await self._store_column_mapping(
                raw_mapping=raw_mapping,
                job=job,
                urn_to_capsule=urn_to_capsule,
                stats=stats,
            )

        # Flush all changes
        await self.session.flush()

        return processed

    async def _store_column_mapping(
        self,
        raw_mapping: "RawColumnMapping",  # type: ignore
        job: IngestionJob,
        urn_to_capsule: dict[str, Capsule],
        stats: IngestionStats,
    ) -> None:
        """Store a column-level lineage mapping (Phase 6.5).

        Args:
            raw_mapping: Raw column mapping from parser
            job: Current ingestion job
            urn_to_capsule: Map of capsule URNs to Capsule objects
            stats: Ingestion statistics to update
        """
        from sqlalchemy import and_, select

        from src.models.column import Column
        from src.models.lineage import ColumnLineage

        try:
            # Resolve target column first
            target_column_id = await self._resolve_column_id(
                qualified_name=raw_mapping.target_column,
                urn_to_capsule=urn_to_capsule,
            )

            if not target_column_id:
                logger.debug(
                    f"Could not resolve target column '{raw_mapping.target_column}' - skipping lineage storage"
                )
                return

            # Process each source column
            for source_col_name in raw_mapping.source_columns:
                source_column_id = await self._resolve_column_id(
                    qualified_name=source_col_name,
                    urn_to_capsule=urn_to_capsule,
                )

                if not source_column_id:
                    logger.debug(
                        f"Could not resolve source column '{source_col_name}' - skipping this mapping"
                    )
                    continue

                # Generate URNs for the columns
                source_urn = f"urn:dcs:column:{source_col_name}"
                target_urn = f"urn:dcs:column:{raw_mapping.target_column}"

                # Check if this mapping already exists
                result = await self.session.execute(
                    select(ColumnLineage).where(
                        and_(
                            ColumnLineage.source_column_id == source_column_id,
                            ColumnLineage.target_column_id == target_column_id,
                        )
                    )
                )
                existing = result.scalar_one_or_none()

                if not existing:
                    # Create new column lineage edge
                    edge = ColumnLineage(
                        source_column_id=source_column_id,
                        source_column_urn=source_urn,
                        target_column_id=target_column_id,
                        target_column_urn=target_urn,
                        edge_type="derives_from",
                        transformation_type=raw_mapping.transformation_type,
                        transformation_logic=raw_mapping.transformation_logic,
                        confidence=raw_mapping.confidence,
                        detected_by=raw_mapping.detected_by,
                        detection_metadata=raw_mapping.meta,
                        ingestion_id=job.id,
                    )
                    self.session.add(edge)
                    logger.info(
                        f"✅ Created column lineage: {source_col_name} -> {raw_mapping.target_column} "
                        f"(type: {raw_mapping.transformation_type}, confidence: {raw_mapping.confidence})"
                    )
                else:
                    # Update existing with latest confidence and metadata
                    existing.transformation_type = raw_mapping.transformation_type
                    existing.transformation_logic = raw_mapping.transformation_logic
                    existing.confidence = raw_mapping.confidence
                    existing.detected_by = raw_mapping.detected_by
                    existing.detection_metadata = raw_mapping.meta
                    existing.ingestion_id = job.id
                    logger.debug(
                        f"Updated column lineage: {source_col_name} -> {raw_mapping.target_column}"
                    )

        except Exception as e:
            logger.warning(f"Failed to store column mapping: {e}")
            # Don't fail the entire ingestion for column mapping errors

    async def _resolve_column_id(
        self,
        qualified_name: str,
        urn_to_capsule: dict[str, Capsule],
    ) -> Optional[UUID]:
        """Resolve a qualified column name to a column ID (Phase 6.5).

        Args:
            qualified_name: Qualified column name (e.g., "orders.customer_id", "public.orders.customer_id")
            urn_to_capsule: Map of capsule URNs to Capsule objects

        Returns:
            Column UUID if resolved, None otherwise
        """
        from sqlalchemy import select

        from src.models.column import Column

        try:
            # Parse qualified name
            # Formats: "table.column", "schema.table.column"
            parts = qualified_name.split(".")

            if len(parts) == 2:
                # Format: "table.column"
                table_name, column_name = parts
                schema_name = None
            elif len(parts) == 3:
                # Format: "schema.table.column"
                schema_name, table_name, column_name = parts
            else:
                # Unknown format
                logger.debug(f"Could not parse qualified name: {qualified_name}")
                return None

            # Find matching capsule by name
            matching_capsule = None
            for capsule in urn_to_capsule.values():
                # Match by capsule name (case-insensitive)
                if capsule.name.lower() == table_name.lower():
                    # If schema is specified, also check schema match
                    if schema_name:
                        if capsule.schema_name and capsule.schema_name.lower() == schema_name.lower():
                            matching_capsule = capsule
                            break
                    else:
                        matching_capsule = capsule
                        break

            if not matching_capsule:
                logger.debug(f"Could not find capsule for table: {table_name}")
                return None

            # Find column by capsule_id and column name
            result = await self.session.execute(
                select(Column).where(
                    and_(
                        Column.capsule_id == matching_capsule.id,
                        Column.name == column_name,
                    )
                )
            )
            column = result.scalar_one_or_none()

            if column:
                return column.id
            else:
                logger.debug(
                    f"Could not find column '{column_name}' in capsule '{matching_capsule.name}'"
                )
                return None

        except Exception as e:
            logger.debug(f"Error resolving column '{qualified_name}': {e}")
            return None

    async def _cleanup_orphans(
        self,
        source_system_id: UUID,
        processed_urns: ProcessedUrns,
        stats: IngestionStats,
    ) -> None:
        """
        Remove capsules, columns, and edges that were not in the current parse.
        Only removes entities from the same source system.
        """
        from sqlalchemy import and_, delete, select
        
        # Get existing capsules from this source system
        existing_capsules = await self.capsule_repo.get_by_source_system(source_system_id)
        
        # Find orphaned capsules (in DB but not in current parse)
        orphan_capsule_ids: list[UUID] = []
        for capsule in existing_capsules:
            if capsule.urn not in processed_urns.capsule_urns:
                orphan_capsule_ids.append(capsule.id)
        
        # Delete orphaned capsules (this will cascade to columns and edges)
        if orphan_capsule_ids:
            for capsule_id in orphan_capsule_ids:
                # Delete associated lineage edges first
                deleted_edges = await self.lineage_repo.delete_edges_for_capsule(capsule_id)
                stats.edges_deleted += deleted_edges
                
                # Delete associated columns
                columns = await self.column_repo.get_by_capsule_id(capsule_id)
                for col in columns:
                    await self.session.delete(col)
                    stats.columns_deleted += 1
                
                # Delete capsule
                capsule = await self.capsule_repo.get_by_id(capsule_id)
                if capsule:
                    await self.session.delete(capsule)
                    stats.capsules_deleted += 1
            
            logger.info(f"Cleaned up {stats.capsules_deleted} orphaned capsules")
        
        # For edges not attached to orphaned capsules, check individual edge orphans
        # Get all edges from this source system
        all_edges_stmt = select(CapsuleLineage).join(
            Capsule, CapsuleLineage.source_id == Capsule.id
        ).where(Capsule.source_system_id == source_system_id)
        result = await self.session.execute(all_edges_stmt)
        all_edges = result.scalars().all()
        
        orphan_edges = []
        for edge in all_edges:
            edge_key = (edge.source_urn, edge.target_urn)
            if edge_key not in processed_urns.edge_keys:
                orphan_edges.append(edge)
        
        for edge in orphan_edges:
            await self.session.delete(edge)
            stats.edges_deleted += 1
        
        await self.session.flush()

    async def get_job_status(self, job_id: UUID) -> Optional[IngestionJob]:
        """Get ingestion job by ID."""
        return await self.job_repo.get_by_id(job_id)

    async def get_recent_jobs(
        self,
        limit: int = 50,
        source_type: Optional[str] = None,
    ) -> list[IngestionJob]:
        """Get recent ingestion jobs."""
        jobs = await self.job_repo.get_recent(limit=limit, source_type=source_type)
        return list(jobs)

    async def cancel_job(self, job_id: UUID) -> Optional[IngestionJob]:
        """Cancel a running ingestion job."""
        job = await self.job_repo.get_by_id(job_id)
        if job and job.is_running:
            return await self.job_repo.cancel_job(job)
        return job
