"""Data Capsule model - the core data asset entity."""

from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, MetadataMixin, URNMixin, fk_ref

if TYPE_CHECKING:
    from src.models.column import Column
    from src.models.data_product import CapsuleDataProduct
    from src.models.domain import Domain, Owner
    from src.models.ingestion import IngestionJob
    from src.models.lineage import CapsuleLineage
    from src.models.source_system import SourceSystem
    from src.models.tag import CapsuleTag
    from src.models.violation import Violation


class CapsuleType(str, Enum):
    """Types of data capsules."""

    MODEL = "model"
    SOURCE = "source"
    SEED = "seed"
    SNAPSHOT = "snapshot"
    ANALYSIS = "analysis"
    TEST = "test"


class ArchitectureLayer(str, Enum):
    """Architecture layers in medallion/similar patterns."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    RAW = "raw"
    STAGING = "staging"
    INTERMEDIATE = "intermediate"
    MARTS = "marts"


class Capsule(DCSBase, URNMixin, MetadataMixin):
    """Data Capsule - atomic unit of the data architecture graph."""

    __tablename__ = "capsules"

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    capsule_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Source context
    source_system_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("source_systems.id")), nullable=True
    )
    database_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    schema_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Domain context
    domain_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("domains.id")), nullable=True
    )
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("owners.id")), nullable=True
    )

    # Architecture context
    layer: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    materialization: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Documentation
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Quality indicators
    has_tests: Mapped[bool] = mapped_column(Boolean, server_default="false")
    test_count: Mapped[int] = mapped_column(Integer, server_default="0")
    doc_coverage: Mapped[float] = mapped_column(Float, server_default="0.0")

    # Ingestion tracking
    ingestion_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("ingestion_jobs.id")), nullable=True
    )

    # Relationships
    source_system: Mapped[Optional["SourceSystem"]] = relationship(
        back_populates="capsules"
    )
    domain: Mapped[Optional["Domain"]] = relationship(back_populates="capsules")
    owner: Mapped[Optional["Owner"]] = relationship(back_populates="capsules")
    ingestion_job: Mapped[Optional["IngestionJob"]] = relationship(
        back_populates="capsules"
    )
    columns: Mapped[list["Column"]] = relationship(
        back_populates="capsule", cascade="all, delete-orphan"
    )
    violations: Mapped[list["Violation"]] = relationship(
        back_populates="capsule", cascade="all, delete-orphan"
    )

    # Lineage relationships
    upstream_edges: Mapped[list["CapsuleLineage"]] = relationship(
        "CapsuleLineage",
        foreign_keys="CapsuleLineage.target_id",
        back_populates="target",
    )
    downstream_edges: Mapped[list["CapsuleLineage"]] = relationship(
        "CapsuleLineage",
        foreign_keys="CapsuleLineage.source_id",
        back_populates="source",
    )

    # Data product associations (PART_OF edges)
    data_product_associations: Mapped[list["CapsuleDataProduct"]] = relationship(
        back_populates="capsule", cascade="all, delete-orphan"
    )

    # Tag associations (TAGGED_WITH edges)
    tag_associations: Mapped[list["CapsuleTag"]] = relationship(
        back_populates="capsule", cascade="all, delete-orphan"
    )

    @property
    def column_count(self) -> int:
        """Get number of columns in this capsule."""
        return len(self.columns)

    @property
    def has_pii(self) -> bool:
        """Check if capsule has any PII columns."""
        return any(col.semantic_type == "pii" for col in self.columns)

    @property
    def pii_column_count(self) -> int:
        """Get number of PII columns."""
        return sum(1 for col in self.columns if col.semantic_type == "pii")
