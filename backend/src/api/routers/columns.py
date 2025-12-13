"""Column endpoints."""

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.api.exceptions import NotFoundError
from src.database import DbSession
from src.repositories import ColumnRepository
from src.repositories.lineage import ColumnLineageRepository

router = APIRouter(prefix="/columns")


class ColumnSummary(BaseModel):
    """Summary view of a column."""

    id: str
    urn: str
    name: str
    data_type: Optional[str] = None
    semantic_type: Optional[str] = None
    pii_type: Optional[str] = None
    pii_detected_by: Optional[str] = None
    capsule_urn: str
    capsule_name: str
    layer: Optional[str] = None
    description: Optional[str] = None


class ColumnDetail(ColumnSummary):
    """Detailed view of a column."""

    ordinal_position: Optional[int] = None
    is_nullable: bool = True
    has_tests: bool = False
    test_count: int = 0
    meta: dict = {}
    tags: list[str] = []
    stats: dict = {}
    created_at: str
    updated_at: str


class ColumnListResponse(BaseModel):
    """Response for column list."""

    data: list[ColumnSummary]
    pagination: dict


@router.get("", response_model=ColumnListResponse)
async def list_columns(
    db: DbSession,
    semantic_type: Optional[str] = Query(None, description="Filter by semantic type"),
    pii_type: Optional[str] = Query(None, description="Filter by PII type"),
    search: Optional[str] = Query(None, description="Search column names"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> ColumnListResponse:
    """List columns with filtering and pagination."""
    repo = ColumnRepository(db)

    if search:
        columns = await repo.search(query=search, offset=offset, limit=limit)
    elif pii_type:
        columns = await repo.get_pii_columns_by_type(pii_type=pii_type, offset=offset, limit=limit)
    elif semantic_type:
        columns = await repo.get_by_semantic_type(semantic_type=semantic_type, offset=offset, limit=limit)
    else:
        columns = await repo.get_all(offset=offset, limit=limit)

    data = [
        ColumnSummary(
            id=str(c.id),
            urn=c.urn,
            name=c.name,
            data_type=c.data_type,
            semantic_type=c.semantic_type,
            pii_type=c.pii_type,
            pii_detected_by=c.pii_detected_by,
            capsule_urn=c.capsule.urn if c.capsule else "",
            capsule_name=c.capsule.name if c.capsule else "",
            layer=c.capsule.layer if c.capsule else None,
            description=c.description,
        )
        for c in columns
    ]

    total = await repo.count()

    return ColumnListResponse(
        data=data,
        pagination={
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + len(data) < total,
        },
    )


@router.get("/pii", response_model=ColumnListResponse)
async def list_pii_columns(
    db: DbSession,
    pii_type: Optional[str] = Query(None, description="Filter by specific PII type"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> ColumnListResponse:
    """List all columns identified as PII."""
    repo = ColumnRepository(db)

    if pii_type:
        columns = await repo.get_pii_columns_by_type(pii_type=pii_type, offset=offset, limit=limit)
    else:
        columns = await repo.get_pii_columns(offset=offset, limit=limit)

    data = [
        ColumnSummary(
            id=str(c.id),
            urn=c.urn,
            name=c.name,
            data_type=c.data_type,
            semantic_type=c.semantic_type,
            pii_type=c.pii_type,
            pii_detected_by=c.pii_detected_by,
            capsule_urn=c.capsule.urn if c.capsule else "",
            capsule_name=c.capsule.name if c.capsule else "",
            layer=c.capsule.layer if c.capsule else None,
            description=c.description,
        )
        for c in columns
    ]

    pii_count = await repo.count_pii()

    return ColumnListResponse(
        data=data,
        pagination={
            "total": pii_count,
            "offset": offset,
            "limit": limit,
            "has_more": offset + len(data) < pii_count,
        },
    )


@router.get("/stats")
async def get_column_stats(db: DbSession) -> dict:
    """Get aggregated statistics about columns."""
    repo = ColumnRepository(db)

    total = await repo.count()
    pii_count = await repo.count_pii()
    pii_by_type = await repo.count_pii_by_type()
    by_semantic_type = await repo.count_by_semantic_type()

    return {
        "total_columns": total,
        "pii_columns": pii_count,
        "pii_by_type": pii_by_type,
        "by_semantic_type": by_semantic_type,
    }


class ColumnLineageNode(BaseModel):
    """Node in column lineage graph."""

    id: str
    urn: str
    name: str
    data_type: Optional[str] = None
    semantic_type: Optional[str] = None
    pii_type: Optional[str] = None
    capsule_urn: str
    capsule_name: str
    layer: Optional[str] = None
    depth: int
    direction: str  # "upstream" or "downstream"


class ColumnLineageEdge(BaseModel):
    """Edge in column lineage graph."""

    source_urn: str
    target_urn: str
    transformation_type: Optional[str] = None
    transformation_expr: Optional[str] = None


class ColumnLineageResponse(BaseModel):
    """Column lineage query response."""

    root: ColumnSummary
    nodes: list[ColumnLineageNode] = []
    edges: list[ColumnLineageEdge] = []
    summary: dict


@router.get("/{urn:path}/lineage", response_model=ColumnLineageResponse)
async def get_column_lineage(
    urn: str,
    db: DbSession,
    direction: str = Query("both", pattern="^(upstream|downstream|both)$"),
    depth: int = Query(3, ge=1, le=10),
) -> ColumnLineageResponse:
    """Get lineage for a column (traces PII and data flows at column level)."""
    repo = ColumnRepository(db)
    lineage_repo = ColumnLineageRepository(db)

    column = await repo.get_by_urn_with_lineage(urn)
    if not column:
        raise NotFoundError("Column", urn)

    nodes: list[ColumnLineageNode] = []
    edges: list[ColumnLineageEdge] = []
    seen_urns: set[str] = {urn}

    async def traverse_upstream(col_id, current_depth: int):
        """Recursively traverse upstream lineage."""
        if current_depth > depth:
            return
        upstream_edges = await lineage_repo.get_upstream_edges(col_id)
        source_ids = [e.source_column_id for e in upstream_edges]
        if source_ids:
            source_columns = await repo.get_by_ids(source_ids)
            col_map = {c.id: c for c in source_columns}
            for edge in upstream_edges:
                edges.append(ColumnLineageEdge(
                    source_urn=edge.source_urn,
                    target_urn=edge.target_urn,
                    transformation_type=edge.transformation_type,
                    transformation_expr=edge.transformation_expr,
                ))
                source_col = col_map.get(edge.source_column_id)
                if source_col and source_col.urn not in seen_urns:
                    seen_urns.add(source_col.urn)
                    nodes.append(ColumnLineageNode(
                        id=str(source_col.id),
                        urn=source_col.urn,
                        name=source_col.name,
                        data_type=source_col.data_type,
                        semantic_type=source_col.semantic_type,
                        pii_type=source_col.pii_type,
                        capsule_urn=source_col.capsule.urn if source_col.capsule else "",
                        capsule_name=source_col.capsule.name if source_col.capsule else "",
                        layer=source_col.capsule.layer if source_col.capsule else None,
                        depth=current_depth,
                        direction="upstream",
                    ))
                    await traverse_upstream(source_col.id, current_depth + 1)

    async def traverse_downstream(col_id, current_depth: int):
        """Recursively traverse downstream lineage."""
        if current_depth > depth:
            return
        downstream_edges = await lineage_repo.get_downstream_edges(col_id)
        target_ids = [e.target_column_id for e in downstream_edges]
        if target_ids:
            target_columns = await repo.get_by_ids(target_ids)
            col_map = {c.id: c for c in target_columns}
            for edge in downstream_edges:
                edges.append(ColumnLineageEdge(
                    source_urn=edge.source_urn,
                    target_urn=edge.target_urn,
                    transformation_type=edge.transformation_type,
                    transformation_expr=edge.transformation_expr,
                ))
                target_col = col_map.get(edge.target_column_id)
                if target_col and target_col.urn not in seen_urns:
                    seen_urns.add(target_col.urn)
                    nodes.append(ColumnLineageNode(
                        id=str(target_col.id),
                        urn=target_col.urn,
                        name=target_col.name,
                        data_type=target_col.data_type,
                        semantic_type=target_col.semantic_type,
                        pii_type=target_col.pii_type,
                        capsule_urn=target_col.capsule.urn if target_col.capsule else "",
                        capsule_name=target_col.capsule.name if target_col.capsule else "",
                        layer=target_col.capsule.layer if target_col.capsule else None,
                        depth=current_depth,
                        direction="downstream",
                    ))
                    await traverse_downstream(target_col.id, current_depth + 1)

    # Traverse based on direction
    if direction in ("upstream", "both"):
        await traverse_upstream(column.id, 1)

    if direction in ("downstream", "both"):
        await traverse_downstream(column.id, 1)

    root = ColumnSummary(
        id=str(column.id),
        urn=column.urn,
        name=column.name,
        data_type=column.data_type,
        semantic_type=column.semantic_type,
        pii_type=column.pii_type,
        pii_detected_by=column.pii_detected_by,
        capsule_urn=column.capsule.urn if column.capsule else "",
        capsule_name=column.capsule.name if column.capsule else "",
        layer=column.capsule.layer if column.capsule else None,
        description=column.description,
    )

    upstream_count = sum(1 for n in nodes if n.direction == "upstream")
    downstream_count = sum(1 for n in nodes if n.direction == "downstream")

    return ColumnLineageResponse(
        root=root,
        nodes=nodes,
        edges=edges,
        summary={
            "upstream_count": upstream_count,
            "downstream_count": downstream_count,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "depth_requested": depth,
            "is_pii": column.is_pii,
            "pii_type": column.pii_type,
        },
    )


@router.get("/{urn:path}", response_model=ColumnDetail)
async def get_column(
    urn: str,
    db: DbSession,
) -> ColumnDetail:
    """Get column details by URN."""
    repo = ColumnRepository(db)
    column = await repo.get_by_urn(urn)

    if not column:
        raise NotFoundError("Column", urn)

    return ColumnDetail(
        id=str(column.id),
        urn=column.urn,
        name=column.name,
        data_type=column.data_type,
        semantic_type=column.semantic_type,
        pii_type=column.pii_type,
        pii_detected_by=column.pii_detected_by,
        capsule_urn=column.capsule.urn if column.capsule else "",
        capsule_name=column.capsule.name if column.capsule else "",
        layer=column.capsule.layer if column.capsule else None,
        description=column.description,
        ordinal_position=column.ordinal_position,
        is_nullable=column.is_nullable,
        has_tests=column.has_tests,
        test_count=column.test_count,
        meta=column.meta or {},
        tags=column.tags or [],
        stats=column.stats or {},
        created_at=column.created_at.isoformat(),
        updated_at=column.updated_at.isoformat(),
    )
