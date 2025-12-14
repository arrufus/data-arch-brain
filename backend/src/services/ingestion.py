"""Ingestion service for orchestrating metadata parsing and persistence."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.capsule import Capsule
from src.models.column import Column
from src.models.ingestion import IngestionJob, IngestionStatus
from src.models.lineage import CapsuleLineage, ColumnLineage
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
            self.column_edges_created + self.column_edges_updated + self.column_edges_deleted
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

            logger.info(
                f"Ingestion completed: {stats.capsules_created} capsules created, "
                f"{stats.capsules_updated} updated, {stats.capsules_deleted} deleted, "
                f"{stats.columns_created} columns, {stats.edges_created} edges"
            )

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

        # Flush all changes
        await self.session.flush()
        
        return processed

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
