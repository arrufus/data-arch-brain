"""Capsule (data asset) endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text

from src.api.exceptions import NotFoundError, ValidationError_
from src.database import DbSession
from src.repositories import CapsuleRepository, ColumnRepository

router = APIRouter(prefix="/capsules")


class CapsuleSummary(BaseModel):
    """Summary view of a capsule."""

    id: str
    urn: str
    name: str
    capsule_type: str
    layer: Optional[str] = None
    schema_name: Optional[str] = None
    database_name: Optional[str] = None
    domain_name: Optional[str] = None
    description: Optional[str] = None
    column_count: int = 0
    has_pii: bool = False
    has_tests: bool = False


class CapsuleDetail(CapsuleSummary):
    """Detailed view of a capsule."""

    materialization: Optional[str] = None
    owner_name: Optional[str] = None
    source_system: Optional[str] = None
    pii_column_count: int = 0
    test_count: int = 0
    doc_coverage: float = 0.0
    upstream_count: int = 0
    downstream_count: int = 0
    violation_count: int = 0
    meta: dict = {}
    tags: list[str] = []
    created_at: str
    updated_at: str


class ColumnSummary(BaseModel):
    """Summary view of a column."""

    id: str
    urn: str
    name: str
    data_type: Optional[str] = None
    ordinal_position: Optional[int] = None
    semantic_type: Optional[str] = None
    pii_type: Optional[str] = None
    pii_detected_by: Optional[str] = None
    description: Optional[str] = None
    has_tests: bool = False
    test_count: int = 0


class LineageNode(BaseModel):
    """Node in lineage graph."""

    id: str
    urn: str
    name: str
    layer: Optional[str] = None
    capsule_type: str
    depth: int
    direction: str  # "upstream" or "downstream"


class LineageEdge(BaseModel):
    """Edge in lineage graph."""

    source_urn: str
    target_urn: str
    edge_type: str
    transformation: Optional[str] = None


class LineageResponse(BaseModel):
    """Lineage query response."""

    root: CapsuleSummary
    nodes: list[LineageNode] = []
    edges: list[LineageEdge] = []
    summary: dict


class CapsuleListResponse(BaseModel):
    """Response for capsule list."""

    data: list[CapsuleSummary]
    pagination: dict


class ColumnListResponse(BaseModel):
    """Response for column list."""

    data: list[ColumnSummary]
    pagination: dict


@router.get("", response_model=CapsuleListResponse)
async def list_capsules(
    db: DbSession,
    layer: Optional[str] = Query(None, description="Filter by architecture layer"),
    capsule_type: Optional[str] = Query(None, description="Filter by type"),
    domain_id: Optional[UUID] = Query(None, description="Filter by domain ID"),
    has_pii: Optional[bool] = Query(None, description="Filter by PII presence"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> CapsuleListResponse:
    """List capsules with filtering and pagination."""
    repo = CapsuleRepository(db)

    if search:
        capsules = await repo.search(
            query=search,
            capsule_type=capsule_type,
            layer=layer,
            domain_id=domain_id,
            offset=offset,
            limit=limit,
        )
    elif has_pii:
        capsules = await repo.get_with_pii(offset=offset, limit=limit)
    elif layer:
        capsules = await repo.get_by_layer(layer=layer, offset=offset, limit=limit)
    elif capsule_type:
        capsules = await repo.get_by_type(capsule_type=capsule_type, offset=offset, limit=limit)
    elif domain_id:
        capsules = await repo.get_by_domain(domain_id=domain_id, offset=offset, limit=limit)
    else:
        capsules = await repo.get_all(offset=offset, limit=limit)

    data = [
        CapsuleSummary(
            id=str(c.id),
            urn=c.urn,
            name=c.name,
            capsule_type=c.capsule_type,
            layer=c.layer,
            schema_name=c.schema_name,
            database_name=c.database_name,
            domain_name=c.domain.name if c.domain else None,
            description=c.description,
            column_count=c.column_count,
            has_pii=c.has_pii,
            has_tests=c.has_tests,
        )
        for c in capsules
    ]

    total = await repo.count()

    return CapsuleListResponse(
        data=data,
        pagination={
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + len(data) < total,
        },
    )


@router.get("/stats")
async def get_capsule_stats(db: DbSession) -> dict:
    """Get aggregated statistics about capsules."""
    repo = CapsuleRepository(db)

    by_layer = await repo.count_by_layer()
    by_type = await repo.count_by_type()
    total = await repo.count()

    # Get PII stats - count capsules with at least one PII column
    result = await db.execute(
        text("""
        SELECT COUNT(DISTINCT c.id) as capsules_with_pii
        FROM capsules c
        INNER JOIN columns col ON col.capsule_id = c.id
        WHERE col.pii_type IS NOT NULL
        """)
    )
    capsules_with_pii = result.scalar() or 0

    # Get documentation stats
    result = await db.execute(
        text("""
        SELECT COUNT(*) as capsules_with_docs
        FROM capsules
        WHERE description IS NOT NULL AND description != ''
        """)
    )
    capsules_with_docs = result.scalar() or 0

    # Get average column count
    result = await db.execute(
        text("""
        SELECT AVG(col_count) as avg_columns
        FROM (
            SELECT COUNT(*) as col_count
            FROM columns
            GROUP BY capsule_id
        ) subq
        """)
    )
    average_column_count = float(result.scalar() or 0)

    # Get average doc coverage (percentage of capsules with descriptions)
    average_doc_coverage = (capsules_with_docs / total * 100) if total > 0 else 0

    return {
        "total_capsules": total,
        "by_layer": by_layer,
        "by_type": by_type,
        "capsules_with_pii": capsules_with_pii,
        "capsules_with_docs": capsules_with_docs,
        "average_column_count": round(average_column_count, 1),
        "average_doc_coverage": round(average_doc_coverage, 1),
    }


@router.get("/{urn:path}/detail", response_model=CapsuleDetail)
async def get_capsule(
    urn: str,
    db: DbSession,
) -> CapsuleDetail:
    """Get capsule details by URN."""
    repo = CapsuleRepository(db)
    capsule = await repo.get_by_urn_with_columns(urn)

    if not capsule:
        raise NotFoundError("Capsule", urn)

    # Get upstream/downstream counts (using depth=3 to match lineage tab default)
    upstream = await repo.get_upstream(capsule.id, depth=3)
    downstream = await repo.get_downstream(capsule.id, depth=3)

    return CapsuleDetail(
        id=str(capsule.id),
        urn=capsule.urn,
        name=capsule.name,
        capsule_type=capsule.capsule_type,
        layer=capsule.layer,
        schema_name=capsule.schema_name,
        database_name=capsule.database_name,
        domain_name=capsule.domain.name if capsule.domain else None,
        description=capsule.description,
        column_count=capsule.column_count,
        has_pii=capsule.has_pii,
        has_tests=capsule.has_tests,
        materialization=capsule.materialization,
        owner_name=capsule.owner.name if capsule.owner else None,
        source_system=capsule.source_system.name if capsule.source_system else None,
        pii_column_count=capsule.pii_column_count,
        test_count=capsule.test_count,
        doc_coverage=capsule.doc_coverage,
        upstream_count=len(upstream),
        downstream_count=len(downstream),
        violation_count=len(capsule.violations),
        meta=capsule.meta or {},
        tags=capsule.tags or [],
        created_at=capsule.created_at.isoformat(),
        updated_at=capsule.updated_at.isoformat(),
    )


@router.get("/{urn:path}/columns", response_model=ColumnListResponse)
async def get_capsule_columns(
    urn: str,
    db: DbSession,
    semantic_type: Optional[str] = Query(None),
    pii_type: Optional[str] = Query(None),
    has_tests: Optional[bool] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
) -> ColumnListResponse:
    """Get columns for a capsule."""
    capsule_repo = CapsuleRepository(db)
    column_repo = ColumnRepository(db)

    capsule = await capsule_repo.get_by_urn(urn)
    if not capsule:
        raise NotFoundError("Capsule", urn)

    columns = await column_repo.get_by_capsule_id(
        capsule_id=capsule.id,
        offset=offset,
        limit=limit,
    )

    # Apply filters
    filtered_columns = columns
    if semantic_type:
        filtered_columns = [c for c in filtered_columns if c.semantic_type == semantic_type]
    if pii_type:
        filtered_columns = [c for c in filtered_columns if c.pii_type == pii_type]
    if has_tests is not None:
        filtered_columns = [c for c in filtered_columns if c.has_tests == has_tests]

    data = [
        ColumnSummary(
            id=str(c.id),
            urn=c.urn,
            name=c.name,
            data_type=c.data_type,
            ordinal_position=c.ordinal_position,
            semantic_type=c.semantic_type,
            pii_type=c.pii_type,
            pii_detected_by=c.pii_detected_by,
            description=c.description,
            has_tests=c.has_tests,
            test_count=c.test_count,
        )
        for c in filtered_columns
    ]

    return ColumnListResponse(
        data=data,
        pagination={
            "total": len(filtered_columns),
            "offset": offset,
            "limit": limit,
            "has_more": False,  # Already filtered all
        },
    )


@router.get("/{urn:path}/lineage", response_model=LineageResponse)
async def get_capsule_lineage(
    urn: str,
    db: DbSession,
    direction: str = Query("both", pattern="^(upstream|downstream|both)$"),
    depth: int = Query(3, ge=1, le=10),
) -> LineageResponse:
    """Get lineage for a capsule."""
    repo = CapsuleRepository(db)

    capsule = await repo.get_by_urn_with_columns(urn)
    if not capsule:
        raise NotFoundError("Capsule", urn)

    nodes: list[LineageNode] = []
    edges: list[LineageEdge] = []
    seen_urns: set[str] = {urn}

    # Get upstream lineage
    if direction in ("upstream", "both"):
        upstream = await repo.get_upstream(capsule.id, depth=depth)
        for u in upstream:
            if u.urn not in seen_urns:
                seen_urns.add(u.urn)
                nodes.append(LineageNode(
                    id=str(u.id),
                    urn=u.urn,
                    name=u.name,
                    layer=u.layer,
                    capsule_type=u.capsule_type,
                    depth=1,  # Simplified - could track actual depth
                    direction="upstream",
                ))

        # Add edges from upstream
        for edge in capsule.upstream_edges:
            edges.append(LineageEdge(
                source_urn=edge.source_urn,
                target_urn=edge.target_urn,
                edge_type=edge.edge_type,
                transformation=edge.transformation,
            ))

    # Get downstream lineage
    if direction in ("downstream", "both"):
        downstream = await repo.get_downstream(capsule.id, depth=depth)
        for d in downstream:
            if d.urn not in seen_urns:
                seen_urns.add(d.urn)
                nodes.append(LineageNode(
                    id=str(d.id),
                    urn=d.urn,
                    name=d.name,
                    layer=d.layer,
                    capsule_type=d.capsule_type,
                    depth=1,
                    direction="downstream",
                ))

        # Add edges to downstream
        for edge in capsule.downstream_edges:
            edges.append(LineageEdge(
                source_urn=edge.source_urn,
                target_urn=edge.target_urn,
                edge_type=edge.edge_type,
                transformation=edge.transformation,
            ))

    root = CapsuleSummary(
        id=str(capsule.id),
        urn=capsule.urn,
        name=capsule.name,
        capsule_type=capsule.capsule_type,
        layer=capsule.layer,
        schema_name=capsule.schema_name,
        database_name=capsule.database_name,
        domain_name=capsule.domain.name if capsule.domain else None,
        description=capsule.description,
        column_count=capsule.column_count,
        has_pii=capsule.has_pii,
        has_tests=capsule.has_tests,
    )

    upstream_count = sum(1 for n in nodes if n.direction == "upstream")
    downstream_count = sum(1 for n in nodes if n.direction == "downstream")

    return LineageResponse(
        root=root,
        nodes=nodes,
        edges=edges,
        summary={
            "upstream_count": upstream_count,
            "downstream_count": downstream_count,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "depth_requested": depth,
        },
    )


@router.get("/{urn:path}/violations")
async def get_capsule_violations(
    urn: str,
    db: DbSession,
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
) -> dict:
    """Get violations for a capsule."""
    repo = CapsuleRepository(db)

    capsule = await repo.get_by_urn(urn)
    if not capsule:
        raise NotFoundError("Capsule", urn)

    # Get violations from capsule relationship
    violations = capsule.violations

    # Apply filters
    if severity:
        violations = [v for v in violations if v.severity == severity]
    if status:
        violations = [v for v in violations if v.status == status]
    if category:
        violations = [v for v in violations if v.rule and v.rule.category == category]

    data = [
        {
            "id": str(v.id),
            "rule_id": str(v.rule_id) if v.rule_id else None,
            "rule_name": v.rule.name if v.rule else None,
            "severity": v.severity,
            "status": v.status,
            "message": v.message,
            "details": v.details,
            "created_at": v.created_at.isoformat(),
        }
        for v in violations
    ]

    return {"data": data, "total": len(data)}
