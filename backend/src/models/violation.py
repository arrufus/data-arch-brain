"""Violation model for conformance rule violations."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DAB_SCHEMA, DABBase, JSONType

if TYPE_CHECKING:
    from src.models.capsule import Capsule
    from src.models.column import Column
    from src.models.ingestion import IngestionJob
    from src.models.rule import Rule


class ViolationStatus(str, Enum):
    """Status of a violation."""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class Violation(DABBase):
    """Conformance rule violation."""

    __tablename__ = "violations"

    # What rule was violated
    rule_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{DAB_SCHEMA}.rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # What violated it (one of these)
    capsule_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(f"{DAB_SCHEMA}.capsules.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    column_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(f"{DAB_SCHEMA}.columns.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Violation details
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), server_default="open", nullable=False, index=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Detection tracking
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    ingestion_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(f"{DAB_SCHEMA}.ingestion_jobs.id"), nullable=True
    )

    # Relationships
    rule: Mapped["Rule"] = relationship(back_populates="violations")
    capsule: Mapped[Optional["Capsule"]] = relationship(back_populates="violations")
    column: Mapped[Optional["Column"]] = relationship(back_populates="violations")
    ingestion_job: Mapped[Optional["IngestionJob"]] = relationship(
        back_populates="violations"
    )
