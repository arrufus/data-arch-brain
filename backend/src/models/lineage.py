"""Lineage models for capsule and column relationships."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import JSONType, UUIDType, fk_ref, get_schema_table_args

if TYPE_CHECKING:
    from src.models.capsule import Capsule
    from src.models.column import Column
    from src.models.ingestion import IngestionJob


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


class ColumnLineage(Base):
    """Lineage edge between columns (DERIVED_FROM relationship)."""

    __tablename__ = "column_lineage"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(
        UUIDType(),
        primary_key=True,
        default=uuid4,
    )

    # URNs for reference
    source_urn: Mapped[str] = mapped_column(String(500), nullable=False)
    target_urn: Mapped[str] = mapped_column(String(500), nullable=False)

    # Foreign keys
    source_column_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("columns.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_column_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("columns.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Transformation details
    transformation_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    transformation_expr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ingestion_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("ingestion_jobs.id")), nullable=True
    )

    # Relationships
    source_column: Mapped["Column"] = relationship(
        "Column", foreign_keys=[source_column_id], back_populates="downstream_edges"
    )
    target_column: Mapped["Column"] = relationship(
        "Column", foreign_keys=[target_column_id], back_populates="upstream_edges"
    )
    ingestion_job: Mapped[Optional["IngestionJob"]] = relationship(
        back_populates="column_lineage_edges"
    )
