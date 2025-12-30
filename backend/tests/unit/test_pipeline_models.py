"""Unit tests for Pipeline orchestration models."""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.models.pipeline import (
    OperationType,
    Pipeline,
    PipelineRun,
    PipelineTask,
    PipelineType,
    RunStatus,
    TaskRun,
    TaskType,
)
from src.models.orchestration_edge import (
    OrchestrationEdgeType,
    PipelineTriggerEdge,
    TaskDataEdge,
    TaskDependencyEdge,
)


class TestPipelineModel:
    """Tests for the Pipeline model."""

    def test_create_pipeline_minimal(self):
        """Test creating a pipeline with minimal fields."""
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:local-dev:test_dag",
            name="test_dag",
            pipeline_type=PipelineType.AIRFLOW_DAG,
            source_system_identifier="test_dag",
        )

        assert pipeline.urn == "urn:dcs:pipeline:airflow:local-dev:test_dag"
        assert pipeline.name == "test_dag"
        assert pipeline.pipeline_type == PipelineType.AIRFLOW_DAG
        assert pipeline.source_system_identifier == "test_dag"
        assert pipeline.description is None

    def test_create_pipeline_full(self):
        """Test creating a pipeline with all fields."""
        source_system_id = uuid4()
        ingestion_id = uuid4()

        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:prod:finance_gl_pipeline",
            name="finance_gl_pipeline",
            pipeline_type=PipelineType.AIRFLOW_DAG,
            description="Finance General Ledger processing pipeline",
            source_system_id=source_system_id,
            source_system_identifier="finance_gl_pipeline",
            schedule_interval="0 1 * * *",
            is_paused=False,
            is_active=True,
            owners=["finance-team"],
            tags=["finance", "general_ledger", "sox", "tier-1"],
            meta={
                "on_failure_callback": "notify_finance_team",
                "sla_hours": 2,
            },
            config={"catchup": False, "max_active_runs": 1},
            ingestion_id=ingestion_id,
        )

        assert pipeline.name == "finance_gl_pipeline"
        assert pipeline.pipeline_type == PipelineType.AIRFLOW_DAG
        assert "General Ledger" in pipeline.description
        assert pipeline.source_system_id == source_system_id
        assert pipeline.source_system_identifier == "finance_gl_pipeline"
        assert pipeline.schedule_interval == "0 1 * * *"
        assert pipeline.is_paused is False
        assert pipeline.is_active is True
        assert "finance-team" in pipeline.owners
        assert "sox" in pipeline.tags
        assert pipeline.meta["sla_hours"] == 2
        assert pipeline.config["catchup"] is False
        assert pipeline.ingestion_id == ingestion_id

    def test_pipeline_types(self):
        """Test different pipeline types."""
        # Airflow DAG
        airflow_pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:prod:dag1",
            name="dag1",
            pipeline_type=PipelineType.AIRFLOW_DAG,
            source_system_identifier="dag1",
        )
        assert airflow_pipeline.pipeline_type == PipelineType.AIRFLOW_DAG

        # dbt run
        dbt_pipeline = Pipeline(
            urn="urn:dcs:pipeline:dbt:prod:daily_run",
            name="daily_run",
            pipeline_type=PipelineType.DBT_RUN,
            source_system_identifier="daily_run",
        )
        assert dbt_pipeline.pipeline_type == PipelineType.DBT_RUN

        # Databricks job
        databricks_pipeline = Pipeline(
            urn="urn:dcs:pipeline:databricks:prod:etl_job",
            name="etl_job",
            pipeline_type=PipelineType.DATABRICKS_JOB,
            source_system_identifier="etl_job",
        )
        assert databricks_pipeline.pipeline_type == PipelineType.DATABRICKS_JOB

    def test_pipeline_pause_state(self):
        """Test pipeline pause state transitions."""
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:prod:test",
            name="test",
            pipeline_type=PipelineType.AIRFLOW_DAG,
            source_system_identifier="test",
            is_paused=False,
        )

        # Active pipeline
        assert pipeline.is_paused is False

        # Pause pipeline
        pipeline.is_paused = True
        assert pipeline.is_paused is True

        # Unpause pipeline
        pipeline.is_paused = False
        assert pipeline.is_paused is False


class TestPipelineTaskModel:
    """Tests for the PipelineTask model."""

    def test_create_task_minimal(self):
        """Test creating a pipeline task with minimal fields."""
        pipeline_id = uuid4()
        task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:test_dag.task1",
            name="task1",
            task_type=TaskType.PYTHON,
            pipeline_id=pipeline_id,
            pipeline_urn="urn:dcs:pipeline:airflow:prod:test_dag",
        )

        assert task.urn == "urn:dcs:task:airflow:prod:test_dag.task1"
        assert task.name == "task1"
        assert task.task_type == TaskType.PYTHON
        assert task.pipeline_id == pipeline_id
        assert task.operator is None

    def test_create_task_full(self):
        """Test creating a pipeline task with all fields."""
        pipeline_id = uuid4()
        ingestion_id = uuid4()

        task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:finance_gl_pipeline.load_gl_transactions",
            name="load_gl_transactions",
            task_type=TaskType.DBT,
            description="Load GL transactions from ERP",
            pipeline_id=pipeline_id,
            pipeline_urn="urn:dcs:pipeline:airflow:prod:finance_gl_pipeline",
            operator="DbtRunOperator",
            operation_type=OperationType.LOAD,
            timeout=timedelta(minutes=30),
            retries=3,
            retry_delay=timedelta(minutes=5),
            tool_reference={
                "tool": "dbt",
                "reference_type": "model",
                "reference_identifier": "gl_transactions",
                "dbt_project": "finance_analytics",
            },
            meta={
                "pool": "finance_pool",
                "priority_weight": 10,
                "trigger_rule": "all_success",
            },
            ingestion_id=ingestion_id,
        )

        assert task.name == "load_gl_transactions"
        assert task.task_type == TaskType.DBT
        assert "ERP" in task.description
        assert task.operator == "DbtRunOperator"
        assert task.operation_type == OperationType.LOAD
        assert task.timeout == timedelta(minutes=30)
        assert task.retries == 3
        assert task.retry_delay == timedelta(minutes=5)
        assert task.tool_reference["tool"] == "dbt"
        assert task.tool_reference["reference_identifier"] == "gl_transactions"
        assert task.meta["pool"] == "finance_pool"
        assert task.ingestion_id == ingestion_id

    def test_task_types(self):
        """Test different task types."""
        pipeline_id = uuid4()
        pipeline_urn = "urn:dcs:pipeline:airflow:prod:dag"

        # Python task
        python_task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:dag.python_task",
            name="python_task",
            task_type=TaskType.PYTHON,
            pipeline_id=pipeline_id,
            pipeline_urn=pipeline_urn,
        )
        assert python_task.task_type == TaskType.PYTHON

        # SQL task
        sql_task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:dag.sql_task",
            name="sql_task",
            task_type=TaskType.SQL,
            pipeline_id=pipeline_id,
            pipeline_urn=pipeline_urn,
        )
        assert sql_task.task_type == TaskType.SQL

        # dbt task
        dbt_task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:dag.dbt_task",
            name="dbt_task",
            task_type=TaskType.DBT,
            pipeline_id=pipeline_id,
            pipeline_urn=pipeline_urn,
        )
        assert dbt_task.task_type == TaskType.DBT

        # Sensor task
        sensor_task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:dag.sensor_task",
            name="sensor_task",
            task_type=TaskType.SENSOR,
            pipeline_id=pipeline_id,
            pipeline_urn=pipeline_urn,
        )
        assert sensor_task.task_type == TaskType.SENSOR

    def test_operation_types(self):
        """Test different operation types."""
        pipeline_id = uuid4()
        pipeline_urn = "urn:dcs:pipeline:airflow:prod:dag"

        # Extract operation
        extract_task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:dag.extract",
            name="extract",
            task_type=TaskType.PYTHON,
            pipeline_id=pipeline_id,
            pipeline_urn=pipeline_urn,
            operation_type=OperationType.EXTRACT,
        )
        assert extract_task.operation_type == OperationType.EXTRACT

        # Transform operation
        transform_task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:dag.transform",
            name="transform",
            task_type=TaskType.DBT,
            pipeline_id=pipeline_id,
            pipeline_urn=pipeline_urn,
            operation_type=OperationType.TRANSFORM,
        )
        assert transform_task.operation_type == OperationType.TRANSFORM

        # Load operation
        load_task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:dag.load",
            name="load",
            task_type=TaskType.SQL,
            pipeline_id=pipeline_id,
            pipeline_urn=pipeline_urn,
            operation_type=OperationType.LOAD,
        )
        assert load_task.operation_type == OperationType.LOAD

    def test_tool_reference(self):
        """Test tool reference linking."""
        pipeline_id = uuid4()

        # dbt model reference
        dbt_task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:dag.dbt_task",
            name="dbt_task",
            task_type=TaskType.DBT,
            pipeline_id=pipeline_id,
            pipeline_urn="urn:dcs:pipeline:airflow:prod:dag",
            tool_reference={
                "tool": "dbt",
                "reference_type": "model",
                "reference_identifier": "stg_customers",
                "dbt_project": "jaffle_shop",
            },
        )
        assert dbt_task.tool_reference["tool"] == "dbt"
        assert dbt_task.tool_reference["reference_identifier"] == "stg_customers"


class TestPipelineRunModel:
    """Tests for the PipelineRun model."""

    def test_create_pipeline_run_minimal(self):
        """Test creating a pipeline run with minimal fields."""
        pipeline_id = uuid4()

        pipeline_run = PipelineRun(
            pipeline_id=pipeline_id,
            run_id="manual__2024-12-28T10:00:00+00:00",
            execution_date=datetime.now(timezone.utc),
            start_time=datetime.now(timezone.utc),
            status=RunStatus.RUNNING,
        )

        assert pipeline_run.pipeline_id == pipeline_id
        assert pipeline_run.run_id == "manual__2024-12-28T10:00:00+00:00"
        assert pipeline_run.status == RunStatus.RUNNING
        assert pipeline_run.end_time is None

    def test_create_pipeline_run_full(self):
        """Test creating a pipeline run with all fields."""
        pipeline_id = uuid4()
        start_time = datetime.now(timezone.utc)
        execution_date = datetime.now(timezone.utc)

        pipeline_run = PipelineRun(
            pipeline_id=pipeline_id,
            run_id="scheduled__2024-12-28T01:00:00+00:00",
            execution_date=execution_date,
            status=RunStatus.SUCCESS,
            start_time=start_time,
            end_time=datetime.now(timezone.utc),
            trigger="scheduled",
            meta={"dag_run_type": "scheduled", "external_trigger": False},
        )

        assert pipeline_run.status == RunStatus.SUCCESS
        assert pipeline_run.start_time == start_time
        assert pipeline_run.trigger == "scheduled"
        assert pipeline_run.meta["dag_run_type"] == "scheduled"

    def test_run_statuses(self):
        """Test different run statuses."""
        pipeline_id = uuid4()
        execution_date = datetime.now(timezone.utc)
        start_time = datetime.now(timezone.utc)

        # Queued
        queued_run = PipelineRun(
            pipeline_id=pipeline_id,
            run_id="run1",
            execution_date=execution_date,
            start_time=start_time,
            status=RunStatus.QUEUED,
        )
        assert queued_run.status == RunStatus.QUEUED

        # Running
        running_run = PipelineRun(
            pipeline_id=pipeline_id,
            run_id="run2",
            execution_date=execution_date,
            start_time=start_time,
            status=RunStatus.RUNNING,
        )
        assert running_run.status == RunStatus.RUNNING

        # Success
        success_run = PipelineRun(
            pipeline_id=pipeline_id,
            run_id="run3",
            execution_date=execution_date,
            start_time=start_time,
            status=RunStatus.SUCCESS,
        )
        assert success_run.status == RunStatus.SUCCESS

        # Failed
        failed_run = PipelineRun(
            pipeline_id=pipeline_id,
            run_id="run4",
            execution_date=execution_date,
            start_time=start_time,
            status=RunStatus.FAILED,
        )
        assert failed_run.status == RunStatus.FAILED


class TestTaskRunModel:
    """Tests for the TaskRun model."""

    def test_create_task_run_minimal(self):
        """Test creating a task run with minimal fields."""
        pipeline_run_id = uuid4()
        task_id = uuid4()

        task_run = TaskRun(
            pipeline_run_id=pipeline_run_id,
            task_id=task_id,
            task_run_id="task_run_1",
            start_time=datetime.now(timezone.utc),
            status=RunStatus.RUNNING,
        )

        assert task_run.pipeline_run_id == pipeline_run_id
        assert task_run.task_id == task_id
        assert task_run.task_run_id == "task_run_1"
        assert task_run.status == RunStatus.RUNNING

    def test_create_task_run_with_data_tracking(self):
        """Test creating a task run with data capsule tracking."""
        pipeline_run_id = uuid4()
        task_id = uuid4()

        task_run = TaskRun(
            pipeline_run_id=pipeline_run_id,
            task_id=task_id,
            task_run_id="task_run_1",
            status=RunStatus.SUCCESS,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            data_capsules_read=[
                "urn:dcs:postgres:table:finance_erp.master:chart_of_accounts",
            ],
            data_capsules_written=[
                "urn:dcs:postgres:table:finance_erp.facts:gl_transactions",
            ],
            rows_read=1500,
            rows_written=1500,
            meta={"xcom_pushed": True, "log_url": "http://airflow/logs/..."},
        )

        assert task_run.status == RunStatus.SUCCESS
        assert len(task_run.data_capsules_read) == 1
        assert len(task_run.data_capsules_written) == 1
        assert "chart_of_accounts" in task_run.data_capsules_read[0]
        assert "gl_transactions" in task_run.data_capsules_written[0]
        assert task_run.rows_read == 1500
        assert task_run.rows_written == 1500


class TestTaskDataEdge:
    """Tests for the TaskDataEdge model."""

    def test_create_produces_edge(self):
        """Test creating a PRODUCES edge (task creates capsule)."""
        task_id = uuid4()
        capsule_id = uuid4()
        ingestion_id = uuid4()

        edge = TaskDataEdge(
            task_urn="urn:dcs:task:airflow:prod:dag.load_task",
            capsule_urn="urn:dcs:postgres:table:analytics.marts:revenue_by_month",
            task_id=task_id,
            capsule_id=capsule_id,
            edge_type=OrchestrationEdgeType.PRODUCES,
            operation="insert",
            meta={"records_written": 12},
            ingestion_id=ingestion_id,
        )

        assert edge.edge_type == OrchestrationEdgeType.PRODUCES
        assert edge.operation == "insert"
        assert edge.task_id == task_id
        assert edge.capsule_id == capsule_id
        assert edge.meta["records_written"] == 12

    def test_create_consumes_edge(self):
        """Test creating a CONSUMES edge (task reads capsule)."""
        task_id = uuid4()
        capsule_id = uuid4()

        edge = TaskDataEdge(
            task_urn="urn:dcs:task:airflow:prod:dag.read_task",
            capsule_urn="urn:dcs:postgres:table:raw.source:customers",
            task_id=task_id,
            capsule_id=capsule_id,
            edge_type=OrchestrationEdgeType.CONSUMES,
            operation="select",
            access_pattern="full_scan",
        )

        assert edge.edge_type == OrchestrationEdgeType.CONSUMES
        assert edge.operation == "select"
        assert edge.access_pattern == "full_scan"

    def test_create_transforms_edge(self):
        """Test creating a TRANSFORMS edge (task modifies capsule in-place)."""
        task_id = uuid4()
        capsule_id = uuid4()

        edge = TaskDataEdge(
            task_urn="urn:dcs:task:airflow:prod:dag.update_task",
            capsule_urn="urn:dcs:postgres:table:staging.dim:customers",
            task_id=task_id,
            capsule_id=capsule_id,
            edge_type=OrchestrationEdgeType.TRANSFORMS,
            operation="update",
            transformation_type="scd_type_2",
        )

        assert edge.edge_type == OrchestrationEdgeType.TRANSFORMS
        assert edge.operation == "update"
        assert edge.transformation_type == "scd_type_2"

    def test_create_validates_edge(self):
        """Test creating a VALIDATES edge (task validates capsule quality)."""
        task_id = uuid4()
        capsule_id = uuid4()

        edge = TaskDataEdge(
            task_urn="urn:dcs:task:airflow:prod:dag.check_task",
            capsule_urn="urn:dcs:postgres:table:finance_erp.facts:gl_transactions",
            task_id=task_id,
            capsule_id=capsule_id,
            edge_type=OrchestrationEdgeType.VALIDATES,
            validation_type="double_entry_balance",
            meta={"validation_passed": True},
        )

        assert edge.edge_type == OrchestrationEdgeType.VALIDATES
        assert edge.validation_type == "double_entry_balance"
        assert edge.meta["validation_passed"] is True


class TestTaskDependencyEdge:
    """Tests for the TaskDependencyEdge model."""

    def test_create_task_dependency(self):
        """Test creating a task-to-task dependency."""
        source_task_id = uuid4()
        target_task_id = uuid4()
        ingestion_id = uuid4()

        edge = TaskDependencyEdge(
            source_task_urn="urn:dcs:task:airflow:prod:dag.task1",
            target_task_urn="urn:dcs:task:airflow:prod:dag.task2",
            source_task_id=source_task_id,
            target_task_id=target_task_id,
            edge_type="depends_on",
            meta={"trigger_rule": "all_success", "weight": 1},
            ingestion_id=ingestion_id,
        )

        assert edge.source_task_id == source_task_id
        assert edge.target_task_id == target_task_id
        assert edge.edge_type == "depends_on"
        assert edge.meta["trigger_rule"] == "all_success"


class TestPipelineTriggerEdge:
    """Tests for the PipelineTriggerEdge model."""

    def test_create_pipeline_trigger(self):
        """Test creating a pipeline-to-pipeline trigger."""
        source_pipeline_id = uuid4()
        target_pipeline_id = uuid4()
        ingestion_id = uuid4()

        edge = PipelineTriggerEdge(
            source_pipeline_urn="urn:dcs:pipeline:airflow:prod:finance_gl_pipeline",
            target_pipeline_urn="urn:dcs:pipeline:airflow:prod:cross_domain_analytics",
            source_pipeline_id=source_pipeline_id,
            target_pipeline_id=target_pipeline_id,
            edge_type="triggers",
            meta={
                "sensor_type": "ExternalTaskSensor",
                "external_task_id": "notify_finance_team",
            },
            ingestion_id=ingestion_id,
        )

        assert edge.source_pipeline_id == source_pipeline_id
        assert edge.target_pipeline_id == target_pipeline_id
        assert edge.edge_type == "triggers"
        assert edge.meta["sensor_type"] == "ExternalTaskSensor"
