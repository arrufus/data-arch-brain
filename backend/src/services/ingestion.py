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
from src.models.lineage import CapsuleLineage
from src.parsers import DbtParser, ParseResult, get_parser
from src.repositories import (
    CapsuleLineageRepository,
    CapsuleRepository,
    ColumnRepository,
    DomainRepository,
    IngestionJobRepository,
    SourceSystemRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    """Statistics from an ingestion run."""

    capsules_created: int = 0
    capsules_updated: int = 0
    capsules_unchanged: int = 0
    columns_created: int = 0
    columns_updated: int = 0
    edges_created: int = 0
    edges_updated: int = 0
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
            "columns_created": self.columns_created,
            "columns_updated": self.columns_updated,
            "edges_created": self.edges_created,
            "edges_updated": self.edges_updated,
            "domains_created": self.domains_created,
            "pii_columns_detected": self.pii_columns_detected,
            "warnings": self.warnings,
            "errors": self.errors,
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
        self.domain_repo = DomainRepository(session)
        self.source_system_repo = SourceSystemRepository(session)

    async def ingest_dbt(
        self,
        manifest_path: str,
        catalog_path: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> IngestionResult:
        """
        Ingest dbt metadata from manifest and catalog files.

        Args:
            manifest_path: Path to manifest.json
            catalog_path: Optional path to catalog.json
            project_name: Optional project name override

        Returns:
            IngestionResult with job details and statistics
        """
        config = {
            "manifest_path": manifest_path,
            "catalog_path": catalog_path,
            "project_name": project_name,
        }

        return await self.ingest("dbt", config)

    async def ingest(
        self,
        source_type: str,
        config: dict[str, Any],
    ) -> IngestionResult:
        """
        Ingest metadata from any supported source.

        Args:
            source_type: Type of source (e.g., "dbt")
            config: Parser-specific configuration

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

            # Persist parsed data
            await self._persist_parse_result(
                parse_result=parse_result,
                job=job,
                source_system_id=source_system.id,
                stats=stats,
            )

            # Complete job
            await self.job_repo.complete_job(job, stats.to_dict())

            result.status = IngestionStatus.COMPLETED
            result.stats = stats
            result.completed_at = job.completed_at

            logger.info(
                f"Ingestion completed: {stats.capsules_created} capsules created, "
                f"{stats.capsules_updated} updated, {stats.columns_created} columns, "
                f"{stats.edges_created} edges"
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
    ) -> None:
        """Persist parsed metadata to database."""
        # Build URN to capsule mapping for lineage
        urn_to_capsule: dict[str, Capsule] = {}

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

            _, created = await self.column_repo.upsert_by_urn(column)

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

            if created:
                stats.edges_created += 1
            else:
                stats.edges_updated += 1

        # Flush all changes
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
