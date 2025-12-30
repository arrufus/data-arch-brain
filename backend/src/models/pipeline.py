"""Pipeline orchestration models for Airflow and other workflow engines.

These models represent orchestration/pipeline metadata, separate from data capsules.
Pipelines PRODUCE/CONSUME/TRANSFORM data capsules but are not themselves data assets.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Interval, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType, MetadataMixin, URNMixin, fk_ref

if TYPE_CHECKING:
    from src.models.capsule import Capsule
    from src.models.ingestion import IngestionJob
    from src.models.source_system import SourceSystem


class PipelineType(str, Enum):
    """Types of orchestration pipelines."""

    AIRFLOW_DAG = "airflow_dag"
    DBT_RUN = "dbt_run"
    DATABRICKS_JOB = "databricks_job"
    SPARK_JOB = "spark_job"
    PREFECT_FLOW = "prefect_flow"
    DAGSTER_JOB = "dagster_job"
    CUSTOM = "custom"


class TaskType(str, Enum):
    """Types of tasks within pipelines."""

    PYTHON = "python"
    BASH = "bash"
    SQL = "sql"
    DBT = "dbt"
    SPARK = "spark"
    SENSOR = "sensor"
    TRIGGER = "trigger"
    CUSTOM = "custom"


class OperationType(str, Enum):
    """Types of data operations performed by tasks."""

    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    VALIDATE = "validate"
    TEST = "test"
    AGGREGATE = "aggregate"
    JOIN = "join"
    FILTER = "filter"
    UNKNOWN = "unknown"


class RunStatus(str, Enum):
    """Execution status for pipeline and task runs."""

    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"
    QUEUED = "queued"
    SKIPPED = "skipped"
    UP_FOR_RESCHEDULE = "up_for_reschedule"
    UP_FOR_RETRY = "up_for_retry"


class Pipeline(DCSBase, URNMixin, MetadataMixin):
    """Pipeline - represents an orchestration workflow (DAG, job, workflow).

    Pipelines orchestrate data processing but are NOT data capsules themselves.
    They represent the "how" and "when" of data movement.

    URN Format: urn:dcs:pipeline:{tool}:{instance}:{pipeline_id}
    Example: urn:dcs:pipeline:airflow:local-dev:finance_gl_pipeline
    """

    __tablename__ = "pipelines"

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    pipeline_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Source system
    source_system_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("source_systems.id"), ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source_system_identifier: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original ID in source system (e.g., DAG ID in Airflow)",
    )

    # Orchestration metadata
    schedule_interval: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Cron expression or interval string",
    )
    owners: Mapped[list[str]] = mapped_column(
        JSONType(),
        default=list,
        nullable=False,
        comment="List of owner identifiers",
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    is_paused: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
        nullable=False,
    )

    # Configuration
    config: Mapped[dict] = mapped_column(
        JSONType(),
        default=dict,
        nullable=False,
        comment="Pipeline-specific configuration (catchup, max_active_runs, etc.)",
    )

    # Temporal tracking
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Ingestion tracking
    ingestion_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("ingestion_jobs.id")),
        nullable=True,
    )

    # Relationships
    source_system: Mapped[Optional["SourceSystem"]] = relationship(
        "SourceSystem",
        back_populates="pipelines",
    )
    tasks: Mapped[list["PipelineTask"]] = relationship(
        "PipelineTask",
        back_populates="pipeline",
        cascade="all, delete-orphan",
        foreign_keys="PipelineTask.pipeline_id",
    )
    runs: Mapped[list["PipelineRun"]] = relationship(
        "PipelineRun",
        back_populates="pipeline",
        cascade="all, delete-orphan",
    )
    ingestion_job: Mapped[Optional["IngestionJob"]] = relationship(
        back_populates="pipelines",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Pipeline(name='{self.name}', type='{self.pipeline_type}', active={self.is_active})>"


class PipelineTask(DCSBase, URNMixin, MetadataMixin):
    """Pipeline Task - represents a step/task within a pipeline.

    Tasks link to DataCapsules via PRODUCES/CONSUMES/TRANSFORMS edges.

    URN Format: urn:dcs:task:{tool}:{instance}:{pipeline_id}.{task_id}
    Example: urn:dcs:task:airflow:local-dev:finance_gl_pipeline.load_gl_transactions
    """

    __tablename__ = "pipeline_tasks"

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Parent pipeline
    pipeline_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("pipelines.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pipeline_urn: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="URN of parent pipeline for reference",
    )

    # Task metadata
    operator: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Operator class (e.g., PythonOperator, DbtOperator)",
    )
    retries: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    retry_delay: Mapped[Optional[timedelta]] = mapped_column(Interval, nullable=True)
    timeout: Mapped[Optional[timedelta]] = mapped_column(Interval, nullable=True)

    # Data operations
    operation_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Type of data operation (extract, transform, load, etc.)",
    )

    # Tool integration (deep integration with dbt, SQL, etc.)
    tool_reference: Mapped[Optional[dict]] = mapped_column(
        JSONType(),
        nullable=True,
        comment="Reference to transformation code/tool (ToolReference structure)",
    )

    # Documentation
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    doc_md: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Ingestion tracking
    ingestion_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("ingestion_jobs.id")),
        nullable=True,
    )

    # Relationships
    pipeline: Mapped["Pipeline"] = relationship(
        "Pipeline",
        back_populates="tasks",
        foreign_keys=[pipeline_id],
    )
    runs: Mapped[list["TaskRun"]] = relationship(
        "TaskRun",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    ingestion_job: Mapped[Optional["IngestionJob"]] = relationship(
        back_populates="pipeline_tasks",
    )
    # Note: PRODUCES/CONSUMES/TRANSFORMS edges are handled via separate edge tables

    def __repr__(self) -> str:
        """String representation."""
        return f"<PipelineTask(name='{self.name}', type='{self.task_type}', operator='{self.operator}')>"


class PipelineRun(DCSBase):
    """Pipeline Run - execution instance of a pipeline.

    Tracks runtime execution and captures actual data flow.
    """

    __tablename__ = "pipeline_runs"

    # Execution identity
    run_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="External run ID from orchestration system",
    )
    pipeline_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("pipelines.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Execution metadata
    execution_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    trigger: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="How the run was triggered (scheduled, manual, sensor, etc.)",
    )

    # Runtime metadata
    meta: Mapped[dict] = mapped_column(
        JSONType(),
        default=dict,
        nullable=False,
        comment="Runtime configuration and context",
    )

    # Relationships
    pipeline: Mapped["Pipeline"] = relationship(
        "Pipeline",
        back_populates="runs",
    )
    task_runs: Mapped[list["TaskRun"]] = relationship(
        "TaskRun",
        back_populates="pipeline_run",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<PipelineRun(run_id='{self.run_id}', status='{self.status}', date={self.execution_date})>"


class TaskRun(DCSBase):
    """Task Run - execution instance of a task.

    Captures runtime data lineage (which capsules were actually read/written).
    """

    __tablename__ = "task_runs"

    # Execution identity
    task_run_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="External task run ID from orchestration system",
    )
    pipeline_run_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("pipeline_runs.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("pipeline_tasks.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Execution metadata
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Runtime data lineage (critical for tracking actual data flow!)
    data_capsules_read: Mapped[list[str]] = mapped_column(
        JSONType(),
        default=list,
        nullable=False,
        comment="URNs of data capsules read during execution",
    )
    data_capsules_written: Mapped[list[str]] = mapped_column(
        JSONType(),
        default=list,
        nullable=False,
        comment="URNs of data capsules written during execution",
    )
    rows_read: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rows_written: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Runtime metadata
    meta: Mapped[dict] = mapped_column(
        JSONType(),
        default=dict,
        nullable=False,
        comment="Runtime logs, metrics, and context",
    )

    # Relationships
    pipeline_run: Mapped["PipelineRun"] = relationship(
        "PipelineRun",
        back_populates="task_runs",
    )
    task: Mapped["PipelineTask"] = relationship(
        "PipelineTask",
        back_populates="runs",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<TaskRun(task_run_id='{self.task_run_id}', status='{self.status}')>"


# ToolReference structure (stored as JSON in PipelineTask.tool_reference)
# This is not a separate table, but a documented structure for the JSON field:
#
# {
#     "tool": "dbt",  # or "sql", "python", "spark", etc.
#     "reference_type": "model",  # or "script", "notebook", "query"
#     "reference_identifier": "revenue_by_month",  # model name, file path, etc.
#
#     # For dbt integration
#     "dbt_project": "finance_analytics",
#     "dbt_model_name": "revenue_by_month",
#     "dbt_selector": "tag:finance",  # if using selector
#
#     # For SQL integration
#     "sql_script_path": "/path/to/script.sql",
#     "sql_hash": "abc123...",
#
#     # For Python/Spark integration
#     "code_path": "/path/to/script.py",
#     "code_hash": "def456...",
# }
