"""Impact History models for Phase 8 Advanced Impact Analysis."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.base import JSONType, UUIDType, get_schema_table_args


class ImpactHistory(Base):
    """Historical record of schema changes and their actual impact (Phase 8).

    Tracks predicted vs actual impact to improve future predictions
    and provide lessons learned.
    """

    __tablename__ = "impact_history"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(
        UUIDType(),
        primary_key=True,
        default=uuid4,
    )

    # Change identification
    change_id: Mapped[UUID] = mapped_column(
        UUIDType(),
        nullable=False,
        unique=True,
        comment="Unique identifier for the schema change",
    )
    column_urn: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
        comment="URN of the changed column",
    )
    change_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="delete, rename, type_change, nullability, etc.",
    )
    change_params: Mapped[Optional[dict]] = mapped_column(
        JSONType(),
        nullable=True,
        comment="Parameters of the change",
    )

    # Predicted impact (from simulation)
    predicted_risk_level: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True,
        comment="low, medium, high, critical",
    )
    predicted_affected_columns: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Predicted number of affected columns",
    )
    predicted_affected_tasks: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Predicted number of affected tasks",
    )
    predicted_downtime_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Predicted downtime in seconds",
    )

    # Actual impact (observed)
    actual_risk_level: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True,
        comment="low, medium, high, critical",
    )
    actual_affected_columns: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Actual number of affected columns",
    )
    actual_affected_tasks: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Actual number of affected tasks",
    )
    actual_downtime_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Actual downtime in seconds",
    )
    actual_failures: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of task failures caused",
    )

    # Outcome
    success: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        index=True,
        comment="Was the change successful",
    )
    rollback_performed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Was a rollback performed",
    )
    issues_encountered: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="List of issues encountered",
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Notes on how issues were resolved",
    )

    # Metadata
    changed_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User who made the change",
    )
    change_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When the change was applied",
    )
    completed_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the change was completed",
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<ImpactHistory(change_id={self.change_id}, "
            f"column_urn={self.column_urn!r}, "
            f"change_type={self.change_type!r}, "
            f"success={self.success})>"
        )
