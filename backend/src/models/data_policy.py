"""Data policy models for policy metadata and governance."""

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, ForeignKey, Interval, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType, fk_ref, get_schema_table_args


class SensitivityLevel(str, Enum):
    """Data sensitivity classification levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    SECRET = "secret"


class DeletionAction(str, Enum):
    """Actions to take when retention period expires."""

    HARD_DELETE = "hard_delete"
    ANONYMIZE = "anonymize"
    ARCHIVE = "archive"


class PolicyStatus(str, Enum):
    """Policy lifecycle status."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUSPENDED = "suspended"


class DataPolicy(DCSBase):
    """Comprehensive policy metadata for data governance.

    Defines retention, masking, access control, compliance, and audit
    requirements for capsules or columns.
    """

    __tablename__ = "data_policies"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN capsule_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN column_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="data_policies_has_subject",
        ),
        get_schema_table_args(),
    )

    # Subject (one of these must be set)
    capsule_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("capsules.id"), ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    column_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("columns.id"), ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Classification
    sensitivity_level: Mapped[SensitivityLevel] = mapped_column(
        String(50), nullable=False, index=True
    )
    classification_tags: Mapped[list[str]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )  # ['gdpr', 'pci', 'hipaa', 'ccpa']

    # Retention policy
    retention_period: Mapped[Optional[timedelta]] = mapped_column(Interval(), nullable=True)
    retention_start: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # 'ingestion', 'last_modified', 'business_date'
    deletion_action: Mapped[Optional[DeletionAction]] = mapped_column(String(50), nullable=True)
    legal_hold: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")

    # Geographic restrictions
    allowed_regions: Mapped[list[str]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )  # ['EU', 'US', 'CA']
    restricted_regions: Mapped[list[str]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )  # ['CN', 'RU']
    data_residency: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # 'EU', 'US', 'multi_region'
    cross_border_transfer: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default="true"
    )

    # Access control
    min_access_level: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # 'public', 'authenticated', 'privileged', 'admin'
    allowed_roles: Mapped[list[str]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )  # ['data_analyst', 'data_scientist']
    denied_roles: Mapped[list[str]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )

    # Approved uses
    approved_purposes: Mapped[list[str]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )  # ['analytics', 'ml_training', 'reporting']
    prohibited_purposes: Mapped[list[str]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )  # ['marketing', 'profiling']

    # Masking/anonymization
    requires_masking: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    masking_method: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # 'hash', 'tokenize', 'redact', 'encrypt', 'pseudonymize'
    masking_conditions: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONType(), nullable=True
    )  # Conditions when masking applies

    # Encryption
    encryption_required: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    encryption_method: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # 'aes256', 'rsa', 'field_level'
    encryption_at_rest: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    encryption_in_transit: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default="true"
    )

    # Compliance tracking
    compliance_frameworks: Mapped[list[str]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )  # ['GDPR', 'CCPA', 'HIPAA', 'PCI-DSS']
    consent_required: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    right_to_erasure: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )  # GDPR Article 17

    # Audit requirements
    audit_log_required: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    audit_retention_period: Mapped[Optional[timedelta]] = mapped_column(
        Interval(), nullable=True
    )

    # Governance
    policy_owner_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("owners.id")),
        nullable=True,
    )
    approved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    review_frequency: Mapped[Optional[timedelta]] = mapped_column(
        Interval(), nullable=True
    )  # e.g., '1 year'
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    next_review_date: Mapped[Optional[date]] = mapped_column(Date(), nullable=True, index=True)

    # Status
    policy_status: Mapped[PolicyStatus] = mapped_column(
        String(50), nullable=False, default=PolicyStatus.ACTIVE, server_default="active"
    )
    effective_from: Mapped[Optional[date]] = mapped_column(Date(), nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date(), nullable=True)

    # Metadata
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONType(), nullable=False, default=dict, server_default="{}"
    )

    # Relationships
    capsule: Mapped[Optional["Capsule"]] = relationship(
        "Capsule", back_populates="data_policies", foreign_keys=[capsule_id]
    )
    column: Mapped[Optional["Column"]] = relationship(
        "Column", back_populates="data_policies", foreign_keys=[column_id]
    )
    policy_owner: Mapped[Optional["Owner"]] = relationship(
        "Owner", back_populates="data_policies", foreign_keys=[policy_owner_id]
    )

    def __repr__(self) -> str:
        """String representation."""
        subject = f"capsule={self.capsule_id}" if self.capsule_id else f"column={self.column_id}"
        return (
            f"<DataPolicy(id={self.id}, sensitivity={self.sensitivity_level}, "
            f"status={self.policy_status}, {subject})>"
        )

    @property
    def subject_type(self) -> str:
        """Return the subject type (capsule or column)."""
        return "capsule" if self.capsule_id else "column"

    @property
    def is_active(self) -> bool:
        """Check if policy is currently active."""
        if self.policy_status != PolicyStatus.ACTIVE:
            return False

        today = date.today()

        if self.effective_from and today < self.effective_from:
            return False

        if self.effective_to and today > self.effective_to:
            return False

        return True

    @property
    def requires_review(self) -> bool:
        """Check if policy requires review."""
        if not self.next_review_date:
            return False
        return date.today() >= self.next_review_date

    @property
    def is_pii_policy(self) -> bool:
        """Check if this policy governs PII data."""
        return any(
            tag.lower() in ["gdpr", "ccpa", "pii", "personal_data"]
            for tag in self.classification_tags
        )

    @property
    def is_regulated(self) -> bool:
        """Check if this policy involves regulated data."""
        return len(self.compliance_frameworks) > 0
