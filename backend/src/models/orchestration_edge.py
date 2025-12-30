"""Orchestration-to-Data edges (PRODUCES, CONSUMES, TRANSFORMS, VALIDATES).

These edges link PipelineTasks to DataCapsules, representing how pipelines
interact with data assets.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import JSONType, UUIDType, fk_ref, get_schema_table_args

if TYPE_CHECKING:
    from src.models.capsule import Capsule
    from src.models.ingestion import IngestionJob
    from src.models.pipeline import PipelineTask


class OrchestrationEdgeType(str, Enum):
    """Types of edges between orchestration (tasks) and data (capsules)."""

    PRODUCES = "produces"  # Task creates/updates capsule
    CONSUMES = "consumes"  # Task reads from capsule
    TRANSFORMS = "transforms"  # Task transforms capsule in-place
    VALIDATES = "validates"  # Task validates capsule quality


class TaskDataEdge(Base):
    """Edge between PipelineTask and DataCapsule (orchestration-to-data relationship).

    Represents how tasks interact with data capsules:
    - PRODUCES: Task creates or updates a capsule
    - CONSUMES: Task reads from a capsule
    - TRANSFORMS: Task modifies a capsule in-place
    - VALIDATES: Task validates capsule quality

    This is separate from CapsuleLineage (data-to-data FLOWS_TO edges).
    """

    __tablename__ = "task_data_edges"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(
        UUIDType(),
        primary_key=True,
        default=uuid4,
    )

    # URNs for reference (survive re-ingestion)
    task_urn: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    capsule_urn: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    # Foreign keys for efficient joins
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("pipeline_tasks.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    capsule_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("capsules.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Edge metadata
    edge_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type: produces, consumes, transforms, validates",
    )

    # Operation details
    operation: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Operation type: insert, update, merge, select, etc.",
    )
    access_pattern: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Access pattern: full_scan, selective, partition, etc.",
    )
    transformation_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Transformation type if applicable",
    )
    validation_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Validation type if applicable",
    )

    # Additional metadata
    meta: Mapped[dict] = mapped_column(
        JSONType(),
        default=dict,
        nullable=False,
        comment="Additional edge properties",
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    ingestion_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("ingestion_jobs.id")),
        nullable=True,
    )

    # Relationships
    task: Mapped["PipelineTask"] = relationship(
        "PipelineTask",
        foreign_keys=[task_id],
    )
    capsule: Mapped["Capsule"] = relationship(
        "Capsule",
        foreign_keys=[capsule_id],
    )
    ingestion_job: Mapped[Optional["IngestionJob"]] = relationship(
        back_populates="task_data_edges",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<TaskDataEdge(task='{self.task_urn}', {self.edge_type}='{self.capsule_urn}')>"


class TaskDependencyEdge(Base):
    """Edge between PipelineTasks (task-to-task DEPENDS_ON relationship).

    Represents dependencies within a pipeline (orchestration-to-orchestration).
    """

    __tablename__ = "task_dependency_edges"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(
        UUIDType(),
        primary_key=True,
        default=uuid4,
    )

    # URNs for reference
    source_task_urn: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    target_task_urn: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    # Foreign keys
    source_task_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("pipeline_tasks.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_task_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("pipeline_tasks.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Edge metadata
    edge_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="depends_on",
        comment="Type: depends_on, triggers, etc.",
    )

    # Dependency metadata
    meta: Mapped[dict] = mapped_column(
        JSONType(),
        default=dict,
        nullable=False,
        comment="Trigger rules, weights, etc.",
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    ingestion_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("ingestion_jobs.id")),
        nullable=True,
    )

    # Relationships
    source_task: Mapped["PipelineTask"] = relationship(
        "PipelineTask",
        foreign_keys=[source_task_id],
    )
    target_task: Mapped["PipelineTask"] = relationship(
        "PipelineTask",
        foreign_keys=[target_task_id],
    )
    ingestion_job: Mapped[Optional["IngestionJob"]] = relationship(
        back_populates="task_dependency_edges",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<TaskDependencyEdge(source='{self.source_task_urn}', target='{self.target_task_urn}')>"


class PipelineTriggerEdge(Base):
    """Edge between Pipelines (pipeline-to-pipeline TRIGGERS relationship).

    Represents cross-pipeline dependencies (e.g., ExternalTaskSensor in Airflow).
    """

    __tablename__ = "pipeline_trigger_edges"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(
        UUIDType(),
        primary_key=True,
        default=uuid4,
    )

    # URNs for reference
    source_pipeline_urn: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    target_pipeline_urn: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    # Foreign keys
    source_pipeline_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("pipelines.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_pipeline_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("pipelines.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Edge metadata
    edge_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="triggers",
        comment="Type: triggers, waits_for, etc.",
    )

    # Trigger metadata
    meta: Mapped[dict] = mapped_column(
        JSONType(),
        default=dict,
        nullable=False,
        comment="Trigger conditions, delays, etc.",
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    ingestion_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("ingestion_jobs.id")),
        nullable=True,
    )

    # Relationships
    source_pipeline: Mapped["Pipeline"] = relationship(
        "Pipeline",
        foreign_keys=[source_pipeline_id],
    )
    target_pipeline: Mapped["Pipeline"] = relationship(
        "Pipeline",
        foreign_keys=[target_pipeline_id],
    )
    ingestion_job: Mapped[Optional["IngestionJob"]] = relationship(
        back_populates="pipeline_trigger_edges",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<PipelineTriggerEdge(source='{self.source_pipeline_urn}', target='{self.target_pipeline_urn}')>"
