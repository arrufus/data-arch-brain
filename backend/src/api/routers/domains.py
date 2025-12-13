"""Domain and ownership endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.api.exceptions import NotFoundError
from src.database import DbSession
from src.repositories import CapsuleRepository
from src.repositories.domain import DomainRepository, OwnerRepository

router = APIRouter(prefix="/domains")


class DomainSummary(BaseModel):
    """Summary view of a domain."""

    id: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    owner_name: Optional[str] = None
    capsule_count: int = 0


class DomainDetail(DomainSummary):
    """Detailed view of a domain."""

    owner_id: Optional[str] = None
    owner_email: Optional[str] = None
    child_domains: list[str] = []
    meta: dict = {}
    created_at: str
    updated_at: str


class DomainListResponse(BaseModel):
    """Response for domain list."""

    data: list[DomainSummary]
    pagination: dict


class CapsuleSummary(BaseModel):
    """Summary view of a capsule."""

    id: str
    urn: str
    name: str
    capsule_type: str
    layer: Optional[str] = None
    has_pii: bool = False


class DomainCapsuleListResponse(BaseModel):
    """Response for capsules in a domain."""

    domain: DomainSummary
    capsules: list[CapsuleSummary]
    pagination: dict


@router.get("", response_model=DomainListResponse)
async def list_domains(
    db: DbSession,
    search: Optional[str] = Query(None, description="Search by name or description"),
    root_only: bool = Query(False, description="Only return root-level domains"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> DomainListResponse:
    """List all domains."""
    repo = DomainRepository(db)
    capsule_repo = CapsuleRepository(db)

    if search:
        domains = await repo.search(query=search, offset=offset, limit=limit)
    elif root_only:
        domains = await repo.get_root_domains()
    else:
        domains = await repo.get_all(offset=offset, limit=limit)

    data = []
    for d in domains:
        # Get capsule count for each domain
        capsules = await capsule_repo.get_by_domain(d.id, limit=1)
        capsule_count = len(await capsule_repo.get_by_domain(d.id, limit=10000))

        data.append(DomainSummary(
            id=str(d.id),
            name=d.name,
            description=d.description,
            parent_id=str(d.parent_id) if d.parent_id else None,
            owner_name=d.owner.name if d.owner else None,
            capsule_count=capsule_count,
        ))

    total = await repo.count()

    return DomainListResponse(
        data=data,
        pagination={
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + len(data) < total,
        },
    )


@router.get("/stats")
async def get_domain_stats(db: DbSession) -> dict:
    """Get aggregated statistics about domains."""
    repo = DomainRepository(db)
    capsule_repo = CapsuleRepository(db)

    total_domains = await repo.count()
    root_domains = await repo.get_root_domains()

    # Get capsule distribution by domain
    all_domains = await repo.get_all(limit=1000)
    domain_capsule_counts = {}
    for d in all_domains:
        capsules = await capsule_repo.get_by_domain(d.id, limit=10000)
        domain_capsule_counts[d.name] = len(capsules)

    return {
        "total_domains": total_domains,
        "root_domains": len(root_domains),
        "capsules_by_domain": domain_capsule_counts,
    }


@router.get("/{name}", response_model=DomainDetail)
async def get_domain(
    name: str,
    db: DbSession,
) -> DomainDetail:
    """Get domain details by name."""
    repo = DomainRepository(db)
    capsule_repo = CapsuleRepository(db)

    domain = await repo.get_by_name(name)
    if not domain:
        raise NotFoundError("Domain", name)

    # Get child domains
    children = await repo.get_children(domain.id)
    child_names = [c.name for c in children]

    # Get capsule count
    capsules = await capsule_repo.get_by_domain(domain.id, limit=10000)
    capsule_count = len(capsules)

    return DomainDetail(
        id=str(domain.id),
        name=domain.name,
        description=domain.description,
        parent_id=str(domain.parent_id) if domain.parent_id else None,
        owner_name=domain.owner.name if domain.owner else None,
        owner_id=str(domain.owner_id) if domain.owner_id else None,
        owner_email=domain.owner.email if domain.owner else None,
        child_domains=child_names,
        capsule_count=capsule_count,
        meta=domain.meta or {},
        created_at=domain.created_at.isoformat(),
        updated_at=domain.updated_at.isoformat(),
    )


@router.get("/{name}/capsules", response_model=DomainCapsuleListResponse)
async def get_domain_capsules(
    name: str,
    db: DbSession,
    capsule_type: Optional[str] = Query(None, description="Filter by capsule type"),
    layer: Optional[str] = Query(None, description="Filter by layer"),
    has_pii: Optional[bool] = Query(None, description="Filter by PII presence"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> DomainCapsuleListResponse:
    """Get capsules belonging to a domain."""
    repo = DomainRepository(db)
    capsule_repo = CapsuleRepository(db)

    domain = await repo.get_by_name(name)
    if not domain:
        raise NotFoundError("Domain", name)

    # Get capsules for domain
    capsules = await capsule_repo.get_by_domain(
        domain_id=domain.id,
        offset=offset,
        limit=limit,
    )

    # Apply additional filters
    filtered_capsules = capsules
    if capsule_type:
        filtered_capsules = [c for c in filtered_capsules if c.capsule_type == capsule_type]
    if layer:
        filtered_capsules = [c for c in filtered_capsules if c.layer == layer]
    if has_pii is not None:
        filtered_capsules = [c for c in filtered_capsules if c.has_pii == has_pii]

    domain_summary = DomainSummary(
        id=str(domain.id),
        name=domain.name,
        description=domain.description,
        parent_id=str(domain.parent_id) if domain.parent_id else None,
        owner_name=domain.owner.name if domain.owner else None,
        capsule_count=len(capsules),
    )

    capsule_summaries = [
        CapsuleSummary(
            id=str(c.id),
            urn=c.urn,
            name=c.name,
            capsule_type=c.capsule_type,
            layer=c.layer,
            has_pii=c.has_pii,
        )
        for c in filtered_capsules
    ]

    return DomainCapsuleListResponse(
        domain=domain_summary,
        capsules=capsule_summaries,
        pagination={
            "total": len(filtered_capsules),
            "offset": offset,
            "limit": limit,
            "has_more": len(capsules) >= limit,
        },
    )


@router.get("/{name}/children", response_model=DomainListResponse)
async def get_domain_children(
    name: str,
    db: DbSession,
) -> DomainListResponse:
    """Get child domains of a domain."""
    repo = DomainRepository(db)
    capsule_repo = CapsuleRepository(db)

    domain = await repo.get_by_name(name)
    if not domain:
        raise NotFoundError("Domain", name)

    children = await repo.get_children(domain.id)

    data = []
    for d in children:
        capsules = await capsule_repo.get_by_domain(d.id, limit=10000)
        data.append(DomainSummary(
            id=str(d.id),
            name=d.name,
            description=d.description,
            parent_id=str(d.parent_id) if d.parent_id else None,
            owner_name=d.owner.name if d.owner else None,
            capsule_count=len(capsules),
        ))

    return DomainListResponse(
        data=data,
        pagination={
            "total": len(data),
            "offset": 0,
            "limit": len(data),
            "has_more": False,
        },
    )
