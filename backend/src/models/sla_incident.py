"""SLA incident models for tracking contract violations."""

from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Interval, Numeric, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType, fk_ref, get_schema_table_args


class IncidentType(str, Enum):
    """Types of SLA incidents."""

    FRESHNESS = "freshness"
    COMPLETENESS = "completeness"
    AVAILABILITY = "availability"
    QUALITY = "quality"
    LATENCY = "latency"
    SCHEMA_CHANGE = "schema_change"


class IncidentStatus(str, Enum):
    """Status of an SLA incident."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    FALSE_POSITIVE = "false_positive"


class IncidentSeverity(str, Enum):
    """Severity levels for SLA incidents."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SLAIncident(DCSBase):
    """SLA incident for tracking contract violations.

    Tracks when SLAs are breached, including timeline, impact,
    resolution, and root cause analysis.
    """

    __tablename__ = "sla_incidents"
    __table_args__ = (
        CheckConstraint(
            "incident_type IN ('freshness', 'completeness', 'availability', 'quality', 'latency', 'schema_change')",
            name="incident_type_valid",
        ),
        CheckConstraint(
            "incident_status IN ('open', 'investigating', 'mitigated', 'resolved', 'closed', 'false_positive')",
            name="incident_status_valid",
        ),
        get_schema_table_args(),
    )

    # Contract reference
    contract_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("capsule_contracts.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    capsule_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("capsules.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Incident details
    incident_type: Mapped[IncidentType] = mapped_column(String(50), nullable=False)
    incident_severity: Mapped[IncidentSeverity] = mapped_column(
        String(20), nullable=False, default=IncidentSeverity.MEDIUM, server_default="medium"
    )

    # What was violated
    sla_target: Mapped[Optional[Decimal]] = mapped_column(Numeric(), nullable=True)
    actual_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(), nullable=True)
    breach_magnitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(), nullable=True)

    # Timeline
    detected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True, server_default="NOW()"
    )
    breach_started_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    breach_ended_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    breach_duration: Mapped[Optional[timedelta]] = mapped_column(Interval(), nullable=True)

    # Impact
    affected_consumers: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )
    downstream_impact: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)

    # Resolution
    incident_status: Mapped[IncidentStatus] = mapped_column(
        String(50), nullable=False, default=IncidentStatus.OPEN, server_default="open", index=True
    )
    resolution: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Root cause
    root_cause: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    root_cause_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Metadata
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONType(), nullable=False, default=dict, server_default="{}"
    )

    # Relationships
    contract: Mapped["CapsuleContract"] = relationship(
        "CapsuleContract", back_populates="sla_incidents", foreign_keys=[contract_id]
    )
    capsule: Mapped["Capsule"] = relationship(
        "Capsule", back_populates="sla_incidents", foreign_keys=[capsule_id]
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<SLAIncident(id={self.id}, type={self.incident_type}, "
            f"severity={self.incident_severity}, status={self.incident_status})>"
        )

    @property
    def is_open(self) -> bool:
        """Check if incident is still open."""
        return self.incident_status in [IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]

    @property
    def is_resolved(self) -> bool:
        """Check if incident is resolved."""
        return self.incident_status in [
            IncidentStatus.RESOLVED,
            IncidentStatus.CLOSED,
            IncidentStatus.FALSE_POSITIVE,
        ]

    @property
    def time_to_detect(self) -> Optional[timedelta]:
        """Calculate time from breach start to detection."""
        if self.breach_started_at and self.detected_at:
            return self.detected_at - self.breach_started_at
        return None

    @property
    def time_to_resolve(self) -> Optional[timedelta]:
        """Calculate time from detection to resolution."""
        if self.resolved_at:
            return self.resolved_at - self.detected_at
        return None

    @property
    def has_impact_assessment(self) -> bool:
        """Check if incident has impact assessment."""
        return bool(
            (self.affected_consumers and len(self.affected_consumers) > 0)
            or self.downstream_impact
        )
