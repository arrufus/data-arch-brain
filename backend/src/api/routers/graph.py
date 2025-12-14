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
        description="Output format: graphml, dot, cypher, mermaid, json-ld",
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
    }

    file_extensions = {
        ExportFormat.GRAPHML: "graphml",
        ExportFormat.DOT: "dot",
        ExportFormat.CYPHER: "cypher",
        ExportFormat.MERMAID: "mmd",
        ExportFormat.JSON_LD: "jsonld",
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
        description="Output format: graphml, dot, cypher, mermaid, json-ld",
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
    }

    file_extensions = {
        ExportFormat.GRAPHML: "graphml",
        ExportFormat.DOT: "dot",
        ExportFormat.CYPHER: "cypher",
        ExportFormat.MERMAID: "mmd",
        ExportFormat.JSON_LD: "jsonld",
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
        ]
    }
