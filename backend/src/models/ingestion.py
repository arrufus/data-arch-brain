"""Ingestion job model for tracking metadata ingestion runs."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType

if TYPE_CHECKING:
    from src.models.capsule import Capsule
    from src.models.lineage import CapsuleLineage, ColumnLineage
    from src.models.violation import Violation


class IngestionStatus(str, Enum):
    """Status of an ingestion job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IngestionJob(DCSBase):
    """Audit log of metadata ingestion runs."""

    __tablename__ = "ingestion_jobs"

    # Source info
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="running"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Statistics and configuration
    stats: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)
    config: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[dict]] = mapped_column(JSONType(), nullable=True)

    # Relationships
    capsules: Mapped[list["Capsule"]] = relationship(back_populates="ingestion_job")
    capsule_lineage_edges: Mapped[list["CapsuleLineage"]] = relationship(
        back_populates="ingestion_job"
    )
    column_lineage_edges: Mapped[list["ColumnLineage"]] = relationship(
        back_populates="ingestion_job"
    )
    violations: Mapped[list["Violation"]] = relationship(back_populates="ingestion_job")

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get job duration in seconds."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_running(self) -> bool:
        """Check if job is still running."""
        return self.status == IngestionStatus.RUNNING.value

    @property
    def is_complete(self) -> bool:
        """Check if job completed successfully."""
        return self.status == IngestionStatus.COMPLETED.value

    @property
    def is_failed(self) -> bool:
        """Check if job failed."""
        return self.status == IngestionStatus.FAILED.value
