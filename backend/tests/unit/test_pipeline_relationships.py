"""Integration tests for Pipeline orchestration model relationships."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.capsule import Capsule, CapsuleType
from src.models.pipeline import (
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
from src.models.domain import Domain
from src.models.source_system import SourceSystem


@pytest.mark.asyncio
class TestPipelineRelationships:
    """Test Pipeline orchestration model relationships."""

    async def test_complete_pipeline_workflow(self, test_session: AsyncSession):
        """Test complete pipeline workflow with all relationships."""
        # Create source system
        source_system = SourceSystem(
            name="airflow_test",
            source_type="airflow",
        )
        test_session.add(source_system)
        await test_session.flush()

        # Create pipeline
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:test:test_dag",
            name="test_dag",
            pipeline_type=PipelineType.AIRFLOW_DAG,
            source_system_id=source_system.id,
            source_system_identifier="test_dag",
        )
        test_session.add(pipeline)
        await test_session.flush()

        # Create tasks
        task1 = PipelineTask(
            urn="urn:dcs:task:airflow:test:test_dag.task1",
            name="task1",
            task_type=TaskType.PYTHON,
            pipeline_id=pipeline.id,
            pipeline_urn=pipeline.urn,
        )
        task2 = PipelineTask(
            urn="urn:dcs:task:airflow:test:test_dag.task2",
            name="task2",
            task_type=TaskType.SQL,
            pipeline_id=pipeline.id,
            pipeline_urn=pipeline.urn,
        )
        test_session.add(task1)
        test_session.add(task2)
        await test_session.flush()

        # Create task dependency (task2 depends on task1)
        task_dep = TaskDependencyEdge(
            source_task_urn=task1.urn,
            target_task_urn=task2.urn,
            source_task_id=task1.id,
            target_task_id=task2.id,
            edge_type="depends_on",
        )
        test_session.add(task_dep)

        # Create pipeline run
        now = datetime.now(timezone.utc)
        pipeline_run = PipelineRun(
            pipeline_id=pipeline.id,
            run_id="test_run_1",
            execution_date=now,
            start_time=now,
            status=RunStatus.SUCCESS,
        )
        test_session.add(pipeline_run)
        await test_session.flush()

        # Create task runs
        task_run1 = TaskRun(
            pipeline_run_id=pipeline_run.id,
            task_id=task1.id,
            task_run_id="task_run_1",
            start_time=now,
            status=RunStatus.SUCCESS,
        )
        task_run2 = TaskRun(
            pipeline_run_id=pipeline_run.id,
            task_id=task2.id,
            task_run_id="task_run_2",
            start_time=now,
            status=RunStatus.SUCCESS,
        )
        test_session.add(task_run1)
        test_session.add(task_run2)
        await test_session.commit()

        # Verify all relationships work
        # 1. Pipeline has tasks
        stmt = select(Pipeline).where(Pipeline.id == pipeline.id).options(selectinload(Pipeline.tasks))
        result = await test_session.execute(stmt)
        loaded_pipeline = result.scalar_one()
        assert len(loaded_pipeline.tasks) == 2

        # 2. Pipeline has runs
        stmt = select(Pipeline).where(Pipeline.id == pipeline.id).options(selectinload(Pipeline.runs))
        result = await test_session.execute(stmt)
        loaded_pipeline = result.scalar_one()
        assert len(loaded_pipeline.runs) == 1

        # 3. Pipeline linked to source system
        stmt = select(Pipeline).where(Pipeline.id == pipeline.id).options(selectinload(Pipeline.source_system))
        result = await test_session.execute(stmt)
        loaded_pipeline = result.scalar_one()
        assert loaded_pipeline.source_system.name == "airflow_test"

        # 4. Task dependency edge exists
        stmt = select(TaskDependencyEdge).where(TaskDependencyEdge.source_task_id == task1.id)
        result = await test_session.execute(stmt)
        dep_edge = result.scalar_one()
        assert dep_edge.target_task_id == task2.id

    async def test_task_data_edges(self, test_session: AsyncSession):
        """Test TaskDataEdge linking orchestration to data."""
        # Create domain and capsule
        domain = Domain(name="test_domain")
        test_session.add(domain)
        await test_session.flush()

        capsule = Capsule(
            urn="urn:dcs:postgres:table:test.fact:revenue",
            name="revenue",
            capsule_type=CapsuleType.MODEL,
            domain_id=domain.id,
        )
        test_session.add(capsule)
        await test_session.flush()

        # Create pipeline and task
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:test:etl_dag",
            name="etl_dag",
            pipeline_type=PipelineType.AIRFLOW_DAG,
            source_system_identifier="etl_dag",
        )
        test_session.add(pipeline)
        await test_session.flush()

        task = PipelineTask(
            urn="urn:dcs:task:airflow:test:etl_dag.load_revenue",
            name="load_revenue",
            task_type=TaskType.SQL,
            pipeline_id=pipeline.id,
            pipeline_urn=pipeline.urn,
        )
        test_session.add(task)
        await test_session.flush()

        # Create PRODUCES edge
        produces_edge = TaskDataEdge(
            task_urn=task.urn,
            capsule_urn=capsule.urn,
            task_id=task.id,
            capsule_id=capsule.id,
            edge_type=OrchestrationEdgeType.PRODUCES,
            operation="insert",
        )
        test_session.add(produces_edge)

        # Create CONSUMES edge (same task reading another capsule)
        capsule2 = Capsule(
            urn="urn:dcs:postgres:table:test.dim:customers",
            name="customers",
            capsule_type=CapsuleType.MODEL,
            domain_id=domain.id,
        )
        test_session.add(capsule2)
        await test_session.flush()

        consumes_edge = TaskDataEdge(
            task_urn=task.urn,
            capsule_urn=capsule2.urn,
            task_id=task.id,
            capsule_id=capsule2.id,
            edge_type=OrchestrationEdgeType.CONSUMES,
            operation="select",
        )
        test_session.add(consumes_edge)
        await test_session.commit()

        # Verify edges exist
        stmt = select(TaskDataEdge).where(TaskDataEdge.task_id == task.id)
        result = await test_session.execute(stmt)
        edges = result.scalars().all()
        assert len(edges) == 2
        assert any(e.edge_type == OrchestrationEdgeType.PRODUCES for e in edges)
        assert any(e.edge_type == OrchestrationEdgeType.CONSUMES for e in edges)

    async def test_pipeline_trigger_edge(self, test_session: AsyncSession):
        """Test PipelineTriggerEdge for cross-pipeline dependencies."""
        # Create two pipelines
        pipeline1 = Pipeline(
            urn="urn:dcs:pipeline:airflow:test:upstream",
            name="upstream",
            pipeline_type=PipelineType.AIRFLOW_DAG,
            source_system_identifier="upstream",
        )
        pipeline2 = Pipeline(
            urn="urn:dcs:pipeline:airflow:test:downstream",
            name="downstream",
            pipeline_type=PipelineType.AIRFLOW_DAG,
            source_system_identifier="downstream",
        )
        test_session.add(pipeline1)
        test_session.add(pipeline2)
        await test_session.flush()

        # Create trigger edge
        trigger_edge = PipelineTriggerEdge(
            source_pipeline_urn=pipeline1.urn,
            target_pipeline_urn=pipeline2.urn,
            source_pipeline_id=pipeline1.id,
            target_pipeline_id=pipeline2.id,
            edge_type="triggers",
            meta={"sensor_type": "ExternalTaskSensor"},
        )
        test_session.add(trigger_edge)
        await test_session.commit()

        # Verify edge exists
        stmt = select(PipelineTriggerEdge).where(PipelineTriggerEdge.source_pipeline_id == pipeline1.id)
        result = await test_session.execute(stmt)
        edge = result.scalar_one()
        assert edge.target_pipeline_id == pipeline2.id
        assert edge.meta["sensor_type"] == "ExternalTaskSensor"

    async def test_cascade_delete(self, test_session: AsyncSession):
        """Test that deleting a pipeline cascades to tasks and runs."""
        # Create pipeline with task
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:test:cascade_test",
            name="cascade_test",
            pipeline_type=PipelineType.AIRFLOW_DAG,
            source_system_identifier="cascade_test",
        )
        test_session.add(pipeline)
        await test_session.flush()

        task = PipelineTask(
            urn="urn:dcs:task:airflow:test:cascade_test.task1",
            name="task1",
            task_type=TaskType.PYTHON,
            pipeline_id=pipeline.id,
            pipeline_urn=pipeline.urn,
        )
        test_session.add(task)
        await test_session.flush()

        task_id = task.id

        # Delete pipeline
        await test_session.delete(pipeline)
        await test_session.commit()

        # Verify task was also deleted
        stmt = select(PipelineTask).where(PipelineTask.id == task_id)
        result = await test_session.execute(stmt)
        assert result.scalar_one_or_none() is None
