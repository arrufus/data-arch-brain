"""Integration tests for Airflow Phase 3 data flow mapping."""

import json
from pathlib import Path

import pytest
import yaml
from sqlalchemy import select

from src.models.capsule import Capsule
from src.models.orchestration_edge import TaskDataEdge
from src.models.pipeline import Pipeline, PipelineTask
from src.models.source_system import SourceSystem
from src.parsers.airflow_parser import AirflowParser
from src.parsers.base import ParseResult, RawCapsule, RawOrchestrationEdge, RawPipeline, RawPipelineTask
from src.services.ingestion import IngestionService


@pytest.fixture
async def source_system(test_session):
    """Create a source system for testing."""
    source = SourceSystem(
        name="test",
        source_type="airflow",
        connection_info={},
    )
    test_session.add(source)
    await test_session.commit()
    return source


@pytest.fixture
async def data_capsules(test_session):
    """Create test data capsules."""
    capsules = [
        Capsule(
            urn="urn:dcs:postgres:table:erp.dim:chart_of_accounts",
            name="chart_of_accounts",
            schema_name="dim",
            database_name="erp",
            capsule_type="model",
        ),
        Capsule(
            urn="urn:dcs:postgres:table:erp.staging:raw_transactions",
            name="raw_transactions",
            schema_name="staging",
            database_name="erp",
            capsule_type="model",
        ),
        Capsule(
            urn="urn:dcs:postgres:table:erp.facts:gl_transactions",
            name="gl_transactions",
            schema_name="facts",
            database_name="erp",
            capsule_type="model",
        ),
    ]

    for capsule in capsules:
        test_session.add(capsule)
    await test_session.commit()

    return capsules


@pytest.fixture
def annotation_file(tmp_path):
    """Create a manual annotation file."""
    annotation_data = {
        "pipelines": [
            {
                "pipeline_id": "finance_gl_pipeline",
                "instance": "prod",
                "tasks": [
                    {
                        "task_id": "validate_chart_of_accounts",
                        "consumes": [
                            "urn:dcs:postgres:table:erp.dim:chart_of_accounts"
                        ],
                        "validates": [
                            "urn:dcs:postgres:table:erp.dim:chart_of_accounts"
                        ],
                    },
                    {
                        "task_id": "load_gl_transactions",
                        "consumes": [
                            "urn:dcs:postgres:table:erp.dim:chart_of_accounts",
                            {
                                "urn": "urn:dcs:postgres:table:erp.staging:raw_transactions",
                                "access_pattern": "incremental",
                            },
                        ],
                        "produces": [
                            {
                                "urn": "urn:dcs:postgres:table:erp.facts:gl_transactions",
                                "operation": "insert",
                            }
                        ],
                    },
                ],
            }
        ]
    }

    annotation_path = tmp_path / "annotations.yaml"
    with open(annotation_path, "w") as f:
        yaml.dump(annotation_data, f)

    return str(annotation_path)


@pytest.mark.asyncio
class TestAirflowDataFlowIntegration:
    """Integration tests for Airflow data flow mapping."""

    async def test_manual_annotation_data_flow(
        self, test_session, source_system, data_capsules, annotation_file
    ):
        """Test data flow extraction from manual annotations."""
        # Create a parse result with orchestration metadata and data flow edges
        parse_result = ParseResult(source_type="airflow")
        parse_result.source_name = "prod"

        # Create pipeline
        pipeline = RawPipeline(
            urn="urn:dcs:pipeline:airflow:prod:finance_gl_pipeline",
            name="finance_gl_pipeline",
            pipeline_type="airflow_dag",
            source_system_identifier="finance_gl_pipeline",
            is_active=True,
        )
        parse_result.pipelines.append(pipeline)

        # Create tasks
        task1 = RawPipelineTask(
            urn="urn:dcs:task:airflow:prod:finance_gl_pipeline.validate_chart_of_accounts",
            name="validate_chart_of_accounts",
            task_type="python",
            pipeline_urn=pipeline.urn,
            operator="PythonOperator",
        )
        task2 = RawPipelineTask(
            urn="urn:dcs:task:airflow:prod:finance_gl_pipeline.load_gl_transactions",
            name="load_gl_transactions",
            task_type="python",
            pipeline_urn=pipeline.urn,
            operator="PythonOperator",
        )
        parse_result.pipeline_tasks.extend([task1, task2])

        # Create CONTAINS edges
        parse_result.orchestration_edges.append(
            RawOrchestrationEdge(
                source_urn=pipeline.urn,
                target_urn=task1.urn,
                edge_category="task_dependency",
                edge_type="contains",
            )
        )
        parse_result.orchestration_edges.append(
            RawOrchestrationEdge(
                source_urn=pipeline.urn,
                target_urn=task2.urn,
                edge_category="task_dependency",
                edge_type="contains",
            )
        )

        # Create data flow edges from annotations
        # Task 1: CONSUMES + VALIDATES chart_of_accounts
        parse_result.orchestration_edges.append(
            RawOrchestrationEdge(
                source_urn="urn:dcs:postgres:table:erp.dim:chart_of_accounts",
                target_urn=task1.urn,
                edge_category="task_data",
                edge_type="consumes",
                meta={"source": "manual_annotation"},
            )
        )
        parse_result.orchestration_edges.append(
            RawOrchestrationEdge(
                source_urn=task1.urn,
                target_urn="urn:dcs:postgres:table:erp.dim:chart_of_accounts",
                edge_category="task_data",
                edge_type="validates",
                meta={"source": "manual_annotation"},
            )
        )

        # Task 2: CONSUMES 2 tables, PRODUCES 1 table
        parse_result.orchestration_edges.append(
            RawOrchestrationEdge(
                source_urn="urn:dcs:postgres:table:erp.dim:chart_of_accounts",
                target_urn=task2.urn,
                edge_category="task_data",
                edge_type="consumes",
                meta={"source": "manual_annotation"},
            )
        )
        parse_result.orchestration_edges.append(
            RawOrchestrationEdge(
                source_urn="urn:dcs:postgres:table:erp.staging:raw_transactions",
                target_urn=task2.urn,
                edge_category="task_data",
                edge_type="consumes",
                access_pattern="incremental",
                meta={"source": "manual_annotation"},
            )
        )
        parse_result.orchestration_edges.append(
            RawOrchestrationEdge(
                source_urn=task2.urn,
                target_urn="urn:dcs:postgres:table:erp.facts:gl_transactions",
                edge_category="task_data",
                edge_type="produces",
                operation="insert",
                meta={"source": "manual_annotation"},
            )
        )

        # Ingest the parse result
        ingestion_service = IngestionService(test_session)
        job, stats = await ingestion_service._persist_parse_result(
            parse_result=parse_result,
            source_system=source_system,
            cleanup_orphans=False,
        )

        await test_session.commit()

        # Verify statistics
        assert stats.pipelines_created == 1
        assert stats.pipeline_tasks_created == 2
        assert stats.orchestration_edges_created == 7  # 2 CONTAINS + 5 data flow edges

        # Verify TaskDataEdge creation
        result = await test_session.execute(select(TaskDataEdge))
        task_data_edges = result.scalars().all()

        assert len(task_data_edges) == 5

        # Verify edge types
        edge_types = {edge.edge_type for edge in task_data_edges}
        assert edge_types == {"consumes", "produces", "validates"}

        # Verify CONSUMES edges
        consumes_edges = [e for e in task_data_edges if e.edge_type == "consumes"]
        assert len(consumes_edges) == 3

        # Verify PRODUCES edges
        produces_edges = [e for e in task_data_edges if e.edge_type == "produces"]
        assert len(produces_edges) == 1
        assert produces_edges[0].operation == "insert"

        # Verify VALIDATES edges
        validates_edges = [e for e in task_data_edges if e.edge_type == "validates"]
        assert len(validates_edges) == 1

        # Verify access_pattern metadata
        incremental_edge = [
            e for e in consumes_edges
            if e.capsule_urn == "urn:dcs:postgres:table:erp.staging:raw_transactions"
        ]
        assert len(incremental_edge) == 1
        assert incremental_edge[0].access_pattern == "incremental"

    async def test_query_capsule_producers(self, test_session, source_system, data_capsules):
        """Test querying which tasks produce a capsule."""
        # Create pipeline and task
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:prod:test_pipeline",
            name="test_pipeline",
            pipeline_type="airflow_dag",
            source_system_id=source_system.id,
        )
        test_session.add(pipeline)
        await test_session.flush()

        task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:test_pipeline.producer_task",
            name="producer_task",
            task_type="python",
            pipeline_id=pipeline.id,
        )
        test_session.add(task)
        await test_session.flush()

        # Create PRODUCES edge
        capsule = data_capsules[2]  # gl_transactions
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

        # Query which tasks produce this capsule
        result = await test_session.execute(
            select(TaskDataEdge)
            .where(TaskDataEdge.capsule_urn == capsule.urn)
            .where(TaskDataEdge.edge_type == "produces")
        )
        producers = result.scalars().all()

        assert len(producers) == 1
        assert producers[0].task_urn == task.urn
        assert producers[0].operation == "insert"

    async def test_query_task_consumers(self, test_session, source_system, data_capsules):
        """Test querying which tasks consume a capsule."""
        # Create pipeline and tasks
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:prod:test_pipeline",
            name="test_pipeline",
            pipeline_type="airflow_dag",
            source_system_id=source_system.id,
        )
        test_session.add(pipeline)
        await test_session.flush()

        task1 = PipelineTask(
            urn="urn:dcs:task:airflow:prod:test_pipeline.consumer1",
            name="consumer1",
            task_type="python",
            pipeline_id=pipeline.id,
        )
        task2 = PipelineTask(
            urn="urn:dcs:task:airflow:prod:test_pipeline.consumer2",
            name="consumer2",
            task_type="sql",
            pipeline_id=pipeline.id,
        )
        test_session.add_all([task1, task2])
        await test_session.flush()

        # Both tasks consume the same capsule
        capsule = data_capsules[0]  # chart_of_accounts
        for task in [task1, task2]:
            edge = TaskDataEdge(
                task_urn=task.urn,
                capsule_urn=capsule.urn,
                task_id=task.id,
                capsule_id=capsule.id,
                edge_type="consumes",
            )
            test_session.add(edge)
        await test_session.commit()

        # Query which tasks consume this capsule
        result = await test_session.execute(
            select(TaskDataEdge)
            .where(TaskDataEdge.capsule_urn == capsule.urn)
            .where(TaskDataEdge.edge_type == "consumes")
        )
        consumers = result.scalars().all()

        assert len(consumers) == 2
        consumer_urns = {c.task_urn for c in consumers}
        assert task1.urn in consumer_urns
        assert task2.urn in consumer_urns

    async def test_data_lineage_via_tasks(self, test_session, source_system, data_capsules):
        """Test tracing data lineage through pipeline tasks."""
        # Create pipeline
        pipeline = Pipeline(
            urn="urn:dcs:pipeline:airflow:prod:lineage_pipeline",
            name="lineage_pipeline",
            pipeline_type="airflow_dag",
            source_system_id=source_system.id,
        )
        test_session.add(pipeline)
        await test_session.flush()

        # Create task that reads from capsule1 and writes to capsule2
        task = PipelineTask(
            urn="urn:dcs:task:airflow:prod:lineage_pipeline.transformer",
            name="transformer",
            task_type="sql",
            pipeline_id=pipeline.id,
        )
        test_session.add(task)
        await test_session.flush()

        # CONSUMES raw_transactions
        consumes_edge = TaskDataEdge(
            task_urn=task.urn,
            capsule_urn=data_capsules[1].urn,  # raw_transactions
            task_id=task.id,
            capsule_id=data_capsules[1].id,
            edge_type="consumes",
        )

        # PRODUCES gl_transactions
        produces_edge = TaskDataEdge(
            task_urn=task.urn,
            capsule_urn=data_capsules[2].urn,  # gl_transactions
            task_id=task.id,
            capsule_id=data_capsules[2].id,
            edge_type="produces",
            operation="insert",
        )

        test_session.add_all([consumes_edge, produces_edge])
        await test_session.commit()

        # Trace lineage: Find what produces gl_transactions
        result = await test_session.execute(
            select(TaskDataEdge)
            .where(TaskDataEdge.capsule_urn == data_capsules[2].urn)
            .where(TaskDataEdge.edge_type == "produces")
        )
        producer_edges = result.scalars().all()
        assert len(producer_edges) == 1

        producing_task_urn = producer_edges[0].task_urn

        # Find what that task consumes
        result = await test_session.execute(
            select(TaskDataEdge)
            .where(TaskDataEdge.task_urn == producing_task_urn)
            .where(TaskDataEdge.edge_type == "consumes")
        )
        consumed_edges = result.scalars().all()
        assert len(consumed_edges) == 1
        assert consumed_edges[0].capsule_urn == data_capsules[1].urn

        # We've traced: raw_transactions -> [task] -> gl_transactions
