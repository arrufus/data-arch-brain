"""Airflow orchestration metamodel - pipelines and tasks.

Revision ID: 20241228_airflow_orchestration
Revises: 20241218_phase7
Create Date: 2024-12-28 00:00:00.000000

This migration adds the orchestration metamodel to correctly represent
Airflow DAGs, tasks, and their relationships to data capsules.

Key changes:
- Pipeline/PipelineTask entities (NOT capsules)
- PipelineRun/TaskRun for execution tracking
- TaskDataEdge for orchestration-to-data relationships (PRODUCES, CONSUMES, etc.)
- TaskDependencyEdge for task-to-task dependencies
- PipelineTriggerEdge for pipeline-to-pipeline triggers
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20241228_airflow_orchestration"
down_revision = "20241218_phase7"
branch_labels = None
depends_on = None

# Schema name
SCHEMA = "dcs"


def upgrade() -> None:
    """Create orchestration metamodel tables."""

    # Create pipelines table
    op.create_table(
        "pipelines",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("urn", sa.String(500), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("pipeline_type", sa.String(50), nullable=False, comment="airflow_dag, dbt_run, databricks_job, etc."),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_system_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_system_identifier", sa.String(255), nullable=False, comment="Original ID in source system (e.g., DAG ID in Airflow)"),
        sa.Column("schedule_interval", sa.String(100), nullable=True, comment="Cron expression or interval string"),
        sa.Column("owners", postgresql.JSONB(), server_default="[]", nullable=False, comment="List of owner identifiers"),
        sa.Column("tags", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("is_paused", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("config", postgresql.JSONB(), server_default="{}", nullable=False, comment="Pipeline-specific configuration"),
        sa.Column("first_seen", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ingestion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("urn"),
        sa.ForeignKeyConstraint(["source_system_id"], [f"{SCHEMA}.source_systems.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingestion_id"], [f"{SCHEMA}.ingestion_jobs.id"]),
        schema=SCHEMA,
    )

    # Create indexes for pipelines
    op.create_index("idx_pipelines_urn", "pipelines", ["urn"], schema=SCHEMA)
    op.create_index("idx_pipelines_name", "pipelines", ["name"], schema=SCHEMA)
    op.create_index("idx_pipelines_type", "pipelines", ["pipeline_type"], schema=SCHEMA)
    op.create_index("idx_pipelines_source_system", "pipelines", ["source_system_id"], schema=SCHEMA)
    op.create_index("idx_pipelines_ingestion", "pipelines", ["ingestion_id"], schema=SCHEMA)

    # Create pipeline_tasks table
    op.create_table(
        "pipeline_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("urn", sa.String(500), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("task_type", sa.String(50), nullable=False, comment="python, bash, sql, dbt, sensor, etc."),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_urn", sa.String(500), nullable=False, comment="URN of parent pipeline for reference"),
        sa.Column("operator", sa.String(100), nullable=True, comment="e.g., PythonOperator, BashOperator"),
        sa.Column("retries", sa.Integer(), server_default="0", nullable=False),
        sa.Column("retry_delay", sa.Interval(), nullable=True),
        sa.Column("timeout", sa.Interval(), nullable=True),
        sa.Column("operation_type", sa.String(50), nullable=True, comment="extract, transform, load, validate, etc."),
        sa.Column("tool_reference", postgresql.JSONB(), nullable=True, comment="Links to dbt model, SQL script, etc."),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("doc_md", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("tags", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ingestion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("urn"),
        sa.ForeignKeyConstraint(["pipeline_id"], [f"{SCHEMA}.pipelines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingestion_id"], [f"{SCHEMA}.ingestion_jobs.id"]),
        schema=SCHEMA,
    )

    # Create indexes for pipeline_tasks
    op.create_index("idx_pipeline_tasks_urn", "pipeline_tasks", ["urn"], schema=SCHEMA)
    op.create_index("idx_pipeline_tasks_name", "pipeline_tasks", ["name"], schema=SCHEMA)
    op.create_index("idx_pipeline_tasks_type", "pipeline_tasks", ["task_type"], schema=SCHEMA)
    op.create_index("idx_pipeline_tasks_pipeline", "pipeline_tasks", ["pipeline_id"], schema=SCHEMA)
    op.create_index("idx_pipeline_tasks_operation", "pipeline_tasks", ["operation_type"], schema=SCHEMA)
    op.create_index("idx_pipeline_tasks_ingestion", "pipeline_tasks", ["ingestion_id"], schema=SCHEMA)

    # Create pipeline_runs table
    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", sa.String(255), nullable=False, comment="External run ID from orchestrator"),
        sa.Column("execution_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, comment="queued, running, success, failed, etc."),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pipeline_id"], [f"{SCHEMA}.pipelines.id"], ondelete="CASCADE"),
        schema=SCHEMA,
    )

    # Create indexes for pipeline_runs
    op.create_index("idx_pipeline_runs_pipeline", "pipeline_runs", ["pipeline_id"], schema=SCHEMA)
    op.create_index("idx_pipeline_runs_run_id", "pipeline_runs", ["run_id"], schema=SCHEMA)
    op.create_index("idx_pipeline_runs_status", "pipeline_runs", ["status"], schema=SCHEMA)
    op.create_index("idx_pipeline_runs_execution_date", "pipeline_runs", ["execution_date"], schema=SCHEMA)
    op.create_index("idx_pipeline_runs_composite", "pipeline_runs", ["pipeline_id", "execution_date"], schema=SCHEMA)

    # Create task_runs table
    op.create_table(
        "task_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", sa.String(255), nullable=False, comment="External task run ID"),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("data_capsules_read", postgresql.JSONB(), server_default="[]", nullable=False, comment="List of capsule URNs read"),
        sa.Column("data_capsules_written", postgresql.JSONB(), server_default="[]", nullable=False, comment="List of capsule URNs written"),
        sa.Column("rows_read", sa.BigInteger(), nullable=True),
        sa.Column("rows_written", sa.BigInteger(), nullable=True),
        sa.Column("bytes_read", sa.BigInteger(), nullable=True),
        sa.Column("bytes_written", sa.BigInteger(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pipeline_run_id"], [f"{SCHEMA}.pipeline_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], [f"{SCHEMA}.pipeline_tasks.id"], ondelete="CASCADE"),
        schema=SCHEMA,
    )

    # Create indexes for task_runs
    op.create_index("idx_task_runs_pipeline_run", "task_runs", ["pipeline_run_id"], schema=SCHEMA)
    op.create_index("idx_task_runs_task", "task_runs", ["task_id"], schema=SCHEMA)
    op.create_index("idx_task_runs_run_id", "task_runs", ["run_id"], schema=SCHEMA)
    op.create_index("idx_task_runs_status", "task_runs", ["status"], schema=SCHEMA)

    # Create task_data_edges table (orchestration-to-data)
    op.create_table(
        "task_data_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("task_urn", sa.String(500), nullable=False),
        sa.Column("capsule_urn", sa.String(500), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("capsule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_type", sa.String(50), nullable=False, comment="produces, consumes, transforms, validates"),
        sa.Column("operation", sa.String(50), nullable=True, comment="insert, update, merge, select, etc."),
        sa.Column("access_pattern", sa.String(50), nullable=True, comment="full_scan, selective, partition, etc."),
        sa.Column("transformation_type", sa.String(50), nullable=True),
        sa.Column("validation_type", sa.String(50), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ingestion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["task_id"], [f"{SCHEMA}.pipeline_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["capsule_id"], [f"{SCHEMA}.capsules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingestion_id"], [f"{SCHEMA}.ingestion_jobs.id"]),
        schema=SCHEMA,
    )

    # Create indexes for task_data_edges
    op.create_index("idx_task_data_edges_task_urn", "task_data_edges", ["task_urn"], schema=SCHEMA)
    op.create_index("idx_task_data_edges_capsule_urn", "task_data_edges", ["capsule_urn"], schema=SCHEMA)
    op.create_index("idx_task_data_edges_task", "task_data_edges", ["task_id"], schema=SCHEMA)
    op.create_index("idx_task_data_edges_capsule", "task_data_edges", ["capsule_id"], schema=SCHEMA)
    op.create_index("idx_task_data_edges_type", "task_data_edges", ["edge_type"], schema=SCHEMA)
    op.create_index("idx_task_data_edges_ingestion", "task_data_edges", ["ingestion_id"], schema=SCHEMA)

    # Create task_dependency_edges table (orchestration-to-orchestration: task-to-task)
    op.create_table(
        "task_dependency_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_task_urn", sa.String(500), nullable=False),
        sa.Column("target_task_urn", sa.String(500), nullable=False),
        sa.Column("source_task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_type", sa.String(50), server_default="depends_on", nullable=False, comment="depends_on, triggers, etc."),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False, comment="Trigger rules, weights, etc."),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ingestion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_task_id"], [f"{SCHEMA}.pipeline_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_task_id"], [f"{SCHEMA}.pipeline_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingestion_id"], [f"{SCHEMA}.ingestion_jobs.id"]),
        schema=SCHEMA,
    )

    # Create indexes for task_dependency_edges
    op.create_index("idx_task_dependency_edges_source_urn", "task_dependency_edges", ["source_task_urn"], schema=SCHEMA)
    op.create_index("idx_task_dependency_edges_target_urn", "task_dependency_edges", ["target_task_urn"], schema=SCHEMA)
    op.create_index("idx_task_dependency_edges_source", "task_dependency_edges", ["source_task_id"], schema=SCHEMA)
    op.create_index("idx_task_dependency_edges_target", "task_dependency_edges", ["target_task_id"], schema=SCHEMA)
    op.create_index("idx_task_dependency_edges_ingestion", "task_dependency_edges", ["ingestion_id"], schema=SCHEMA)

    # Create pipeline_trigger_edges table (orchestration-to-orchestration: pipeline-to-pipeline)
    op.create_table(
        "pipeline_trigger_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_pipeline_urn", sa.String(500), nullable=False),
        sa.Column("target_pipeline_urn", sa.String(500), nullable=False),
        sa.Column("source_pipeline_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_pipeline_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_type", sa.String(50), server_default="triggers", nullable=False, comment="triggers, waits_for, etc."),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False, comment="Trigger conditions, delays, etc."),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ingestion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_pipeline_id"], [f"{SCHEMA}.pipelines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_pipeline_id"], [f"{SCHEMA}.pipelines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingestion_id"], [f"{SCHEMA}.ingestion_jobs.id"]),
        schema=SCHEMA,
    )

    # Create indexes for pipeline_trigger_edges
    op.create_index("idx_pipeline_trigger_edges_source_urn", "pipeline_trigger_edges", ["source_pipeline_urn"], schema=SCHEMA)
    op.create_index("idx_pipeline_trigger_edges_target_urn", "pipeline_trigger_edges", ["target_pipeline_urn"], schema=SCHEMA)
    op.create_index("idx_pipeline_trigger_edges_source", "pipeline_trigger_edges", ["source_pipeline_id"], schema=SCHEMA)
    op.create_index("idx_pipeline_trigger_edges_target", "pipeline_trigger_edges", ["target_pipeline_id"], schema=SCHEMA)
    op.create_index("idx_pipeline_trigger_edges_ingestion", "pipeline_trigger_edges", ["ingestion_id"], schema=SCHEMA)


def downgrade() -> None:
    """Drop orchestration metamodel tables."""

    # Drop edge tables first (due to foreign keys)
    op.drop_table("pipeline_trigger_edges", schema=SCHEMA)
    op.drop_table("task_dependency_edges", schema=SCHEMA)
    op.drop_table("task_data_edges", schema=SCHEMA)

    # Drop execution tracking tables
    op.drop_table("task_runs", schema=SCHEMA)
    op.drop_table("pipeline_runs", schema=SCHEMA)

    # Drop pipeline structure tables
    op.drop_table("pipeline_tasks", schema=SCHEMA)
    op.drop_table("pipelines", schema=SCHEMA)
