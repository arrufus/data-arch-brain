"""Quality rule models for data quality expectations."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType, fk_ref, get_schema_table_args


class RuleType(str, Enum):
    """Types of quality rules."""

    # Completeness
    NOT_NULL = "not_null"
    NO_EMPTY_STRINGS = "no_empty_strings"
    COMPLETENESS_THRESHOLD = "completeness_threshold"

    # Validity
    VALUE_IN_SET = "value_in_set"
    PATTERN_MATCH = "pattern_match"
    FORMAT_VALID = "format_valid"
    TYPE_VALID = "type_valid"
    RANGE_CHECK = "range_check"
    LENGTH_CHECK = "length_check"

    # Uniqueness
    UNIQUE = "unique"
    UNIQUE_COMBINATION = "unique_combination"
    DUPLICATE_THRESHOLD = "duplicate_threshold"

    # Consistency
    REFERENTIAL_INTEGRITY = "referential_integrity"
    CROSS_FIELD_VALIDATION = "cross_field_validation"

    # Timeliness
    FRESHNESS = "freshness"
    RECENCY_CHECK = "recency_check"

    # Distribution
    DISTRIBUTION_CHECK = "distribution_check"
    OUTLIER_DETECTION = "outlier_detection"
    STATISTICAL_THRESHOLD = "statistical_threshold"

    # Custom
    CUSTOM_SQL = "custom_sql"
    CUSTOM_FUNCTION = "custom_function"


class QualityRuleCategory(str, Enum):
    """Categories of quality rules."""

    COMPLETENESS = "completeness"
    VALIDITY = "validity"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    ACCURACY = "accuracy"
    UNIQUENESS = "uniqueness"
    DISTRIBUTION = "distribution"


class QualityRuleSeverity(str, Enum):
    """Severity levels for quality rules."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class QualityRule(DCSBase):
    """Quality rule definition for data quality expectations.

    Supports column-level or capsule-level quality rules with flexible
    configuration via JSONB.
    """

    __tablename__ = "quality_rules"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN capsule_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN column_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="quality_rules_has_subject",
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

    # Rule definition
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[RuleType] = mapped_column(String(50), nullable=False, index=True)
    rule_category: Mapped[Optional[QualityRuleCategory]] = mapped_column(String(50), nullable=True)

    # Rule parameters (flexible JSONB configuration)
    rule_config: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False)

    # Thresholds
    threshold_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(), nullable=True)
    threshold_operator: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # '>', '>=', '<', '<=', '=', '!='
    threshold_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(), nullable=True)

    # Expected values
    expected_value: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    expected_range_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(), nullable=True)
    expected_range_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(), nullable=True)
    expected_pattern: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)

    # Severity
    severity: Mapped[QualityRuleSeverity] = mapped_column(
        String(20), nullable=False, default=QualityRuleSeverity.WARNING, server_default="warning"
    )
    blocking: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )  # Block pipeline if fails?

    # Status
    is_enabled: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default="true"
    )

    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONType(), nullable=False, default=dict, server_default="{}"
    )

    # Relationships
    capsule: Mapped[Optional["Capsule"]] = relationship(
        "Capsule", back_populates="quality_rules", foreign_keys=[capsule_id]
    )
    column: Mapped[Optional["Column"]] = relationship(
        "Column", back_populates="quality_rules", foreign_keys=[column_id]
    )

    def __repr__(self) -> str:
        """String representation."""
        subject = f"capsule={self.capsule_id}" if self.capsule_id else f"column={self.column_id}"
        return (
            f"<QualityRule(id={self.id}, name={self.rule_name}, "
            f"type={self.rule_type}, {subject})>"
        )

    @property
    def subject_type(self) -> str:
        """Return the subject type (capsule or column)."""
        return "capsule" if self.capsule_id else "column"

    @property
    def is_capsule_rule(self) -> bool:
        """Check if rule applies to capsule."""
        return self.capsule_id is not None

    @property
    def is_column_rule(self) -> bool:
        """Check if rule applies to column."""
        return self.column_id is not None
