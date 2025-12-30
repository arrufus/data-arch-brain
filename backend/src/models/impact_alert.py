"""Impact Alert models for Phase 8 Advanced Impact Analysis."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.base import JSONType, UUIDType, get_schema_table_args


class ImpactAlert(Base):
    """Alert for high-risk schema changes (Phase 8).

    Proactive notifications for changes that may cause
    breaking impacts or require special attention.
    """

    __tablename__ = "impact_alerts"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(
        UUIDType(),
        primary_key=True,
        default=uuid4,
    )

    # Alert classification
    alert_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="high_risk_change, production_impact, pii_change, breaking_change, low_confidence",
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="critical, high, medium, low",
    )

    # Related change
    column_urn: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
        comment="URN of the affected column",
    )
    change_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of change triggering the alert",
    )

    # Alert details
    trigger_condition: Mapped[Optional[dict]] = mapped_column(
        JSONType(),
        nullable=True,
        comment="Conditions that triggered the alert",
    )
    alert_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable alert message",
    )
    recommendation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Recommended action to take",
    )

    # Recipients
    notified_users: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="List of users notified",
    )
    notified_teams: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="List of teams notified",
    )
    notified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When notifications were sent",
    )

    # Status
    acknowledged: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Has alert been acknowledged",
    )
    acknowledged_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User who acknowledged the alert",
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When alert was acknowledged",
    )
    resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        index=True,
        comment="Has alert been resolved",
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When alert was resolved",
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<ImpactAlert(alert_type={self.alert_type!r}, "
            f"severity={self.severity!r}, "
            f"column_urn={self.column_urn!r}, "
            f"resolved={self.resolved})>"
        )
