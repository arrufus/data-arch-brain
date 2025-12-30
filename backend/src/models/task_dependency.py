"""Task Dependency models for Phase 8 Advanced Impact Analysis."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import JSONType, UUIDType, fk_ref, get_schema_table_args

if TYPE_CHECKING:
    from src.models.capsule import Capsule


class TaskDependency(Base):
    """Task dependency on capsules (Phase 8).

    Tracks which Airflow tasks depend on which data capsules,
    enabling task-level impact analysis for schema changes.
    """

    __tablename__ = "task_dependencies"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(
        UUIDType(),
        primary_key=True,
        default=uuid4,
    )

    # DAG and Task identification
    dag_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Capsule reference
    capsule_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("capsules.id"), ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Dependency metadata
    dependency_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="read, write, transform",
    )
    schedule_interval: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Cron expression or preset",
    )

    # Task status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        index=True,
        comment="Is task currently active",
    )

    # Execution metrics
    last_execution_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful execution timestamp",
    )
    avg_execution_duration_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Average execution duration in seconds",
    )
    success_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Success rate percentage (0.00-100.00)",
    )

    # Impact scoring
    criticality_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        comment="Criticality score (0.00-1.00)",
    )

    # Additional metadata
    task_metadata: Mapped[dict] = mapped_column(
        JSONType(),
        default=dict,
        nullable=False,
        server_default="{}",
        comment="Additional task metadata",
        name="metadata",  # Map to "metadata" column in database
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    capsule: Mapped[Optional["Capsule"]] = relationship(
        "Capsule",
        back_populates="task_dependencies",
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<TaskDependency(dag_id={self.dag_id!r}, "
            f"task_id={self.task_id!r}, "
            f"capsule_id={self.capsule_id}, "
            f"dependency_type={self.dependency_type!r})>"
        )
