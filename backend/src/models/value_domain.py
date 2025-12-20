"""Value domain models for controlled vocabularies."""

from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType, fk_ref

if TYPE_CHECKING:
    from src.models.domain import Owner


class DomainType(str, Enum):
    """Types of value domains."""

    ENUM = "enum"  # Enumerated list of values
    PATTERN = "pattern"  # Regex pattern
    RANGE = "range"  # Numeric or date range
    REFERENCE_DATA = "reference_data"  # References another table/column


class ValueDomain(DCSBase):
    """Controlled vocabulary or value domain.

    Defines valid values, patterns, or ranges for columns. Can be used
    to enforce data quality and provide consistent semantics.

    Attributes:
        domain_name: Unique name of the domain.
        domain_type: Type of domain (enum, pattern, range, reference_data).
        description: Description of the domain.
        allowed_values: For enum domains, the list of valid values.
        pattern_regex: For pattern domains, the validation regex.
        pattern_description: Human-readable pattern description.
        min_value: For range domains, the minimum value.
        max_value: For range domains, the maximum value.
        reference_table_urn: For reference data, the URN of the table.
        reference_column_urn: For reference data, the URN of the column.
        owner_id: Owner of this domain definition.
        is_extensible: Whether new values can be added.
        meta: Additional metadata as JSON.
    """

    __tablename__ = "value_domains"

    # Domain definition
    domain_name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    domain_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # 'enum', 'pattern', 'range', 'reference_data'
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # For enum domains
    allowed_values: Mapped[Optional[list]] = mapped_column(
        JSONType(), nullable=True
    )  # [{"code": "A", "label": "Active", "description": "..."}]

    # For pattern domains
    pattern_regex: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pattern_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # For range domains
    min_value: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # String to support various types
    max_value: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # For reference data domains
    reference_table_urn: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    reference_column_urn: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )

    # Governance
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("owners.id")), nullable=True
    )
    is_extensible: Mapped[bool] = mapped_column(
        Boolean, server_default="false"
    )  # Can new values be added?

    # Metadata
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)

    # Relationships
    owner: Mapped[Optional["Owner"]] = relationship(back_populates="value_domains")

    def __repr__(self) -> str:
        """String representation."""
        return f"<ValueDomain(name={self.domain_name}, type={self.domain_type})>"

    @property
    def value_count(self) -> int:
        """Get number of allowed values for enum domains."""
        if self.domain_type == DomainType.ENUM.value and self.allowed_values:
            return len(self.allowed_values)
        return 0

    def validate_value(self, value: str) -> bool:
        """Validate a value against this domain.

        Args:
            value: The value to validate.

        Returns:
            True if valid, False otherwise.
        """
        if self.domain_type == DomainType.ENUM.value and self.allowed_values:
            # Extract codes from allowed_values
            codes = [
                v if isinstance(v, str) else v.get("code")
                for v in self.allowed_values
            ]
            return value in codes

        if self.domain_type == DomainType.PATTERN.value and self.pattern_regex:
            import re

            return bool(re.match(self.pattern_regex, value))

        # For range and reference_data, more complex validation needed
        return True
