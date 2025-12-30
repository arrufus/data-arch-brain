"""Data Capsule model - the core data asset entity."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType, MetadataMixin, URNMixin, fk_ref

if TYPE_CHECKING:
    from src.models.business_term import CapsuleBusinessTerm
    from src.models.column import Column
    from src.models.data_policy import DataPolicy
    from src.models.data_product import CapsuleDataProduct
    from src.models.domain import Domain, Owner
    from src.models.index import CapsuleIndex
    from src.models.ingestion import IngestionJob
    from src.models.lineage import CapsuleLineage
    from src.models.quality_rule import QualityRule
    from src.models.source_system import SourceSystem
    from src.models.tag import CapsuleTag
    from src.models.task_dependency import TaskDependency
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

    # Phase 1: Storage and partition metadata
    partition_strategy: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="Partitioning strategy: range, list, hash, none"
    )
    partition_key: Mapped[Optional[list]] = mapped_column(
        JSONType(), nullable=True, comment="Partition key columns as JSON array"
    )
    partition_expression: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Partition expression or definition"
    )
    storage_format: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="Storage format: parquet, orc, avro, delta, iceberg"
    )
    compression: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="Compression: gzip, snappy, zstd, lz4"
    )
    table_size_bytes: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="Physical size in bytes"
    )
    row_count: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="Approximate row count"
    )
    last_analyzed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last statistics update"
    )

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

    # Phase 1: Index relationships
    indexes: Mapped[list["CapsuleIndex"]] = relationship(
        back_populates="capsule", cascade="all, delete-orphan"
    )

    # Phase 2: Business term associations
    business_term_associations: Mapped[list["CapsuleBusinessTerm"]] = relationship(
        back_populates="capsule", cascade="all, delete-orphan"
    )

    # Phase 3: Quality expectations
    quality_rules: Mapped[list["QualityRule"]] = relationship(
        back_populates="capsule",
        cascade="all, delete-orphan",
        foreign_keys="QualityRule.capsule_id",
    )

    # Phase 4: Policy metadata
    data_policies: Mapped[list["DataPolicy"]] = relationship(
        back_populates="capsule",
        cascade="all, delete-orphan",
        foreign_keys="DataPolicy.capsule_id",
    )

    # Phase 5-6: Provenance and contracts
    versions: Mapped[list["CapsuleVersion"]] = relationship(
        back_populates="capsule", cascade="all, delete-orphan"
    )
    transformation_codes: Mapped[list["TransformationCode"]] = relationship(
        back_populates="capsule",
        cascade="all, delete-orphan",
        foreign_keys="TransformationCode.capsule_id",
    )
    contracts: Mapped[list["CapsuleContract"]] = relationship(
        back_populates="capsule", cascade="all, delete-orphan"
    )
    sla_incidents: Mapped[list["SLAIncident"]] = relationship(
        back_populates="capsule",
        cascade="all, delete-orphan",
        foreign_keys="SLAIncident.capsule_id",
    )

    # Phase 8: Task dependencies (advanced impact analysis)
    task_dependencies: Mapped[list["TaskDependency"]] = relationship(
        back_populates="capsule",
        cascade="all, delete-orphan",
    )

    @property
    def column_count(self) -> int:
        """Get number of columns in this capsule."""
        return len(self.columns)

    @property
    def index_count(self) -> int:
        """Get number of indexes on this capsule."""
        return len(self.indexes)

    @property
    def has_pii(self) -> bool:
        """Check if capsule has any PII columns."""
        return any(col.semantic_type == "pii" for col in self.columns)

    @property
    def pii_column_count(self) -> int:
        """Get number of PII columns."""
        return sum(1 for col in self.columns if col.semantic_type == "pii")
