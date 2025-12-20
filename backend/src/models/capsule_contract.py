"""Capsule contract models for operational SLAs and agreements."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, ForeignKey, Interval, Numeric, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType, fk_ref, get_schema_table_args


class ContractStatus(str, Enum):
    """Status of a capsule contract."""

    DRAFT = "draft"
    PROPOSED = "proposed"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    BREACHED = "breached"


class SchemaChangePolicy(str, Enum):
    """Policy for handling schema changes."""

    STRICT = "strict"
    BACKWARDS_COMPATIBLE = "backwards_compatible"
    FLEXIBLE = "flexible"
    UNRESTRICTED = "unrestricted"


class SupportLevel(str, Enum):
    """Level of support provided for a capsule."""

    NONE = "none"
    BEST_EFFORT = "best_effort"
    BUSINESS_HOURS = "business_hours"
    TWENTY_FOUR_SEVEN = "24x7"
    CRITICAL = "critical"


class CapsuleContract(DCSBase):
    """Service-level agreement for a capsule.

    Defines operational contracts including freshness, completeness,
    availability, quality, support, and deprecation policies.
    """

    __tablename__ = "capsule_contracts"
    __table_args__ = (
        CheckConstraint(
            "contract_status IN ('draft', 'proposed', 'active', 'deprecated', 'breached')",
            name="contract_status_valid",
        ),
        CheckConstraint(
            "schema_change_policy IN ('strict', 'backwards_compatible', 'flexible', 'unrestricted')",
            name="schema_change_policy_valid",
        ),
        CheckConstraint(
            "support_level IN ('none', 'best_effort', 'business_hours', '24x7', 'critical')",
            name="support_level_valid",
        ),
        get_schema_table_args(),
    )

    # Capsule reference
    capsule_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("capsules.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Contract metadata
    contract_version: Mapped[str] = mapped_column(String(50), nullable=False)
    contract_status: Mapped[ContractStatus] = mapped_column(
        String(50), nullable=False, default=ContractStatus.ACTIVE, server_default="active", index=True
    )

    # Freshness SLA
    freshness_sla: Mapped[Optional[timedelta]] = mapped_column(Interval(), nullable=True)
    freshness_schedule: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_updated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Completeness SLA
    completeness_sla: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # Percentage
    expected_row_count_min: Mapped[Optional[int]] = mapped_column(nullable=True)
    expected_row_count_max: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Availability SLA
    availability_sla: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # Percentage
    max_downtime: Mapped[Optional[timedelta]] = mapped_column(Interval(), nullable=True)

    # Quality SLA
    quality_score_sla: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # Min score
    critical_quality_rules: Mapped[list[str]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )

    # Latency SLA
    query_latency_p95: Mapped[Optional[int]] = mapped_column(nullable=True)
    query_latency_p99: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Schema stability
    schema_change_policy: Mapped[Optional[SchemaChangePolicy]] = mapped_column(
        String(50), nullable=True
    )
    breaking_change_notice_days: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Support
    support_level: Mapped[Optional[SupportLevel]] = mapped_column(String(50), nullable=True)
    support_contact: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    support_slack_channel: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    support_oncall: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Maintenance windows
    maintenance_windows: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )

    # Deprecation
    deprecation_policy: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    deprecation_date: Mapped[Optional[date]] = mapped_column(Date(), nullable=True, index=True)
    replacement_capsule_urn: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Consumers
    known_consumers: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )
    consumer_notification_required: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default="true"
    )

    # Performance targets
    target_row_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    target_size_bytes: Mapped[Optional[int]] = mapped_column(nullable=True)
    target_column_count: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Cost allocation
    cost_center: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    billing_tags: Mapped[dict[str, Any]] = mapped_column(
        JSONType(), nullable=False, default=dict, server_default="{}"
    )

    # Metadata
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONType(), nullable=False, default=dict, server_default="{}"
    )

    # Governance
    contract_owner_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("owners.id")),
        nullable=True,
    )
    approved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Relationships
    capsule: Mapped["Capsule"] = relationship(
        "Capsule", back_populates="contracts", foreign_keys=[capsule_id]
    )
    contract_owner: Mapped[Optional["Owner"]] = relationship(
        "Owner", back_populates="capsule_contracts", foreign_keys=[contract_owner_id]
    )
    sla_incidents: Mapped[list["SLAIncident"]] = relationship(
        "SLAIncident", back_populates="contract", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<CapsuleContract(id={self.id}, capsule_id={self.capsule_id}, "
            f"version={self.contract_version}, status={self.contract_status})>"
        )

    @property
    def is_active(self) -> bool:
        """Check if contract is currently active."""
        return self.contract_status == ContractStatus.ACTIVE

    @property
    def is_deprecated(self) -> bool:
        """Check if contract is deprecated."""
        if self.contract_status == ContractStatus.DEPRECATED:
            return True
        if self.deprecation_date and date.today() >= self.deprecation_date:
            return True
        return False

    @property
    def has_freshness_sla(self) -> bool:
        """Check if contract has freshness SLA."""
        return self.freshness_sla is not None

    @property
    def has_completeness_sla(self) -> bool:
        """Check if contract has completeness SLA."""
        return self.completeness_sla is not None or (
            self.expected_row_count_min is not None or self.expected_row_count_max is not None
        )

    @property
    def has_quality_sla(self) -> bool:
        """Check if contract has quality SLA."""
        return self.quality_score_sla is not None or len(self.critical_quality_rules) > 0

    @property
    def requires_consumer_notification(self) -> bool:
        """Check if consumers need to be notified of changes."""
        return self.consumer_notification_required and len(self.known_consumers) > 0
