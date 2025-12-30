"""Unit tests for Pipeline repositories."""

import pytest
from sqlalchemy import select

from src.models.capsule import Capsule
from src.models.orchestration_edge import TaskDataEdge, TaskDependencyEdge
from src.models.pipeline import Pipeline, PipelineTask
from src.models.source_system import SourceSystem
from src.repositories.pipeline import PipelineRepository, TaskDataEdgeRepository


@pytest.mark.asyncio
class TestPipelineRepository:
    """Tests for PipelineRepository."""

    async def test_list_pipelines_no_filters(self, test_session):
        """Test listing all pipelines without filters."""
        # Create test source system
        source_system = SourceSystem(
            name="test-airflow",
            source_type="airflow",
            connection_info={},
        )
        test_session.add(source_system)
        await test_session.flush()

        # Create test pipelines
        pipelines = [
            Pipeline(
                urn="urn:dcs:pipeline:airflow:prod:pipeline_1",
                name="pipeline_1",
                pipeline_type="airflow_dag",
                source_system_id=source_system.id,
                source_system_identifier="pipeline_1",
                is_active=True,
            ),
            Pipeline(
                urn="urn:dcs:pipeline:airflow:prod:pipeline_2",
                name="pipeline_2",
                pipeline_type="airflow_dag",
                source_system_id=source_system.id,
                source_system_identifier="pipeline_2",
                is_active=True,
            ),
        ]
        for p in pipelines:
            test_session.add(p)
        await test_session.commit()

        repo = PipelineRepository(test_session)
        result, total = await repo.list_pipelines()

        assert total == 2
        assert len(result) == 2

    async def test_list_pipelines_filter_by_type(self, test_session):
        """Test filtering pipelines by type."""
        # Create test pipelines with different types
        pipelines = [
            Pipeline(
                urn="urn:dcs:pipeline:airflow:prod:dag1",
                name="dag1",
                pipeline_type="airflow_dag",
                source_system_identifier="dag1",
            ),
            Pipeline(
                urn="urn:dcs:pipeline:dbt:prod:dbt1",
                name="dbt1",
                pipeline_type="dbt_run",
                source_system_identifier="dbt1",
            ),
        ]
        for p in pipelines:
            test_session.add(p)
        await test_session.commit()

        repo = PipelineRepository(test_session)

        # Filter by airflow_dag
        result, total = await repo.list_pipelines(pipeline_type="airflow_dag")
        assert total == 1
        assert result[0].name == "dag1"

        # Filter by dbt_run
        result, total = await repo.list_pipelines(pipeline_type="dbt_run")
        assert total == 1
        assert result[0].name == "dbt1"

    async def test_list_pipelines_filter_by_active(self, test_session):
        """Test filtering pipelines by is_active flag."""
        pipelines = [
            Pipeline(
                urn="urn:dcs:pipeline:airflow:prod:active",
                name="active",
                pipeline_type="airflow_dag",
                source_system_identifier="active",
                is_active=True,
            ),
            Pipeline(
                urn="urn:dcs:pipeline:airflow:prod:inactive",
                name="inactive",
                pipeline_type="airflow_dag",
                source_system_identifier="inactive",
                is_active=False,
            ),
        ]
        for p in pipelines:
            test_session.add(p)
        await test_session.commit()

        repo = PipelineRepository(test_session)

        # Get only active
        result, total = await repo.list_pipelines(is_active=True)
        assert total == 1
        assert result[0].name == "active"

        # Get only inactive
        result, total = await repo.list_pipelines(is_active=False)
        assert total == 1
        assert result[0].name == "inactive"

    async def test_list_pipelines_search_query(self, test_session):
        """Test searching pipelines by name or description."""
        pipelines = [
            Pipeline(
                urn="urn:dcs:pipeline:airflow:prod:finance_pipeline",
                name="finance_pipeline",
                pipeline_type="airflow_dag",
                source_system_identifier="finance_pipeline",
                description="Financial data processing",
            ),
            Pipeline(
                urn="urn:dcs:pipeline:airflow:prod:customer_pipeline",
                name="customer_pipeline",
                pipeline_type="airflow_dag",
                source_system_identifier="customer_pipeline",
                description="Customer data management",
            ),
        ]
        for p in pipelines:
            test_session.add(p)
        await test_session.commit()

        repo = PipelineRepository(test_session)

        # Search by name
        result, total = await repo.list_pipelines(search_query="finance")
        assert total == 1
        assert result[0].name == "finance_pipeline"

        # Search by description
        result, total = await repo.list_pipelines(search_query="customer")
        assert total == 1
        assert result[0].name == "customer_pipeline"

    async def test_list_pipelines_pagination(self, test_session):
        """Test pagination in list_pipelines."""
        # Create 5 pipelines
        for i in range(5):
            pipeline = Pipeline(
                urn=f"urn:dcs:pipeline:airflow:prod:pipeline_{i}",
                name=f"pipeline_{i}",
                pipeline_type="airflow_dag",
                source_system_identifier=f"pipeline_{i}",
            )
            test_session.add(pipeline)
        await test_session.commit()

        repo = PipelineRepository(test_session)

        # Get first page (2 items)
        result, total = await repo.list_pipelines(offset=0, limit=2)
        assert total == 5
        assert len(result) == 2

        # Get second page (2 items)
        result, total = await repo.list_pipelines(offset=2, limit=2)
        assert total == 5
        assert len(result) == 2

    async def test_get_by_urn(self, test_session):
        """Test getting pipeline by URN."""
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:prod:test_pipeline",
            name="test_pipeline",
            pipeline_type="airflow_dag",
            source_system_identifier="test_pipeline",
        )
        test_session.add(pipeline)
        await test_session.commit()

        repo = PipelineRepository(test_session)

        # Existing pipeline
        result = await repo.get_by_urn("urn:dcs:pipeline:airflow:prod:test_pipeline")
        assert result is not None
        assert result.name == "test_pipeline"

        # Non-existing pipeline
        result = await repo.get_by_urn("urn:dcs:pipeline:airflow:prod:nonexistent")
        assert result is None

    async def test_get_tasks(self, test_session):
        """Test getting tasks for a pipeline."""
        # Create pipeline
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:prod:pipeline_with_tasks",
            name="pipeline_with_tasks",
            pipeline_type="airflow_dag",
            source_system_identifier="pipeline_with_tasks",
        )
        test_session.add(pipeline)
        await test_session.flush()

        # Create tasks
        tasks = [
            PipelineTask(
                urn="urn:dcs:task:airflow:prod:pipeline_with_tasks.task1",
                name="task1",
                task_type="python",
                pipeline_id=pipeline.id,
                pipeline_urn=pipeline.urn,
            ),
            PipelineTask(
                urn="urn:dcs:task:airflow:prod:pipeline_with_tasks.task2",
                name="task2",
                task_type="sql",
                pipeline_id=pipeline.id,
                pipeline_urn=pipeline.urn,
            ),
        ]
        for t in tasks:
            test_session.add(t)
        await test_session.commit()

        repo = PipelineRepository(test_session)
        result = await repo.get_tasks(pipeline.id)

        assert len(result) == 2
        task_names = {t.name for t in result}
        assert task_names == {"task1", "task2"}

    async def test_get_data_footprint(self, test_session):
        """Test getting data footprint for a pipeline."""
        # Create pipeline and tasks
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:prod:footprint_test",
            name="footprint_test",
            pipeline_type="airflow_dag",
            source_system_identifier="footprint_test",
        )
        test_session.add(pipeline)
        await test_session.flush()

        task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:footprint_test.etl_task",
            name="etl_task",
            task_type="python",
            pipeline_id=pipeline.id,
            pipeline_urn=pipeline.urn,
        )
        test_session.add(task)
        await test_session.flush()

        # Create capsules
        capsules = [
            Capsule(
                urn="urn:dcs:postgres:table:source.raw:transactions",
                name="transactions",
                capsule_type="model",
                schema_name="raw",
            ),
            Capsule(
                urn="urn:dcs:postgres:table:target.facts:processed_transactions",
                name="processed_transactions",
                capsule_type="model",
                schema_name="facts",
            ),
        ]
        for c in capsules:
            test_session.add(c)
        await test_session.flush()

        # Create task-data edges
        edges = [
            TaskDataEdge(
                task_urn=task.urn,
                capsule_urn=capsules[0].urn,
                task_id=task.id,
                capsule_id=capsules[0].id,
                edge_type="consumes",
                access_pattern="incremental",
            ),
            TaskDataEdge(
                task_urn=task.urn,
                capsule_urn=capsules[1].urn,
                task_id=task.id,
                capsule_id=capsules[1].id,
                edge_type="produces",
                operation="insert",
            ),
        ]
        for e in edges:
            test_session.add(e)
        await test_session.commit()

        repo = PipelineRepository(test_session)
        footprint = await repo.get_data_footprint(pipeline.id)

        assert len(footprint["consumes"]) == 1
        assert footprint["consumes"][0]["capsule_name"] == "transactions"
        assert footprint["consumes"][0]["access_pattern"] == "incremental"

        assert len(footprint["produces"]) == 1
        assert footprint["produces"][0]["capsule_name"] == "processed_transactions"
        assert footprint["produces"][0]["operation"] == "insert"

        assert len(footprint["transforms"]) == 0
        assert len(footprint["validates"]) == 0

    async def test_get_task_dependencies(self, test_session):
        """Test getting task dependency edges for a pipeline."""
        # Create pipeline and tasks
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:prod:dep_test",
            name="dep_test",
            pipeline_type="airflow_dag",
            source_system_identifier="dep_test",
        )
        test_session.add(pipeline)
        await test_session.flush()

        task1 = PipelineTask(
            urn="urn:dcs:task:airflow:prod:dep_test.task1",
            name="task1",
            task_type="python",
            pipeline_id=pipeline.id,
            pipeline_urn=pipeline.urn,
        )
        task2 = PipelineTask(
            urn="urn:dcs:task:airflow:prod:dep_test.task2",
            name="task2",
            task_type="python",
            pipeline_id=pipeline.id,
            pipeline_urn=pipeline.urn,
        )
        test_session.add_all([task1, task2])
        await test_session.flush()

        # Create task dependency edge
        edge = TaskDependencyEdge(
            source_task_urn=task1.urn,
            target_task_urn=task2.urn,
            source_task_id=task1.id,
            target_task_id=task2.id,
            edge_type="depends_on",
        )
        test_session.add(edge)
        await test_session.commit()

        repo = PipelineRepository(test_session)
        dependencies = await repo.get_task_dependencies(pipeline.id)

        assert len(dependencies) == 1
        assert dependencies[0].source_task_urn == task1.urn
        assert dependencies[0].target_task_urn == task2.urn

    async def test_count_by_type(self, test_session):
        """Test counting pipelines by type."""
        pipelines = [
            Pipeline(
                urn="urn:dcs:pipeline:airflow:prod:dag1",
                name="dag1",
                pipeline_type="airflow_dag",
                source_system_identifier="dag1",
            ),
            Pipeline(
                urn="urn:dcs:pipeline:airflow:prod:dag2",
                name="dag2",
                pipeline_type="airflow_dag",
                source_system_identifier="dag2",
            ),
            Pipeline(
                urn="urn:dcs:pipeline:dbt:prod:dbt1",
                name="dbt1",
                pipeline_type="dbt_run",
                source_system_identifier="dbt1",
            ),
        ]
        for p in pipelines:
            test_session.add(p)
        await test_session.commit()

        repo = PipelineRepository(test_session)
        counts = await repo.count_by_type()

        assert counts["airflow_dag"] == 2
        assert counts["dbt_run"] == 1

    async def test_count_by_source_system(self, test_session):
        """Test counting pipelines by source system."""
        # Create source systems
        systems = [
            SourceSystem(
                name="airflow-prod",
                source_type="airflow",
                connection_info={},
            ),
            SourceSystem(
                name="airflow-dev",
                source_type="airflow",
                connection_info={},
            ),
        ]
        for s in systems:
            test_session.add(s)
        await test_session.flush()

        # Create pipelines
        pipelines = [
            Pipeline(
                urn="urn:dcs:pipeline:airflow:prod:p1",
                name="p1",
                pipeline_type="airflow_dag",
                source_system_identifier="p1",
                source_system_id=systems[0].id,
            ),
            Pipeline(
                urn="urn:dcs:pipeline:airflow:prod:p2",
                name="p2",
                pipeline_type="airflow_dag",
                source_system_identifier="p2",
                source_system_id=systems[0].id,
            ),
            Pipeline(
                urn="urn:dcs:pipeline:airflow:dev:p3",
                name="p3",
                pipeline_type="airflow_dag",
                source_system_identifier="p3",
                source_system_id=systems[1].id,
            ),
        ]
        for p in pipelines:
            test_session.add(p)
        await test_session.commit()

        repo = PipelineRepository(test_session)
        counts = await repo.count_by_source_system()

        assert counts["airflow-prod"] == 2
        assert counts["airflow-dev"] == 1


@pytest.mark.asyncio
class TestTaskDataEdgeRepository:
    """Tests for TaskDataEdgeRepository."""

    async def test_get_producers(self, test_session):
        """Test getting tasks that produce a capsule."""
        # Create pipeline and task
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:prod:producer_test",
            name="producer_test",
            pipeline_type="airflow_dag",
            source_system_identifier="producer_test",
        )
        test_session.add(pipeline)
        await test_session.flush()

        task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:producer_test.producer_task",
            name="producer_task",
            task_type="sql",
            pipeline_id=pipeline.id,
            pipeline_urn=pipeline.urn,
        )
        test_session.add(task)
        await test_session.flush()

        # Create capsule
        capsule = Capsule(
            urn="urn:dcs:postgres:table:analytics.facts:revenue",
            name="revenue",
            capsule_type="model",
            schema_name="facts",
        )
        test_session.add(capsule)
        await test_session.flush()

        # Create PRODUCES edge
        edge = TaskDataEdge(
            task_urn=task.urn,
            capsule_urn=capsule.urn,
            task_id=task.id,
            capsule_id=capsule.id,
            edge_type="produces",
            operation="insert",
        )
        test_session.add(edge)
        await test_session.commit()

        repo = TaskDataEdgeRepository(test_session)
        producers = await repo.get_producers(capsule.urn)

        assert len(producers) == 1
        assert producers[0]["task_name"] == "producer_task"
        assert producers[0]["pipeline_name"] == "producer_test"
        assert producers[0]["operation"] == "insert"

    async def test_get_consumers(self, test_session):
        """Test getting tasks that consume a capsule."""
        # Create pipeline and task
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:prod:consumer_test",
            name="consumer_test",
            pipeline_type="airflow_dag",
            source_system_identifier="consumer_test",
        )
        test_session.add(pipeline)
        await test_session.flush()

        task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:consumer_test.consumer_task",
            name="consumer_task",
            task_type="python",
            pipeline_id=pipeline.id,
            pipeline_urn=pipeline.urn,
        )
        test_session.add(task)
        await test_session.flush()

        # Create capsule
        capsule = Capsule(
            urn="urn:dcs:postgres:table:raw.staging:orders",
            name="orders",
            capsule_type="model",
            schema_name="staging",
        )
        test_session.add(capsule)
        await test_session.flush()

        # Create CONSUMES edge
        edge = TaskDataEdge(
            task_urn=task.urn,
            capsule_urn=capsule.urn,
            task_id=task.id,
            capsule_id=capsule.id,
            edge_type="consumes",
            access_pattern="incremental",
        )
        test_session.add(edge)
        await test_session.commit()

        repo = TaskDataEdgeRepository(test_session)
        consumers = await repo.get_consumers(capsule.urn)

        assert len(consumers) == 1
        assert consumers[0]["task_name"] == "consumer_task"
        assert consumers[0]["pipeline_name"] == "consumer_test"
        assert consumers[0]["access_pattern"] == "incremental"

    async def test_get_by_task(self, test_session):
        """Test getting all edges for a specific task."""
        # Create pipeline and task
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:prod:task_edge_test",
            name="task_edge_test",
            pipeline_type="airflow_dag",
            source_system_identifier="task_edge_test",
        )
        test_session.add(pipeline)
        await test_session.flush()

        task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:task_edge_test.etl_task",
            name="etl_task",
            task_type="python",
            pipeline_id=pipeline.id,
            pipeline_urn=pipeline.urn,
        )
        test_session.add(task)
        await test_session.flush()

        # Create capsules
        capsules = [
            Capsule(
                urn="urn:dcs:postgres:table:raw:source1",
                name="source1",
                capsule_type="model",
                schema_name="raw",
            ),
            Capsule(
                urn="urn:dcs:postgres:table:analytics:target1",
                name="target1",
                capsule_type="model",
                schema_name="analytics",
            ),
        ]
        for c in capsules:
            test_session.add(c)
        await test_session.flush()

        # Create edges
        edges = [
            TaskDataEdge(
                task_urn=task.urn,
                capsule_urn=capsules[0].urn,
                task_id=task.id,
                capsule_id=capsules[0].id,
                edge_type="consumes",
            ),
            TaskDataEdge(
                task_urn=task.urn,
                capsule_urn=capsules[1].urn,
                task_id=task.id,
                capsule_id=capsules[1].id,
                edge_type="produces",
            ),
        ]
        for e in edges:
            test_session.add(e)
        await test_session.commit()

        repo = TaskDataEdgeRepository(test_session)
        task_edges = await repo.get_by_task(task.urn)

        assert len(task_edges) == 2
        edge_types = {e.edge_type for e in task_edges}
        assert edge_types == {"consumes", "produces"}

    async def test_get_by_pipeline(self, test_session):
        """Test getting all edges for tasks in a pipeline."""
        # Create pipeline and tasks
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:prod:pipeline_edge_test",
            name="pipeline_edge_test",
            pipeline_type="airflow_dag",
            source_system_identifier="pipeline_edge_test",
        )
        test_session.add(pipeline)
        await test_session.flush()

        tasks = [
            PipelineTask(
                urn="urn:dcs:task:airflow:prod:pipeline_edge_test.task1",
                name="task1",
                task_type="python",
                pipeline_id=pipeline.id,
                pipeline_urn=pipeline.urn,
            ),
            PipelineTask(
                urn="urn:dcs:task:airflow:prod:pipeline_edge_test.task2",
                name="task2",
                task_type="sql",
                pipeline_id=pipeline.id,
                pipeline_urn=pipeline.urn,
            ),
        ]
        for t in tasks:
            test_session.add(t)
        await test_session.flush()

        # Create capsule
        capsule = Capsule(
            urn="urn:dcs:postgres:table:analytics:shared_table",
            name="shared_table",
            capsule_type="model",
            schema_name="analytics",
        )
        test_session.add(capsule)
        await test_session.flush()

        # Create edges for both tasks
        edges = [
            TaskDataEdge(
                task_urn=tasks[0].urn,
                capsule_urn=capsule.urn,
                task_id=tasks[0].id,
                capsule_id=capsule.id,
                edge_type="produces",
            ),
            TaskDataEdge(
                task_urn=tasks[1].urn,
                capsule_urn=capsule.urn,
                task_id=tasks[1].id,
                capsule_id=capsule.id,
                edge_type="consumes",
            ),
        ]
        for e in edges:
            test_session.add(e)
        await test_session.commit()

        repo = TaskDataEdgeRepository(test_session)
        pipeline_edges = await repo.get_by_pipeline(pipeline.urn)

        assert len(pipeline_edges) == 2
        task_urns = {e.task_urn for e in pipeline_edges}
        assert task_urns == {tasks[0].urn, tasks[1].urn}

    async def test_count_by_edge_type(self, test_session):
        """Test counting task-data edges by edge type."""
        # Create pipeline and task
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:prod:count_test",
            name="count_test",
            pipeline_type="airflow_dag",
            source_system_identifier="count_test",
        )
        test_session.add(pipeline)
        await test_session.flush()

        task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:count_test.task",
            name="task",
            task_type="python",
            pipeline_id=pipeline.id,
            pipeline_urn=pipeline.urn,
        )
        test_session.add(task)
        await test_session.flush()

        # Create capsules
        capsules = []
        for i in range(5):
            capsule = Capsule(
                urn=f"urn:dcs:postgres:table:test:table_{i}",
                name=f"table_{i}",
                capsule_type="model",
                schema_name="test",
            )
            capsules.append(capsule)
            test_session.add(capsule)
        await test_session.flush()

        # Create edges: 2 produces, 2 consumes, 1 validates
        edge_configs = [
            ("produces", 0),
            ("produces", 1),
            ("consumes", 2),
            ("consumes", 3),
            ("validates", 4),
        ]

        for edge_type, capsule_idx in edge_configs:
            edge = TaskDataEdge(
                task_urn=task.urn,
                capsule_urn=capsules[capsule_idx].urn,
                task_id=task.id,
                capsule_id=capsules[capsule_idx].id,
                edge_type=edge_type,
            )
            test_session.add(edge)
        await test_session.commit()

        repo = TaskDataEdgeRepository(test_session)
        counts = await repo.count_by_edge_type()

        assert counts["produces"] == 2
        assert counts["consumes"] == 2
        assert counts["validates"] == 1
