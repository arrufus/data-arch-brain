"""Conformance rule models."""

from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType


class RuleSeverity(str, Enum):
    """Severity levels for rules."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RuleCategory(str, Enum):
    """Categories of conformance rules."""

    NAMING = "naming"
    LINEAGE = "lineage"
    PII = "pii"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    OWNERSHIP = "ownership"


class RuleScope(str, Enum):
    """Scope of rule application."""

    CAPSULE = "capsule"
    COLUMN = "column"
    LINEAGE = "lineage"
    GLOBAL = "global"


class Rule(DCSBase):
    """Conformance rule definition."""

    __tablename__ = "rules"

    # Identity
    rule_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Classification
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="warning"
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    rule_set: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    scope: Mapped[str] = mapped_column(String(50), nullable=False)

    # Rule logic
    definition: Mapped[dict] = mapped_column(JSONType(), nullable=False)

    # Status
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="true", index=True)

    # Metadata
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)

    # Relationships
    violations: Mapped[list["Violation"]] = relationship(
        "Violation", back_populates="rule", cascade="all, delete-orphan"
    )


# Import here to avoid circular imports
from src.models.violation import Violation  # noqa: E402, F401
