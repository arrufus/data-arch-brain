"""Lineage models for capsule and column relationships."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import JSONType, UUIDType, fk_ref, get_schema_table_args

if TYPE_CHECKING:
    from src.models.capsule import Capsule
    from src.models.column import Column
    from src.models.ingestion import IngestionJob
    from src.models.pipeline import PipelineTask


class CapsuleLineage(Base):
    """Lineage edge between capsules (FLOWS_TO relationship)."""

    __tablename__ = "capsule_lineage"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(
        UUIDType(),
        primary_key=True,
        default=uuid4,
    )

    # URNs for reference (survive re-ingestion)
    source_urn: Mapped[str] = mapped_column(String(500), nullable=False)
    target_urn: Mapped[str] = mapped_column(String(500), nullable=False)

    # Foreign keys for efficient joins
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("capsules.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("capsules.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Edge metadata
    edge_type: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="flows_to"
    )
    transformation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ingestion_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("ingestion_jobs.id")), nullable=True
    )

    # Relationships
    source: Mapped["Capsule"] = relationship(
        "Capsule", foreign_keys=[source_id], back_populates="downstream_edges"
    )
    target: Mapped["Capsule"] = relationship(
        "Capsule", foreign_keys=[target_id], back_populates="upstream_edges"
    )
    ingestion_job: Mapped[Optional["IngestionJob"]] = relationship(
        back_populates="capsule_lineage_edges"
    )
    transformation_codes: Mapped[list["TransformationCode"]] = relationship(
        back_populates="lineage_edge",
        cascade="all, delete-orphan",
        foreign_keys="TransformationCode.lineage_edge_id",
    )


class ColumnLineage(Base):
    """Column-to-column lineage edge (Phase 6)."""

    __tablename__ = "column_lineage"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(
        UUIDType(),
        primary_key=True,
        default=uuid4,
    )

    # Source column
    source_column_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("columns.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_column_urn: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    # Target column
    target_column_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("columns.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_column_urn: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    # Lineage metadata
    edge_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="derives_from, same_as, transforms_to"
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        default=Decimal("1.0"),
        server_default="1.0",
        comment="0.0 to 1.0 confidence score"
    )

    # Transformation
    transformation_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="cast, aggregate, join, formula, etc."
    )
    transformation_logic: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="SQL expression, formula, etc."
    )

    # Detection method
    detected_by: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="sql_parser, dbt_metadata, manual"
    )
    detection_metadata: Mapped[dict] = mapped_column(
        JSONType(),
        nullable=False,
        default=dict,
        server_default="{}"
    )

    # Audit
    ingestion_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("ingestion_jobs.id")),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    source_column: Mapped["Column"] = relationship(
        "Column",
        foreign_keys=[source_column_id],
        back_populates="downstream_edges"
    )
    target_column: Mapped["Column"] = relationship(
        "Column",
        foreign_keys=[target_column_id],
        back_populates="upstream_edges"
    )
    ingestion_job: Mapped[Optional["IngestionJob"]] = relationship(
        back_populates="column_lineage_edges"
    )


class TaskColumnEdge(Base):
    """Edge between pipeline task and column (Phase 6)."""

    __tablename__ = "task_column_edges"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(
        UUIDType(),
        primary_key=True,
        default=uuid4,
    )

    # Task reference
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("pipeline_tasks.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_urn: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    # Column reference
    column_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("columns.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    column_urn: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    # Edge metadata
    edge_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="reads, writes, transforms"
    )

    # Transformation details
    transformation_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="select, insert, update, aggregate, etc."
    )
    transformation_logic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    operation: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="select, insert, update, aggregate, etc."
    )

    # Audit
    ingestion_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("ingestion_jobs.id")),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # Relationships
    task: Mapped["PipelineTask"] = relationship("PipelineTask")
    column: Mapped["Column"] = relationship("Column")


class ColumnVersion(Base):
    """Column version for schema evolution tracking (Phase 6)."""

    __tablename__ = "column_versions"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(
        UUIDType(),
        primary_key=True,
        default=uuid4,
    )

    # Column reference
    column_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("columns.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    column_urn: Mapped[str] = mapped_column(String(500), nullable=False)

    # Version info
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    valid_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Schema snapshot
    data_type: Mapped[str] = mapped_column(String(100), nullable=False)
    is_nullable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Change metadata
    change_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="created, modified, deleted, renamed"
    )
    change_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    breaking_change: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True
    )

    # Audit
    changed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ingestion_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("ingestion_jobs.id")),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    # Relationships
    column: Mapped["Column"] = relationship("Column")
    ingestion_job: Mapped[Optional["IngestionJob"]] = relationship()
