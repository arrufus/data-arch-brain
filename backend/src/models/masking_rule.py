"""Masking rule models for data anonymization and masking."""

from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType, fk_ref, get_schema_table_args


class MaskingMethod(str, Enum):
    """Methods for data masking and anonymization."""

    REDACTION = "redaction"
    PARTIAL_REDACTION = "partial_redaction"
    SUBSTITUTION = "substitution"
    HASHING = "hashing"
    TOKENIZATION = "tokenization"
    ENCRYPTION = "encryption"
    PSEUDONYMIZATION = "pseudonymization"
    GENERALIZATION = "generalization"
    NOISE_ADDITION = "noise_addition"
    FORMAT_PRESERVING_ENCRYPTION = "format_preserving_encryption"
    DATA_MASKING = "data_masking"
    CUSTOM = "custom"


class MaskingRule(DCSBase):
    """Masking rule for column-level data anonymization.

    Defines how data should be masked/anonymized when accessed by
    specific roles or under specific conditions.
    """

    __tablename__ = "masking_rules"
    __table_args__ = (get_schema_table_args(),)

    # Subject
    column_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("columns.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Rule definition
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    masking_method: Mapped[MaskingMethod] = mapped_column(String(50), nullable=False)

    # Method-specific configuration (flexible JSONB)
    method_config: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False)

    # Conditional masking
    apply_condition: Mapped[Optional[str]] = mapped_column(
        Text(), nullable=True
    )  # SQL WHERE clause
    applies_to_roles: Mapped[list[str]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )  # Roles that see masked data
    exempt_roles: Mapped[list[str]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )  # Roles that see unmasked data

    # Preservation options
    preserve_length: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    preserve_format: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    preserve_type: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default="true"
    )
    preserve_null: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default="true"
    )

    # Reversibility
    is_reversible: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    tokenization_vault: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # Reference to token vault

    # Status
    is_enabled: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default="true", index=True
    )

    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONType(), nullable=False, default=dict, server_default="{}"
    )

    # Relationships
    column: Mapped["Column"] = relationship("Column", back_populates="masking_rules")

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<MaskingRule(id={self.id}, name={self.rule_name}, "
            f"method={self.masking_method}, column_id={self.column_id})>"
        )

    @property
    def is_role_based(self) -> bool:
        """Check if masking is role-based."""
        return (
            (self.applies_to_roles is not None and len(self.applies_to_roles) > 0)
            or (self.exempt_roles is not None and len(self.exempt_roles) > 0)
        )

    @property
    def is_conditional(self) -> bool:
        """Check if masking is conditional."""
        return self.apply_condition is not None

    @property
    def preserves_data_characteristics(self) -> bool:
        """Check if masking preserves data characteristics."""
        return bool(
            (self.preserve_length if self.preserve_length is not None else False)
            or (self.preserve_format if self.preserve_format is not None else False)
            or (self.preserve_type if self.preserve_type is not None else False)
        )

    def applies_to_role(self, role: str) -> bool:
        """Check if masking applies to a specific role.

        Args:
            role: Role name to check

        Returns:
            True if masking should be applied for this role
        """
        # If no roles specified, masking applies to all
        if not self.applies_to_roles or len(self.applies_to_roles) == 0:
            return True

        # Check if role is exempt
        if self.exempt_roles and role in self.exempt_roles:
            return False

        # Check if role is in applies_to list
        return role in self.applies_to_roles
