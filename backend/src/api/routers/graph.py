"""Graph export API endpoints.

Provides endpoints to export the property graph in various formats
for visualization and import into external tools.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel

from src.api.exceptions import NotFoundError, ValidationError_
from src.database import DbSession
from src.services.graph_export import ExportFormat, GraphExportService
from src.services.lineage import LineageService

router = APIRouter(prefix="/graph")


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class ExportStatsResponse(BaseModel):
    """Statistics about the export."""

    node_count: int
    edge_count: int
    format: str
    content_type: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/export")
async def export_graph(
    db: DbSession,
    format: ExportFormat = Query(
        ExportFormat.MERMAID,
        description="Output format: graphml, dot, cypher, mermaid, json-ld, json",
    ),
    domain_id: Optional[UUID] = Query(
        None,
        description="Filter to specific domain",
    ),
    include_columns: bool = Query(
        False,
        description="Include column nodes and edges",
    ),
    include_tags: bool = Query(
        False,
        description="Include tag nodes and TAGGED_WITH edges",
    ),
    include_data_products: bool = Query(
        False,
        description="Include data product nodes and PART_OF edges",
    ),
) -> Response:
    """
    Export the property graph in various formats.

    Supported formats:
    - **graphml**: XML format for yEd, Gephi, and other graph tools
    - **dot**: Graphviz DOT format for rendering with `dot`, `neato`, etc.
    - **cypher**: Neo4j Cypher statements for graph database import
    - **mermaid**: Mermaid flowchart syntax for documentation
    - **json-ld**: JSON-LD format for semantic web applications
    - **json**: Simple JSON format for visualization (React Flow)

    Options:
    - Filter by domain to export only a subset of the graph
    - Include column-level nodes for detailed lineage
    - Include tags to see classification relationships
    - Include data products to see logical groupings
    """
    service = GraphExportService(db)

    try:
        content = await service.export_full_graph(
            format=format,
            include_columns=include_columns,
            include_tags=include_tags,
            include_data_products=include_data_products,
            domain_id=domain_id,
        )
    except ValueError as e:
        raise ValidationError_(str(e))

    content_types = {
        ExportFormat.GRAPHML: "application/xml",
        ExportFormat.DOT: "text/plain",
        ExportFormat.CYPHER: "text/plain",
        ExportFormat.MERMAID: "text/plain",
        ExportFormat.JSON_LD: "application/ld+json",
        ExportFormat.JSON: "application/json",
    }

    file_extensions = {
        ExportFormat.GRAPHML: "graphml",
        ExportFormat.DOT: "dot",
        ExportFormat.CYPHER: "cypher",
        ExportFormat.MERMAID: "mmd",
        ExportFormat.JSON_LD: "jsonld",
        ExportFormat.JSON: "json",
    }

    return Response(
        content=content,
        media_type=content_types[format],
        headers={
            "Content-Disposition": f"attachment; filename=graph.{file_extensions[format]}"
        },
    )


@router.get("/export/lineage/{urn:path}")
async def export_lineage(
    urn: str,
    db: DbSession,
    format: ExportFormat = Query(
        ExportFormat.MERMAID,
        description="Output format: graphml, dot, cypher, mermaid, json-ld, json",
    ),
    depth: int = Query(
        3,
        ge=1,
        le=10,
        description="Number of hops to traverse (1-10)",
    ),
    direction: str = Query(
        "both",
        pattern="^(upstream|downstream|both)$",
        description="Direction to traverse: upstream, downstream, or both",
    ),
    include_columns: bool = Query(
        False,
        description="Include column-level lineage",
    ),
) -> Response:
    """
    Export lineage subgraph for a specific capsule.

    Generates a subgraph centered on the specified capsule, traversing
    lineage relationships up to the specified depth.

    **Direction options:**
    - **upstream**: Show sources (what flows INTO this capsule)
    - **downstream**: Show targets (what this capsule flows TO)
    - **both**: Show both directions

    **Example URNs:**
    - `urn:dab:capsule:jaffle_shop:orders`
    - `urn:dab:capsule:myproject:staging:stg_customers`
    """
    service = GraphExportService(db)

    try:
        content = await service.export_lineage_subgraph(
            urn=urn,
            format=format,
            depth=depth,
            direction=direction,
            include_columns=include_columns,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise NotFoundError("Capsule", urn)
        raise ValidationError_(str(e))

    content_types = {
        ExportFormat.GRAPHML: "application/xml",
        ExportFormat.DOT: "text/plain",
        ExportFormat.CYPHER: "text/plain",
        ExportFormat.MERMAID: "text/plain",
        ExportFormat.JSON_LD: "application/ld+json",
        ExportFormat.JSON: "application/json",
    }

    file_extensions = {
        ExportFormat.GRAPHML: "graphml",
        ExportFormat.DOT: "dot",
        ExportFormat.CYPHER: "cypher",
        ExportFormat.MERMAID: "mmd",
        ExportFormat.JSON_LD: "jsonld",
        ExportFormat.JSON: "json",
    }

    # Use capsule name in filename
    safe_name = urn.split(":")[-1].replace(".", "_")

    return Response(
        content=content,
        media_type=content_types[format],
        headers={
            "Content-Disposition": f"attachment; filename=lineage_{safe_name}.{file_extensions[format]}"
        },
    )


@router.get("/formats")
async def list_formats() -> dict:
    """
    List available export formats and their descriptions.
    """
    return {
        "formats": [
            {
                "name": "graphml",
                "description": "GraphML XML format for graph visualization tools",
                "tools": ["yEd", "Gephi", "Cytoscape", "NetworkX"],
                "content_type": "application/xml",
            },
            {
                "name": "dot",
                "description": "Graphviz DOT language for rendering diagrams",
                "tools": ["Graphviz (dot, neato, fdp)", "VSCode Graphviz Preview"],
                "content_type": "text/plain",
            },
            {
                "name": "cypher",
                "description": "Neo4j Cypher query language for graph database import",
                "tools": ["Neo4j", "Amazon Neptune", "Memgraph"],
                "content_type": "text/plain",
            },
            {
                "name": "mermaid",
                "description": "Mermaid flowchart syntax for documentation",
                "tools": ["GitHub", "GitLab", "Notion", "Obsidian", "Mermaid Live"],
                "content_type": "text/plain",
            },
            {
                "name": "json-ld",
                "description": "JSON-LD format for semantic web and linked data",
                "tools": ["JSON-LD Playground", "Apache Jena", "RDF tools"],
                "content_type": "application/ld+json",
            },
            {
                "name": "json",
                "description": "Simple JSON format for web visualization",
                "tools": ["React Flow", "D3.js", "vis.js", "Cytoscape.js"],
                "content_type": "application/json",
            },
        ]
    }


# ---------------------------------------------------------------------------
# Phase 4: Integrated Lineage (Orchestration + Data)
# ---------------------------------------------------------------------------


@router.get("/lineage/integrated/{urn:path}")
async def get_integrated_lineage(
    urn: str,
    db: DbSession,
    direction: str = Query(
        "both",
        pattern="^(upstream|downstream|both)$",
        description="Direction to traverse: upstream, downstream, or both",
    ),
    depth: int = Query(
        3,
        ge=1,
        le=5,
        description="Number of hops to traverse (1-5)",
    ),
    include_orchestration: bool = Query(
        True,
        description="Include pipeline tasks and orchestration edges",
    ),
) -> dict:
    """Get integrated lineage combining data and orchestration edges.

    This endpoint provides a unified view of data lineage that includes:
    - **Data Lineage**: Capsule-to-capsule FLOWS_TO relationships
    - **Orchestration**: Pipeline tasks that PRODUCE/CONSUME capsules

    **Use Cases:**
    - Understand which pipelines produce a dataset
    - Trace data flow through both capsules and pipeline tasks
    - Impact analysis showing orchestration dependencies

    **Example:**
    ```
    GET /graph/lineage/integrated/urn:dcs:postgres:table:analytics.facts:revenue
    ```

    Returns nodes (capsules + tasks) and edges (data lineage + orchestration).
    """
    service = LineageService(db)

    try:
        result = await service.get_integrated_lineage(
            urn=urn,
            direction=direction,
            depth=depth,
            include_orchestration=include_orchestration,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise NotFoundError("Capsule or Task", urn)
        raise ValidationError_(str(e))

    return result


@router.get("/impact-analysis/{pipeline_urn:path}")
async def analyze_pipeline_impact(
    pipeline_urn: str,
    db: DbSession,
    scenario: str = Query(
        "modify",
        pattern="^(modify|disable|delete)$",
        description="Change scenario: modify, disable, or delete",
    ),
    task_urn: Optional[str] = Query(
        None,
        description="Optional specific task URN for task-level analysis",
    ),
) -> dict:
    """Analyze the impact of changes to a pipeline.

    Performs impact analysis to understand what would be affected by:
    - **modify**: Changing pipeline logic or schedule
    - **disable**: Pausing pipeline execution
    - **delete**: Permanently removing the pipeline

    **Returns:**
    - Directly affected capsules (produces/transforms)
    - Downstream capsules that depend on pipeline outputs
    - Consuming tasks in other pipelines
    - Risk level and recommendations

    **Example:**
    ```
    GET /graph/impact-analysis/urn:dcs:pipeline:airflow:prod:finance_pipeline?scenario=disable
    ```

    **Use Cases:**
    - Pre-deployment impact assessment
    - Change management and risk analysis
    - Understanding pipeline dependencies
    """
    service = LineageService(db)

    try:
        result = await service.analyze_pipeline_impact(
            pipeline_urn=pipeline_urn,
            scenario=scenario,
            task_urn=task_urn,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise NotFoundError("Pipeline", pipeline_urn)
        raise ValidationError_(str(e))

    return result


# ---------------------------------------------------------------------------
# Phase 6: Column-Level Lineage (Fine-Grained Tracking)
# ---------------------------------------------------------------------------


@router.get("/column-lineage/{column_urn:path}")
async def get_column_lineage(
    column_urn: str,
    db: DbSession,
    direction: str = Query(
        "both",
        pattern="^(upstream|downstream|both)$",
        description="Direction to traverse: upstream, downstream, or both",
    ),
    depth: int = Query(
        5,
        ge=1,
        le=10,
        description="Number of hops to traverse (1-10)",
    ),
) -> dict:
    """Get column-level lineage graph.

    Traces fine-grained column-to-column lineage relationships, showing:
    - **Upstream**: Source columns that feed into this column
    - **Downstream**: Target columns derived from this column
    - **Transformations**: SQL operations applied (identity, cast, aggregate, etc.)
    - **Confidence Scores**: Detection accuracy (0.0-1.0)

    **Returns:**
    - **nodes**: Array of column nodes with metadata (name, type, capsule)
    - **edges**: Array of lineage edges with transformation details
    - **summary**: Statistics (total_nodes, total_edges, max_depth_reached)

    **Example:**
    ```
    GET /graph/column-lineage/urn:dcs:column:postgres.analytics.revenue:customer_id?direction=both&depth=5
    ```

    **Use Cases:**
    - Understand column dependencies at SQL level
    - Trace data transformations through pipelines
    - Impact analysis for schema changes
    """
    from src.repositories.column_lineage import ColumnLineageRepository

    repo = ColumnLineageRepository(db)

    try:
        result = await repo.trace_column_lineage(
            column_urn=column_urn,
            direction=direction,
            depth=depth,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise NotFoundError("Column", column_urn)
        raise ValidationError_(str(e))

    return result


@router.get("/columns/{column_urn:path}/upstream")
async def get_upstream_columns(
    column_urn: str,
    db: DbSession,
    depth: int = Query(
        3,
        ge=1,
        le=10,
        description="Number of hops to traverse upstream (1-10)",
    ),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Results per page"),
) -> dict:
    """Get upstream source columns for a given column.

    Returns columns that flow INTO the specified column through transformations.

    **Example:**
    ```
    GET /graph/columns/urn:dcs:column:postgres.analytics.revenue:total_amount/upstream?depth=3
    ```

    **Response:**
    ```json
    {
      "column_urn": "urn:dcs:column:...",
      "upstream_columns": [
        {
          "column_urn": "urn:dcs:column:postgres.raw.orders:amount",
          "column_name": "amount",
          "data_type": "DECIMAL(10,2)",
          "capsule_urn": "urn:dcs:postgres:table:raw.orders",
          "capsule_name": "orders",
          "transformation_type": "aggregate",
          "transformation_logic": "SUM(amount)",
          "confidence": 0.95,
          "depth": 1
        }
      ],
      "total": 5
    }
    ```
    """
    from src.repositories.column_lineage import ColumnLineageRepository

    repo = ColumnLineageRepository(db)

    try:
        upstream = await repo.get_upstream_columns(
            column_urn=column_urn,
            depth=depth,
            offset=offset,
            limit=limit,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise NotFoundError("Column", column_urn)
        raise ValidationError_(str(e))

    return {
        "column_urn": column_urn,
        "upstream_columns": upstream,
        "total": len(upstream),
    }


@router.get("/columns/{column_urn:path}/downstream")
async def get_downstream_columns(
    column_urn: str,
    db: DbSession,
    depth: int = Query(
        3,
        ge=1,
        le=10,
        description="Number of hops to traverse downstream (1-10)",
    ),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Results per page"),
) -> dict:
    """Get downstream target columns derived from a given column.

    Returns columns that are derived FROM the specified column through transformations.

    **Example:**
    ```
    GET /graph/columns/urn:dcs:column:postgres.raw.orders:customer_id/downstream?depth=3
    ```

    **Use Cases:**
    - Impact analysis: What breaks if this column changes?
    - Understand column usage across datasets
    - Trace data propagation through transformations
    """
    from src.repositories.column_lineage import ColumnLineageRepository

    repo = ColumnLineageRepository(db)

    try:
        downstream = await repo.get_downstream_columns(
            column_urn=column_urn,
            depth=depth,
            offset=offset,
            limit=limit,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise NotFoundError("Column", column_urn)
        raise ValidationError_(str(e))

    return {
        "column_urn": column_urn,
        "downstream_columns": downstream,
        "total": len(downstream),
    }


@router.get("/columns/{column_urn:path}/transformations")
async def get_column_transformations(
    column_urn: str,
    db: DbSession,
) -> dict:
    """Get all transformations applied to create a column.

    Returns the SQL operations and logic used to derive this column from sources.

    **Example:**
    ```
    GET /graph/columns/urn:dcs:column:postgres.analytics.revenue:total_spent/transformations
    ```

    **Response:**
    ```json
    {
      "column_urn": "urn:dcs:column:...",
      "transformations": [
        {
          "source_column_urn": "urn:dcs:column:postgres.raw.orders:amount",
          "transformation_type": "aggregate",
          "transformation_logic": "SUM(amount)",
          "edge_type": "derives_from",
          "confidence": 0.95,
          "detected_by": "sql_parser"
        }
      ],
      "total": 1
    }
    ```

    **Use Cases:**
    - Understand how a column is computed
    - Audit transformation logic
    - Identify complex vs. simple derivations
    """
    from src.repositories.column_lineage import ColumnLineageRepository

    repo = ColumnLineageRepository(db)

    try:
        transformations = await repo.get_column_transformations(column_urn=column_urn)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise NotFoundError("Column", column_urn)
        raise ValidationError_(str(e))

    return {
        "column_urn": column_urn,
        "transformations": transformations,
        "total": len(transformations),
    }


@router.get("/columns/{column_urn:path}/impact")
async def analyze_column_impact(
    column_urn: str,
    db: DbSession,
    change_type: str = Query(
        "delete",
        pattern="^(delete|rename|type_change)$",
        description="Type of schema change: delete, rename, or type_change",
    ),
) -> dict:
    """Analyze the impact of changing a column's schema.

    Performs impact analysis to understand what would break if you:
    - **delete**: Remove the column from the schema
    - **rename**: Change the column name
    - **type_change**: Modify the column's data type

    **Returns:**
    - **risk_level**: none, low, medium, high
    - **affected_columns**: Count of downstream columns impacted
    - **affected_capsules**: Count of unique capsules affected
    - **affected_tasks**: Count of pipeline tasks reading/writing this column
    - **breaking_changes**: Detailed list of dependencies that will break
    - **recommendations**: Suggested mitigation actions

    **Example:**
    ```
    GET /graph/columns/urn:dcs:column:postgres.raw.orders:customer_id/impact?change_type=delete
    ```

    **Response:**
    ```json
    {
      "column_urn": "urn:dcs:column:postgres.raw.orders:customer_id",
      "change_type": "delete",
      "risk_level": "high",
      "affected_columns": 15,
      "affected_capsules": 8,
      "affected_tasks": 12,
      "breaking_changes": [
        {
          "target_column_urn": "...",
          "target_column_name": "customer_id",
          "capsule_name": "analytics.revenue",
          "reason": "Direct dependency - source column will be missing",
          "suggested_action": "Update transformation logic or remove dependency"
        }
      ],
      "recommendations": [
        "Review 15 downstream dependencies before deletion",
        "Consider deprecation period with warnings before removal",
        "Update 12 affected pipeline tasks"
      ]
    }
    ```

    **Use Cases:**
    - Pre-change impact assessment
    - Schema evolution planning
    - Breaking change detection
    - Migration risk analysis
    """
    from src.repositories.column_lineage import ColumnLineageRepository

    repo = ColumnLineageRepository(db)

    try:
        result = await repo.get_column_impact(
            column_urn=column_urn,
            change_type=change_type,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise NotFoundError("Column", column_urn)
        raise ValidationError_(str(e))

    return result
