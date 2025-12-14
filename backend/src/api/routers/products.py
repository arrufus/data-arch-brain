"""Data Products API endpoints.

This module provides REST endpoints for managing data products
and their capsule associations (PART_OF edges).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.api.exceptions import ConflictError, NotFoundError
from src.database import DbSession
from src.models.data_product import CapsuleRole, DataProduct, DataProductStatus
from src.repositories.capsule import CapsuleRepository
from src.repositories.data_product import (
    CapsuleDataProductRepository,
    DataProductRepository,
)
from src.services.slo import SLOService, SLOStatus

router = APIRouter(prefix="/products")


# ============================================================================
# Pydantic Models
# ============================================================================


class DataProductSummary(BaseModel):
    """Summary view of a data product."""

    id: str
    name: str
    description: Optional[str] = None
    status: str
    version: Optional[str] = None
    domain_name: Optional[str] = None
    owner_name: Optional[str] = None
    capsule_count: int = 0
    created_at: str
    updated_at: str


class SLODefinition(BaseModel):
    """SLO configuration for a data product."""

    freshness_hours: Optional[int] = Field(
        None, description="Max hours since last data update"
    )
    availability_percent: Optional[float] = Field(
        None, ge=0, le=100, description="Target availability percentage"
    )
    quality_threshold: Optional[float] = Field(
        None, ge=0, le=1, description="Min conformance score (0.0 to 1.0)"
    )


class CapsuleAssociation(BaseModel):
    """Capsule association within a data product."""

    capsule_id: str
    capsule_urn: str
    capsule_name: str
    role: str
    added_at: str


class DataProductDetail(DataProductSummary):
    """Detailed view of a data product."""

    domain_id: Optional[str] = None
    owner_id: Optional[str] = None
    slo: SLODefinition
    output_port_schema: dict = {}
    input_sources: list = []
    capsules: list[CapsuleAssociation] = []
    meta: dict = {}
    tags: list[str] = []


class CreateDataProduct(BaseModel):
    """Request body for creating a data product."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    version: Optional[str] = Field(None, max_length=50)
    status: str = Field(default="draft")
    domain_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    slo: Optional[SLODefinition] = None
    output_port_schema: dict = Field(default_factory=dict)
    input_sources: list = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class UpdateDataProduct(BaseModel):
    """Request body for updating a data product."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    version: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = None
    domain_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    slo: Optional[SLODefinition] = None
    output_port_schema: Optional[dict] = None
    input_sources: Optional[list] = None
    meta: Optional[dict] = None
    tags: Optional[list[str]] = None


class AddCapsuleRequest(BaseModel):
    """Request body for adding a capsule to a data product."""

    capsule_urn: str = Field(..., description="URN of the capsule to add")
    role: str = Field(default="member", description="Role: member, output, or input")


class UpdateCapsuleRoleRequest(BaseModel):
    """Request body for updating a capsule's role."""

    role: str = Field(..., description="New role: member, output, or input")


class DataProductListResponse(BaseModel):
    """Response for data product list."""

    data: list[DataProductSummary]
    pagination: dict


class SLOStatusResponse(BaseModel):
    """SLO compliance status response."""

    data_product_id: str
    data_product_name: str
    overall_status: str  # passing, warning, failing
    checked_at: str
    freshness: Optional[dict] = None
    availability: Optional[dict] = None
    quality: Optional[dict] = None


# ============================================================================
# Helper Functions
# ============================================================================


def _to_summary(product: DataProduct) -> DataProductSummary:
    """Convert DataProduct to summary response."""
    return DataProductSummary(
        id=str(product.id),
        name=product.name,
        description=product.description,
        status=product.status,
        version=product.version,
        domain_name=product.domain.name if product.domain else None,
        owner_name=product.owner.name if product.owner else None,
        capsule_count=len(product.capsule_associations),
        created_at=product.created_at.isoformat(),
        updated_at=product.updated_at.isoformat(),
    )


def _to_detail(product: DataProduct) -> DataProductDetail:
    """Convert DataProduct to detailed response."""
    capsules = [
        CapsuleAssociation(
            capsule_id=str(assoc.capsule.id),
            capsule_urn=assoc.capsule.urn,
            capsule_name=assoc.capsule.name,
            role=assoc.role,
            added_at=assoc.created_at.isoformat(),
        )
        for assoc in product.capsule_associations
    ]

    return DataProductDetail(
        id=str(product.id),
        name=product.name,
        description=product.description,
        status=product.status,
        version=product.version,
        domain_name=product.domain.name if product.domain else None,
        owner_name=product.owner.name if product.owner else None,
        domain_id=str(product.domain_id) if product.domain_id else None,
        owner_id=str(product.owner_id) if product.owner_id else None,
        slo=SLODefinition(
            freshness_hours=product.slo_freshness_hours,
            availability_percent=product.slo_availability_percent,
            quality_threshold=product.slo_quality_threshold,
        ),
        output_port_schema=product.output_port_schema or {},
        input_sources=product.input_sources or [],
        capsules=capsules,
        capsule_count=len(capsules),
        meta=product.meta or {},
        tags=product.tags or [],
        created_at=product.created_at.isoformat(),
        updated_at=product.updated_at.isoformat(),
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=DataProductListResponse)
async def list_products(
    db: DbSession,
    search: Optional[str] = Query(None, description="Search by name or description"),
    status: Optional[str] = Query(None, description="Filter by status"),
    domain_id: Optional[UUID] = Query(None, description="Filter by domain"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> DataProductListResponse:
    """List all data products with optional filtering."""
    repo = DataProductRepository(db)

    if search:
        products = await repo.search(query=search, offset=offset, limit=limit)
    else:
        products = await repo.get_all_with_relations(
            offset=offset, limit=limit, status=status, domain_id=domain_id
        )

    total = await repo.count()

    return DataProductListResponse(
        data=[_to_summary(p) for p in products],
        pagination={
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + len(products) < total,
        },
    )


@router.get("/stats")
async def get_product_stats(db: DbSession) -> dict:
    """Get aggregated statistics about data products."""
    repo = DataProductRepository(db)

    total = await repo.count()
    all_products = await repo.get_all_with_relations(limit=10000)

    # Count by status
    status_counts = {}
    for p in all_products:
        status_counts[p.status] = status_counts.get(p.status, 0) + 1

    # Count total capsules
    total_capsules = sum(len(p.capsule_associations) for p in all_products)

    return {
        "total_products": total,
        "by_status": status_counts,
        "total_capsule_associations": total_capsules,
        "avg_capsules_per_product": (
            total_capsules / total if total > 0 else 0
        ),
    }


@router.get("/{id}", response_model=DataProductDetail)
async def get_product(id: UUID, db: DbSession) -> DataProductDetail:
    """Get data product details by ID."""
    repo = DataProductRepository(db)
    product = await repo.get_by_id_with_capsules(id)

    if not product:
        raise NotFoundError("DataProduct", str(id))

    return _to_detail(product)


@router.post("", response_model=DataProductDetail, status_code=201)
async def create_product(
    data: CreateDataProduct,
    db: DbSession,
) -> DataProductDetail:
    """Create a new data product."""
    repo = DataProductRepository(db)

    # Check for duplicate name
    existing = await repo.get_by_name(data.name)
    if existing:
        raise ConflictError(f"Data product with name '{data.name}' already exists")

    product = DataProduct(
        name=data.name,
        description=data.description,
        version=data.version,
        status=data.status,
        domain_id=data.domain_id,
        owner_id=data.owner_id,
        slo_freshness_hours=data.slo.freshness_hours if data.slo else None,
        slo_availability_percent=data.slo.availability_percent if data.slo else None,
        slo_quality_threshold=data.slo.quality_threshold if data.slo else None,
        output_port_schema=data.output_port_schema,
        input_sources=data.input_sources,
        meta=data.meta,
        tags=data.tags,
    )

    created = await repo.create(product)

    # Reload with relationships
    loaded_product = await repo.get_by_id_with_capsules(created.id)
    if not loaded_product:
        raise NotFoundError("DataProduct", str(created.id))
    return _to_detail(loaded_product)


@router.put("/{id}", response_model=DataProductDetail)
async def update_product(
    id: UUID,
    data: UpdateDataProduct,
    db: DbSession,
) -> DataProductDetail:
    """Update a data product."""
    repo = DataProductRepository(db)
    product = await repo.get_by_id_with_capsules(id)

    if not product:
        raise NotFoundError("DataProduct", str(id))

    # Check for name conflict if updating name
    if data.name and data.name != product.name:
        existing = await repo.get_by_name(data.name)
        if existing:
            raise ConflictError(f"Data product with name '{data.name}' already exists")

    # Update fields
    if data.name is not None:
        product.name = data.name
    if data.description is not None:
        product.description = data.description
    if data.version is not None:
        product.version = data.version
    if data.status is not None:
        product.status = data.status
    if data.domain_id is not None:
        product.domain_id = data.domain_id
    if data.owner_id is not None:
        product.owner_id = data.owner_id
    if data.slo is not None:
        product.slo_freshness_hours = data.slo.freshness_hours
        product.slo_availability_percent = data.slo.availability_percent
        product.slo_quality_threshold = data.slo.quality_threshold
    if data.output_port_schema is not None:
        product.output_port_schema = data.output_port_schema
    if data.input_sources is not None:
        product.input_sources = data.input_sources
    if data.meta is not None:
        product.meta = data.meta
    if data.tags is not None:
        product.tags = data.tags

    await repo.update(product)

    # Reload with relationships
    updated_product = await repo.get_by_id_with_capsules(id)
    if not updated_product:
        raise NotFoundError("DataProduct", str(id))
    return _to_detail(updated_product)


@router.delete("/{id}", status_code=204)
async def delete_product(id: UUID, db: DbSession) -> None:
    """Delete a data product."""
    repo = DataProductRepository(db)
    product = await repo.get_by_id(id)

    if not product:
        raise NotFoundError("DataProduct", str(id))

    await repo.delete(product)


# ============================================================================
# Capsule Association Endpoints (PART_OF edges)
# ============================================================================


@router.post("/{id}/capsules", response_model=CapsuleAssociation, status_code=201)
async def add_capsule_to_product(
    id: UUID,
    data: AddCapsuleRequest,
    db: DbSession,
) -> CapsuleAssociation:
    """Add a capsule to a data product (create PART_OF edge)."""
    product_repo = DataProductRepository(db)
    capsule_repo = CapsuleRepository(db)
    assoc_repo = CapsuleDataProductRepository(db)

    # Verify product exists
    product = await product_repo.get_by_id(id)
    if not product:
        raise NotFoundError("DataProduct", str(id))

    # Find capsule by URN
    capsule = await capsule_repo.get_by_urn(data.capsule_urn)
    if not capsule:
        raise NotFoundError("Capsule", data.capsule_urn)

    # Check if association already exists
    existing = await assoc_repo.get_association(capsule.id, id)
    if existing:
        raise ConflictError(
            f"Capsule '{data.capsule_urn}' is already part of this data product"
        )

    # Validate role
    valid_roles = [r.value for r in CapsuleRole]
    if data.role not in valid_roles:
        raise ValueError(f"Invalid role. Must be one of: {valid_roles}")

    # Create association
    association = await assoc_repo.add_capsule_to_product(
        capsule_id=capsule.id,
        data_product_id=id,
        role=data.role,
    )

    return CapsuleAssociation(
        capsule_id=str(capsule.id),
        capsule_urn=capsule.urn,
        capsule_name=capsule.name,
        role=association.role,
        added_at=association.created_at.isoformat(),
    )


@router.get("/{id}/capsules", response_model=list[CapsuleAssociation])
async def list_product_capsules(
    id: UUID,
    db: DbSession,
    role: Optional[str] = Query(None, description="Filter by role"),
) -> list[CapsuleAssociation]:
    """List all capsules in a data product."""
    product_repo = DataProductRepository(db)
    assoc_repo = CapsuleDataProductRepository(db)

    # Verify product exists
    product = await product_repo.get_by_id(id)
    if not product:
        raise NotFoundError("DataProduct", str(id))

    associations = await assoc_repo.get_capsules_in_product(id, role=role)

    return [
        CapsuleAssociation(
            capsule_id=str(assoc.capsule.id),
            capsule_urn=assoc.capsule.urn,
            capsule_name=assoc.capsule.name,
            role=assoc.role,
            added_at=assoc.created_at.isoformat(),
        )
        for assoc in associations
    ]


@router.put("/{id}/capsules/{capsule_id}", response_model=CapsuleAssociation)
async def update_capsule_role_in_product(
    id: UUID,
    capsule_id: UUID,
    data: UpdateCapsuleRoleRequest,
    db: DbSession,
) -> CapsuleAssociation:
    """Update a capsule's role in a data product."""
    product_repo = DataProductRepository(db)
    capsule_repo = CapsuleRepository(db)
    assoc_repo = CapsuleDataProductRepository(db)

    # Verify product exists
    product = await product_repo.get_by_id(id)
    if not product:
        raise NotFoundError("DataProduct", str(id))

    # Verify capsule exists
    capsule = await capsule_repo.get_by_id(capsule_id)
    if not capsule:
        raise NotFoundError("Capsule", str(capsule_id))

    # Validate role
    valid_roles = [r.value for r in CapsuleRole]
    if data.role not in valid_roles:
        raise ValueError(f"Invalid role. Must be one of: {valid_roles}")

    # Update role
    association = await assoc_repo.update_capsule_role(capsule_id, id, data.role)
    if not association:
        raise NotFoundError(
            "CapsuleDataProduct",
            f"capsule {capsule_id} in product {id}",
        )

    return CapsuleAssociation(
        capsule_id=str(capsule.id),
        capsule_urn=capsule.urn,
        capsule_name=capsule.name,
        role=association.role,
        added_at=association.created_at.isoformat(),
    )


@router.delete("/{id}/capsules/{capsule_id}", status_code=204)
async def remove_capsule_from_product(
    id: UUID,
    capsule_id: UUID,
    db: DbSession,
) -> None:
    """Remove a capsule from a data product (delete PART_OF edge)."""
    product_repo = DataProductRepository(db)
    assoc_repo = CapsuleDataProductRepository(db)

    # Verify product exists
    product = await product_repo.get_by_id(id)
    if not product:
        raise NotFoundError("DataProduct", str(id))

    # Remove association
    removed = await assoc_repo.remove_capsule_from_product(capsule_id, id)
    if not removed:
        raise NotFoundError(
            "CapsuleDataProduct",
            f"capsule {capsule_id} in product {id}",
        )


# ============================================================================
# SLO Status Endpoint
# ============================================================================


@router.get("/{id}/slo-status", response_model=SLOStatusResponse)
async def get_slo_status(id: UUID, db: DbSession) -> SLOStatusResponse:
    """Check SLO compliance for a data product."""
    product_repo = DataProductRepository(db)
    product = await product_repo.get_by_id_with_capsules(id)

    if not product:
        raise NotFoundError("DataProduct", str(id))

    slo_service = SLOService(db)
    status = await slo_service.check_slo_status(product)

    return SLOStatusResponse(
        data_product_id=str(product.id),
        data_product_name=product.name,
        overall_status=status.overall_status.value,
        checked_at=status.checked_at.isoformat(),
        freshness=status.freshness,
        availability=status.availability,
        quality=status.quality,
    )
