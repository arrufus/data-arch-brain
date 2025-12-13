"""Repository for IngestionJob data access."""

from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ingestion import IngestionJob, IngestionStatus
from src.repositories.base import BaseRepository


class IngestionJobRepository(BaseRepository[IngestionJob]):
    """Repository for ingestion job operations."""

    model_class = IngestionJob

    async def get_latest_by_source(
        self,
        source_type: str,
        source_name: Optional[str] = None,
    ) -> Optional[IngestionJob]:
        """Get most recent ingestion job for a source."""
        stmt = select(IngestionJob).where(
            IngestionJob.source_type == source_type
        )
        if source_name:
            stmt = stmt.where(IngestionJob.source_name == source_name)

        stmt = stmt.order_by(IngestionJob.started_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_status(
        self,
        status: IngestionStatus,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[IngestionJob]:
        """Get ingestion jobs by status."""
        stmt = (
            select(IngestionJob)
            .where(IngestionJob.status == status.value)
            .order_by(IngestionJob.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_running(self) -> Sequence[IngestionJob]:
        """Get all running ingestion jobs."""
        return await self.get_by_status(IngestionStatus.RUNNING)

    async def get_recent(
        self,
        limit: int = 50,
        source_type: Optional[str] = None,
    ) -> Sequence[IngestionJob]:
        """Get recent ingestion jobs."""
        stmt = select(IngestionJob).order_by(IngestionJob.started_at.desc())

        if source_type:
            stmt = stmt.where(IngestionJob.source_type == source_type)

        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def start_job(
        self,
        source_type: str,
        source_name: Optional[str] = None,
        config: Optional[dict] = None,
    ) -> IngestionJob:
        """Create a new running ingestion job."""
        job = IngestionJob(
            source_type=source_type,
            source_name=source_name,
            status=IngestionStatus.RUNNING.value,
            config=config or {},
        )
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def complete_job(
        self,
        job: IngestionJob,
        stats: Optional[dict] = None,
    ) -> IngestionJob:
        """Mark job as completed."""
        job.status = IngestionStatus.COMPLETED.value
        job.completed_at = datetime.now(timezone.utc)
        if stats:
            job.stats = stats
        await self.session.flush()
        return job

    async def fail_job(
        self,
        job: IngestionJob,
        error_message: str,
        error_details: Optional[dict] = None,
    ) -> IngestionJob:
        """Mark job as failed."""
        job.status = IngestionStatus.FAILED.value
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = error_message
        job.error_details = error_details
        await self.session.flush()
        return job

    async def cancel_job(self, job: IngestionJob) -> IngestionJob:
        """Mark job as cancelled."""
        job.status = IngestionStatus.CANCELLED.value
        job.completed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return job

    async def update_stats(
        self,
        job: IngestionJob,
        stats: dict,
    ) -> IngestionJob:
        """Update job statistics."""
        job.stats = stats
        await self.session.flush()
        return job
