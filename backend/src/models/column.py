"""Column model for data capsule columns."""

from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DABBase, JSONType, URNMixin, fk_ref

if TYPE_CHECKING:
    from src.models.capsule import Capsule
    from src.models.lineage import ColumnLineage
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


class Column(DABBase, URNMixin):
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

    @property
    def is_pii(self) -> bool:
        """Check if column is PII."""
        return self.semantic_type == SemanticType.PII.value or self.pii_type is not None
