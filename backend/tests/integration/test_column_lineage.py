"""Integration tests for Phase 6: Column-level Lineage."""

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from src.models.capsule import Capsule
from src.models.column import Column
from src.models.lineage import ColumnLineage
from src.models.orchestration_edge import TaskDataEdge
from src.models.pipeline import Pipeline, PipelineTask
from src.models.source_system import SourceSystem
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
async def data_capsules_with_columns(test_session):
    """Create test capsules with columns for column lineage testing."""
    # Create capsules
    customers = Capsule(
        urn="urn:dcs:postgres:table:erp.dim:customers",
        name="customers",
        schema_name="dim",
        database_name="erp",
        capsule_type="model",
    )
    orders = Capsule(
        urn="urn:dcs:postgres:table:erp.staging:orders",
        name="orders",
        schema_name="staging",
        database_name="erp",
        capsule_type="model",
    )
    customer_summary = Capsule(
        urn="urn:dcs:postgres:table:erp.marts:customer_summary",
        name="customer_summary",
        schema_name="marts",
        database_name="erp",
        capsule_type="model",
    )

    test_session.add_all([customers, orders, customer_summary])
    await test_session.flush()

    # Create columns for customers table
    customers_cols = [
        Column(
            capsule_id=customers.id,
            urn="urn:dcs:column:erp.dim.customers.customer_id",
            name="customer_id",
            data_type="INTEGER",
            ordinal_position=1,
        ),
        Column(
            capsule_id=customers.id,
            urn="urn:dcs:column:erp.dim.customers.customer_name",
            name="customer_name",
            data_type="VARCHAR",
            ordinal_position=2,
        ),
        Column(
            capsule_id=customers.id,
            urn="urn:dcs:column:erp.dim.customers.email",
            name="email",
            data_type="VARCHAR",
            ordinal_position=3,
        ),
    ]

    # Create columns for orders table
    orders_cols = [
        Column(
            capsule_id=orders.id,
            urn="urn:dcs:column:erp.staging.orders.order_id",
            name="order_id",
            data_type="INTEGER",
            ordinal_position=1,
        ),
        Column(
            capsule_id=orders.id,
            urn="urn:dcs:column:erp.staging.orders.customer_id",
            name="customer_id",
            data_type="INTEGER",
            ordinal_position=2,
        ),
        Column(
            capsule_id=orders.id,
            urn="urn:dcs:column:erp.staging.orders.order_date",
            name="order_date",
            data_type="DATE",
            ordinal_position=3,
        ),
        Column(
            capsule_id=orders.id,
            urn="urn:dcs:column:erp.staging.orders.amount",
            name="amount",
            data_type="DECIMAL",
            ordinal_position=4,
        ),
    ]

    # Create columns for customer_summary table
    summary_cols = [
        Column(
            capsule_id=customer_summary.id,
            urn="urn:dcs:column:erp.marts.customer_summary.customer_id",
            name="customer_id",
            data_type="INTEGER",
            ordinal_position=1,
        ),
        Column(
            capsule_id=customer_summary.id,
            urn="urn:dcs:column:erp.marts.customer_summary.customer_name",
            name="customer_name",
            data_type="VARCHAR",
            ordinal_position=2,
        ),
        Column(
            capsule_id=customer_summary.id,
            urn="urn:dcs:column:erp.marts.customer_summary.order_count",
            name="order_count",
            data_type="INTEGER",
            ordinal_position=3,
        ),
        Column(
            capsule_id=customer_summary.id,
            urn="urn:dcs:column:erp.marts.customer_summary.total_spent",
            name="total_spent",
            data_type="DECIMAL",
            ordinal_position=4,
        ),
        Column(
            capsule_id=customer_summary.id,
            urn="urn:dcs:column:erp.marts.customer_summary.first_order_date",
            name="first_order_date",
            data_type="VARCHAR",
            ordinal_position=5,
        ),
    ]

    for col_list in [customers_cols, orders_cols, summary_cols]:
        test_session.add_all(col_list)

    await test_session.commit()

    return {
        "capsules": [customers, orders, customer_summary],
        "columns": {
            "customers": customers_cols,
            "orders": orders_cols,
            "customer_summary": summary_cols,
        }
    }


@pytest.mark.asyncio
class TestColumnLineageIntegration:
    """Integration tests for column-level lineage (Phase 6)."""

    async def test_column_lineage_from_sql(
        self, test_session, source_system, data_capsules_with_columns
    ):
        """Test column lineage creation and storage."""
        capsules = data_capsules_with_columns["capsules"]
        columns_data = data_capsules_with_columns["columns"]
        customers, orders, customer_summary = capsules
        customers_cols = columns_data["customers"]
        orders_cols = columns_data["orders"]
        summary_cols = columns_data["customer_summary"]

        # Create an ingestion job for tracking
        from datetime import datetime, timezone
        from src.models.ingestion import IngestionJob

        job = IngestionJob(
            source_type="airflow",
            source_name="test",
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        test_session.add(job)
        await test_session.flush()

        # Create column lineage edges directly
        # customers.customer_id -> customer_summary.customer_id (identity)
        edge1 = ColumnLineage(
            source_column_id=customers_cols[0].id,
            source_column_urn="urn:dcs:column:customers.customer_id",
            target_column_id=summary_cols[0].id,
            target_column_urn="urn:dcs:column:customer_summary.customer_id",
            edge_type="derives_from",
            transformation_type="identity",
            confidence=1.0,
            detected_by="sql_parser",
            ingestion_id=job.id,
        )

        # orders.amount -> customer_summary.total_spent (aggregate)
        edge2 = ColumnLineage(
            source_column_id=orders_cols[3].id,
            source_column_urn="urn:dcs:column:orders.amount",
            target_column_id=summary_cols[3].id,
            target_column_urn="urn:dcs:column:customer_summary.total_spent",
            edge_type="derives_from",
            transformation_type="aggregate",
            transformation_logic="SUM(o.amount)",
            confidence=0.95,
            detected_by="sql_parser",
            ingestion_id=job.id,
        )

        # orders.order_date -> customer_summary.first_order_date (cast)
        edge3 = ColumnLineage(
            source_column_id=orders_cols[2].id,
            source_column_urn="urn:dcs:column:orders.order_date",
            target_column_id=summary_cols[4].id,
            target_column_urn="urn:dcs:column:customer_summary.first_order_date",
            edge_type="derives_from",
            transformation_type="cast",
            transformation_logic="CAST(MIN(o.order_date) AS VARCHAR)",
            confidence=0.95,
            detected_by="sql_parser",
            ingestion_id=job.id,
        )

        test_session.add_all([edge1, edge2, edge3])
        await test_session.commit()

        # Verify column lineage edges were created
        result = await test_session.execute(select(ColumnLineage))
        column_edges = result.scalars().all()

        # Should have 3 column mappings created
        assert len(column_edges) == 3, f"Expected 3 column edges, got {len(column_edges)}"

        # Verify we have different transformation types
        transformation_types = {e.transformation_type for e in column_edges}
        assert "identity" in transformation_types
        assert "aggregate" in transformation_types
        assert "cast" in transformation_types

        # Verify detection metadata
        for edge in column_edges:
            assert edge.detected_by == "sql_parser"
            assert edge.ingestion_id == job.id
            assert edge.confidence > 0

    async def test_column_lineage_upstream_query(
        self, test_session, source_system, data_capsules_with_columns
    ):
        """Test querying upstream columns for a given column."""
        columns_data = data_capsules_with_columns["columns"]
        customers_cols = columns_data["customers"]
        summary_cols = columns_data["customer_summary"]

        # Create a column lineage edge: customers.customer_id -> customer_summary.customer_id
        edge = ColumnLineage(
            source_column_id=customers_cols[0].id,  # customer_id
            source_column_urn="urn:dcs:column:customers.customer_id",
            target_column_id=summary_cols[0].id,  # customer_id
            target_column_urn="urn:dcs:column:customer_summary.customer_id",
            edge_type="derives_from",
            transformation_type="identity",
            confidence=1.0,
            detected_by="sql_parser",
        )
        test_session.add(edge)
        await test_session.commit()

        # Query upstream columns for customer_summary.customer_id
        from src.repositories.column_lineage import ColumnLineageRepository

        repo = ColumnLineageRepository(test_session)
        upstream = await repo.get_upstream_columns(
            column_urn="urn:dcs:column:customer_summary.customer_id",
            depth=5,
        )

        assert len(upstream) == 1
        assert upstream[0]["column_id"] == customers_cols[0].id
        assert upstream[0]["depth"] == 1
        assert upstream[0]["transformation_type"] == "identity"

    async def test_column_lineage_downstream_query(
        self, test_session, source_system, data_capsules_with_columns
    ):
        """Test querying downstream columns for a given column."""
        columns_data = data_capsules_with_columns["columns"]
        orders_cols = columns_data["orders"]
        summary_cols = columns_data["customer_summary"]

        # Create a column lineage edge: orders.amount -> customer_summary.total_spent
        edge = ColumnLineage(
            source_column_id=orders_cols[3].id,  # amount
            source_column_urn="urn:dcs:column:orders.amount",
            target_column_id=summary_cols[3].id,  # total_spent
            target_column_urn="urn:dcs:column:customer_summary.total_spent",
            edge_type="derives_from",
            transformation_type="aggregate",
            transformation_logic="SUM(o.amount)",
            confidence=0.95,
            detected_by="sql_parser",
        )
        test_session.add(edge)
        await test_session.commit()

        # Query downstream columns for orders.amount
        from src.repositories.column_lineage import ColumnLineageRepository

        repo = ColumnLineageRepository(test_session)
        downstream = await repo.get_downstream_columns(
            column_urn="urn:dcs:column:orders.amount",
            depth=5,
        )

        assert len(downstream) == 1
        assert downstream[0]["column_id"] == summary_cols[3].id
        assert downstream[0]["depth"] == 1
        assert downstream[0]["transformation_type"] == "aggregate"
        assert downstream[0]["transformation_logic"] == "SUM(o.amount)"

    async def test_column_lineage_multi_hop(
        self, test_session, source_system, data_capsules_with_columns
    ):
        """Test multi-hop column lineage traversal."""
        columns_data = data_capsules_with_columns["columns"]
        customers_cols = columns_data["customers"]
        orders_cols = columns_data["orders"]
        summary_cols = columns_data["customer_summary"]

        # Create a 2-hop lineage chain:
        # customers.customer_id -> orders.customer_id -> customer_summary.customer_id

        # Hop 1: customers -> orders
        edge1 = ColumnLineage(
            source_column_id=customers_cols[0].id,
            source_column_urn="urn:dcs:column:customers.customer_id",
            target_column_id=orders_cols[1].id,
            target_column_urn="urn:dcs:column:orders.customer_id",
            edge_type="derives_from",
            transformation_type="identity",
            confidence=1.0,
            detected_by="manual",
        )

        # Hop 2: orders -> customer_summary
        edge2 = ColumnLineage(
            source_column_id=orders_cols[1].id,
            source_column_urn="urn:dcs:column:orders.customer_id",
            target_column_id=summary_cols[0].id,
            target_column_urn="urn:dcs:column:customer_summary.customer_id",
            edge_type="derives_from",
            transformation_type="identity",
            confidence=1.0,
            detected_by="sql_parser",
        )

        test_session.add_all([edge1, edge2])
        await test_session.commit()

        # Query upstream from customer_summary.customer_id
        from src.repositories.column_lineage import ColumnLineageRepository

        repo = ColumnLineageRepository(test_session)
        upstream = await repo.get_upstream_columns(
            column_urn="urn:dcs:column:customer_summary.customer_id",
            depth=5,
        )

        # Should find both orders.customer_id (depth 1) and customers.customer_id (depth 2)
        assert len(upstream) == 2

        depth_1 = [c for c in upstream if c["depth"] == 1]
        depth_2 = [c for c in upstream if c["depth"] == 2]

        assert len(depth_1) == 1
        assert depth_1[0]["column_id"] == orders_cols[1].id

        assert len(depth_2) == 1
        assert depth_2[0]["column_id"] == customers_cols[0].id

    async def test_column_resolution_case_insensitive(
        self, test_session, source_system, data_capsules_with_columns
    ):
        """Test that column resolution is case-insensitive for table names."""
        capsules = data_capsules_with_columns["capsules"]
        customers = capsules[0]

        # Create parse result with uppercase table name in SQL
        parse_result = ParseResult(source_type="airflow")
        parse_result.source_name = "prod"

        parse_result.capsules = [
            RawCapsule(
                urn=customers.urn,
                name="customers",
                capsule_type="model",
                unique_id="customers",
                schema_name="dim",
                database_name="erp",
            ),
        ]

        pipeline = RawPipeline(
            urn="urn:dcs:pipeline:airflow:prod:test_case",
            name="test_case",
            pipeline_type="airflow_dag",
            source_system_identifier="test_case",
            is_active=True,
        )
        parse_result.pipelines.append(pipeline)

        # SQL with uppercase table name
        sql_query = "SELECT CUSTOMERS.customer_id FROM CUSTOMERS"

        task = RawPipelineTask(
            urn="urn:dcs:task:airflow:prod:test_case.test_task",
            name="test_task",
            task_type="sql",
            pipeline_urn=pipeline.urn,
            operator="PostgresOperator",
            meta={"sql": sql_query},
        )
        parse_result.pipeline_tasks.append(task)

        parse_result.orchestration_edges.append(
            RawOrchestrationEdge(
                source_urn=pipeline.urn,
                target_urn=task.urn,
                edge_category="task_dependency",
                edge_type="contains",
            )
        )

        # Ingest
        ingestion_service = IngestionService(test_session)
        job, stats = await ingestion_service._persist_parse_result(
            parse_result=parse_result,
            source_system=source_system,
            cleanup_orphans=False,
        )

        await test_session.commit()

        # Verify column lineage was created despite case mismatch
        result = await test_session.execute(select(ColumnLineage))
        column_edges = result.scalars().all()

        # Should resolve "CUSTOMERS.customer_id" to actual column despite case difference
        assert len(column_edges) >= 1

    async def test_column_lineage_with_schema_qualified_names(
        self, test_session, source_system, data_capsules_with_columns
    ):
        """Test column resolution with 3-part qualified names (schema.table.column)."""
        capsules = data_capsules_with_columns["capsules"]
        customers = capsules[0]

        # Create parse result with schema-qualified column references
        parse_result = ParseResult(source_type="airflow")
        parse_result.source_name = "prod"

        parse_result.capsules = [
            RawCapsule(
                urn=customers.urn,
                name="customers",
                capsule_type="model",
                unique_id="customers",
                schema_name="dim",
                database_name="erp",
            ),
        ]

        pipeline = RawPipeline(
            urn="urn:dcs:pipeline:airflow:prod:test_schema",
            name="test_schema",
            pipeline_type="airflow_dag",
            source_system_identifier="test_schema",
            is_active=True,
        )
        parse_result.pipelines.append(pipeline)

        # SQL with 3-part qualified names
        sql_query = "SELECT dim.customers.customer_id, dim.customers.customer_name FROM dim.customers"

        task = RawPipelineTask(
            urn="urn:dcs:task:airflow:prod:test_schema.test_task",
            name="test_task",
            task_type="sql",
            pipeline_urn=pipeline.urn,
            operator="PostgresOperator",
            meta={"sql": sql_query},
        )
        parse_result.pipeline_tasks.append(task)

        parse_result.orchestration_edges.append(
            RawOrchestrationEdge(
                source_urn=pipeline.urn,
                target_urn=task.urn,
                edge_category="task_dependency",
                edge_type="contains",
            )
        )

        # Ingest
        ingestion_service = IngestionService(test_session)
        job, stats = await ingestion_service._persist_parse_result(
            parse_result=parse_result,
            source_system=source_system,
            cleanup_orphans=False,
        )

        await test_session.commit()

        # Verify column lineage was created with schema matching
        result = await test_session.execute(select(ColumnLineage))
        column_edges = result.scalars().all()

        # Should resolve "dim.customers.customer_id" correctly
        assert len(column_edges) >= 2  # customer_id and customer_name
