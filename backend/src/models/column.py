"""Column model for data capsule columns."""

from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType, URNMixin, fk_ref

if TYPE_CHECKING:
    from src.models.business_term import ColumnBusinessTerm
    from src.models.capsule import Capsule
    from src.models.column_profile import ColumnProfile
    from src.models.constraint import ColumnConstraint
    from src.models.data_policy import DataPolicy
    from src.models.lineage import ColumnLineage
    from src.models.masking_rule import MaskingRule
    from src.models.quality_rule import QualityRule
    from src.models.tag import ColumnTag
    from src.models.violation import Violation


class SemanticType(str, Enum):
    """Semantic types for columns."""

    PII = "pii"
    BUSINESS_KEY = "business_key"
    NATURAL_KEY = "natural_key"
    SURROGATE_KEY = "surrogate_key"
    FOREIGN_KEY = "foreign_key"
    METRIC = "metric"
    MEASURE = "measure"
    DIMENSION = "dimension"
    TIMESTAMP = "timestamp"
    EVENT_TIME = "event_time"
    PROCESSING_TIME = "processing_time"


class PIIType(str, Enum):
    """Types of PII data."""

    DIRECT_IDENTIFIER = "direct_identifier"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    HEALTH = "health"
    BIOMETRIC = "biometric"
    DATE_OF_BIRTH = "date_of_birth"
    NAME = "name"
    IP_ADDRESS = "ip_address"
    DEVICE_ID = "device_id"


class PIIDetectionMethod(str, Enum):
    """How PII was detected."""

    TAG = "tag"
    PATTERN = "pattern"
    MANUAL = "manual"


class Column(DCSBase, URNMixin):
    """Column within a Data Capsule."""

    __tablename__ = "columns"

    # Parent reference
    capsule_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("capsules.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Column definition
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ordinal_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_nullable: Mapped[bool] = mapped_column(Boolean, server_default="true")

    # Semantic classification
    semantic_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    pii_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    pii_detected_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Documentation
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Phase 2: Semantic metadata extensions
    unit_of_measure: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Physical unit or currency (ISO 4217, SI units)"
    )
    value_domain: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Reference to controlled vocabulary or enum type"
    )
    value_range_min: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Minimum expected value"
    )
    value_range_max: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Maximum expected value"
    )
    allowed_values: Mapped[Optional[list]] = mapped_column(
        JSONType(), nullable=True, comment="Enumerated list of valid values"
    )
    format_pattern: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Expected format (regex or pattern)"
    )
    example_values: Mapped[list] = mapped_column(
        JSONType(), default=list, nullable=False, comment="Example values for documentation"
    )

    # Metadata
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)
    tags: Mapped[list] = mapped_column(JSONType(), default=list, nullable=False)
    stats: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)

    # Quality indicators
    has_tests: Mapped[bool] = mapped_column(Boolean, server_default="false")
    test_count: Mapped[int] = mapped_column(Integer, server_default="0")

    # Relationships
    capsule: Mapped["Capsule"] = relationship(back_populates="columns")
    violations: Mapped[list["Violation"]] = relationship(
        back_populates="column", cascade="all, delete-orphan"
    )

    # Lineage relationships
    upstream_edges: Mapped[list["ColumnLineage"]] = relationship(
        "ColumnLineage",
        foreign_keys="ColumnLineage.target_column_id",
        back_populates="target_column",
    )
    downstream_edges: Mapped[list["ColumnLineage"]] = relationship(
        "ColumnLineage",
        foreign_keys="ColumnLineage.source_column_id",
        back_populates="source_column",
    )

    # Tag associations (TAGGED_WITH edges)
    tag_associations: Mapped[list["ColumnTag"]] = relationship(
        back_populates="column", cascade="all, delete-orphan"
    )

    # Phase 1: Constraint relationships
    constraints: Mapped[list["ColumnConstraint"]] = relationship(
        back_populates="column", cascade="all, delete-orphan"
    )

    # Phase 2: Business term associations
    business_term_associations: Mapped[list["ColumnBusinessTerm"]] = relationship(
        back_populates="column", cascade="all, delete-orphan"
    )

    # Phase 3: Quality expectations
    quality_rules: Mapped[list["QualityRule"]] = relationship(
        back_populates="column",
        cascade="all, delete-orphan",
        foreign_keys="QualityRule.column_id",
    )
    profiles: Mapped[list["ColumnProfile"]] = relationship(
        back_populates="column", cascade="all, delete-orphan"
    )

    # Phase 4: Policy metadata
    data_policies: Mapped[list["DataPolicy"]] = relationship(
        back_populates="column",
        cascade="all, delete-orphan",
        foreign_keys="DataPolicy.column_id",
    )
    masking_rules: Mapped[list["MaskingRule"]] = relationship(
        back_populates="column", cascade="all, delete-orphan"
    )

    @property
    def is_pii(self) -> bool:
        """Check if column is PII."""
        return self.semantic_type == SemanticType.PII.value or self.pii_type is not None

    @property
    def has_constraints(self) -> bool:
        """Check if column has any constraints."""
        return len(self.constraints) > 0

    @property
    def is_primary_key(self) -> bool:
        """Check if column is part of primary key."""
        return any(c.constraint_type == "primary_key" for c in self.constraints)

    @property
    def is_foreign_key(self) -> bool:
        """Check if column is a foreign key."""
        return any(c.constraint_type == "foreign_key" for c in self.constraints)
