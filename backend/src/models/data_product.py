"""Data Product model for Data Mesh architecture.

This module implements the DataProduct node type and PART_OF edge
from the property graph specification (Section 5.2).
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import (
    DCSBase,
    JSONType,
    UUIDType,
    fk_ref,
    get_schema_table_args,
)

if TYPE_CHECKING:
    from src.models.capsule import Capsule
    from src.models.domain import Domain, Owner


class DataProductStatus(str, Enum):
    """Data product lifecycle status."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class CapsuleRole(str, Enum):
    """Role of a capsule within a data product."""

    MEMBER = "member"  # Standard member capsule
    OUTPUT = "output"  # Output port (published data)
    INPUT = "input"  # Input dependency


class DataProduct(DCSBase):
    """Logical data product grouping capsules.

    DataProduct represents a logical grouping of capsules that together
    form a coherent data product in a Data Mesh architecture. It includes
    SLO definitions for freshness, availability, and quality.

    Attributes:
        name: Human-readable name of the data product.
        description: Detailed description of the data product.
        version: Semantic version of the data product.
        status: Lifecycle status (draft, active, deprecated).
        domain_id: Associated business domain.
        owner_id: Team or individual responsible.
        slo_freshness_hours: Data freshness SLO (max hours since last update).
        slo_availability_percent: Target availability percentage (e.g., 99.9).
        slo_quality_threshold: Minimum conformance score (0.0 to 1.0).
        output_port_schema: JSON schema for the output port contract.
        input_sources: Expected input source URNs.
        meta: Additional metadata as JSON.
        tags: Classification tags.
    """

    __tablename__ = "data_products"

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="draft"
    )

    # Relationships
    domain_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("domains.id")), nullable=True
    )
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("owners.id")), nullable=True
    )

    # SLO Definitions
    slo_freshness_hours: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Max hours since last data update"
    )
    slo_availability_percent: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Target availability (e.g., 99.9)"
    )
    slo_quality_threshold: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Min conformance score (0.0 to 1.0)"
    )

    # Contract definitions
    output_port_schema: Mapped[dict] = mapped_column(
        JSONType(), default=dict, nullable=False
    )
    input_sources: Mapped[list] = mapped_column(
        JSONType(), default=list, nullable=False
    )

    # Metadata
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)
    tags: Mapped[list] = mapped_column(JSONType(), default=list, nullable=False)

    # ORM Relationships
    domain: Mapped[Optional["Domain"]] = relationship(back_populates="data_products")
    owner: Mapped[Optional["Owner"]] = relationship(back_populates="data_products")
    capsule_associations: Mapped[list["CapsuleDataProduct"]] = relationship(
        back_populates="data_product", cascade="all, delete-orphan"
    )

    @property
    def capsules(self) -> list["Capsule"]:
        """Get all capsules in this data product."""
        return [assoc.capsule for assoc in self.capsule_associations]

    @property
    def output_capsules(self) -> list["Capsule"]:
        """Get capsules marked as output ports."""
        return [
            assoc.capsule
            for assoc in self.capsule_associations
            if assoc.role == CapsuleRole.OUTPUT
        ]

    @property
    def input_capsules(self) -> list["Capsule"]:
        """Get capsules marked as input dependencies."""
        return [
            assoc.capsule
            for assoc in self.capsule_associations
            if assoc.role == CapsuleRole.INPUT
        ]

    @property
    def capsule_count(self) -> int:
        """Get total number of capsules in this data product."""
        return len(self.capsule_associations)


class CapsuleDataProduct(Base):
    """Association table for Capsule-DataProduct (PART_OF edge).

    This implements the PART_OF edge type from the property graph spec,
    representing that a capsule is part of a data product.

    Attributes:
        capsule_id: The capsule that is part of the data product.
        data_product_id: The data product containing the capsule.
        role: Role of the capsule (member, output, input).
        meta: Additional edge metadata.
        created_at: When the association was created.
    """

    __tablename__ = "capsule_data_products"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid4)

    capsule_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("capsules.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_product_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("data_products.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(String(50), server_default="member")
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ORM Relationships
    capsule: Mapped["Capsule"] = relationship(back_populates="data_product_associations")
    data_product: Mapped["DataProduct"] = relationship(
        back_populates="capsule_associations"
    )
