"""Value domain endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.api.exceptions import NotFoundError
from src.api.schemas.value_domain import (
    ValueDomainCreate,
    ValueDomainDetail,
    ValueDomainListResponse,
    ValueDomainSummary,
    ValueDomainUpdate,
    ValueValidationRequest,
    ValueValidationResponse,
)
from src.database import DbSession
from src.models import ValueDomain
from src.repositories import ValueDomainRepository

router = APIRouter(prefix="/value-domains", tags=["value-domains"])


@router.post("", response_model=ValueDomainDetail, status_code=status.HTTP_201_CREATED)
async def create_value_domain(
    db: DbSession,
    domain: ValueDomainCreate,
) -> ValueDomainDetail:
    """Create a new value domain."""
    repo = ValueDomainRepository(db)

    # Check if domain name already exists
    existing = await repo.get_by_name(domain.domain_name)
    if existing:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Value domain '{domain.domain_name}' already exists"
        )

    # Create domain
    new_domain = ValueDomain(
        domain_name=domain.domain_name,
        domain_type=domain.domain_type,
        description=domain.description,
        allowed_values=domain.allowed_values,
        pattern_regex=domain.pattern_regex,
        pattern_description=domain.pattern_description,
        min_value=domain.min_value,
        max_value=domain.max_value,
        reference_table_urn=domain.reference_table_urn,
        reference_column_urn=domain.reference_column_urn,
        is_extensible=domain.is_extensible,
        owner_id=UUID(domain.owner_id) if domain.owner_id else None,
        meta=domain.meta,
    )

    created = await repo.create(new_domain)
    await db.commit()
    await db.refresh(created, ["owner"])

    return ValueDomainDetail(
        id=str(created.id),
        domain_name=created.domain_name,
        domain_type=created.domain_type,
        description=created.description,
        allowed_values=created.allowed_values,
        pattern_regex=created.pattern_regex,
        pattern_description=created.pattern_description,
        min_value=created.min_value,
        max_value=created.max_value,
        reference_table_urn=created.reference_table_urn,
        reference_column_urn=created.reference_column_urn,
        is_extensible=created.is_extensible,
        owner_id=str(created.owner_id) if created.owner_id else None,
        owner_name=created.owner.name if created.owner else None,
        meta=created.meta,
        created_at=created.created_at.isoformat(),
        updated_at=created.updated_at.isoformat(),
    )


@router.get("", response_model=ValueDomainListResponse)
async def list_value_domains(
    db: DbSession,
    search: Optional[str] = Query(None, description="Search domain name or description"),
    domain_type: Optional[str] = Query(None, description="Filter by domain type"),
    owner_id: Optional[str] = Query(None, description="Filter by owner"),
    is_extensible: Optional[bool] = Query(None, description="Filter by extensibility"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> ValueDomainListResponse:
    """List value domains with optional filters."""
    repo = ValueDomainRepository(db)

    if search:
        domains = await repo.search(search, offset, limit)
    elif domain_type:
        domains = await repo.get_by_type(domain_type, offset, limit)
    elif owner_id:
        domains = await repo.get_by_owner(UUID(owner_id), offset, limit)
    elif is_extensible is not None:
        if is_extensible:
            domains = await repo.get_extensible_domains(offset, limit)
        else:
            # Get all domains and filter out extensible ones
            all_domains = await repo.get_all(offset, limit)
            domains = [d for d in all_domains if not d.is_extensible]
    else:
        domains = await repo.get_all(offset, limit)

    total = await repo.count()

    data = []
    for domain in domains:
        await db.refresh(domain, ["owner"])
        value_count = len(domain.allowed_values) if domain.allowed_values else 0
        data.append(ValueDomainSummary(
            id=str(domain.id),
            domain_name=domain.domain_name,
            domain_type=domain.domain_type,
            description=domain.description,
            is_extensible=domain.is_extensible,
            owner_name=domain.owner.name if domain.owner else None,
            value_count=value_count,
        ))

    return ValueDomainListResponse(
        data=data,
        pagination={
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": offset + limit < total,
        },
    )


@router.get("/{domain_id}", response_model=ValueDomainDetail)
async def get_value_domain(
    db: DbSession,
    domain_id: UUID,
) -> ValueDomainDetail:
    """Get value domain by ID."""
    repo = ValueDomainRepository(db)
    domain = await repo.get_by_id(domain_id)

    if not domain:
        raise NotFoundError("Value domain", str(domain_id))

    await db.refresh(domain, ["owner"])

    return ValueDomainDetail(
        id=str(domain.id),
        domain_name=domain.domain_name,
        domain_type=domain.domain_type,
        description=domain.description,
        allowed_values=domain.allowed_values,
        pattern_regex=domain.pattern_regex,
        pattern_description=domain.pattern_description,
        min_value=domain.min_value,
        max_value=domain.max_value,
        reference_table_urn=domain.reference_table_urn,
        reference_column_urn=domain.reference_column_urn,
        is_extensible=domain.is_extensible,
        owner_id=str(domain.owner_id) if domain.owner_id else None,
        owner_name=domain.owner.name if domain.owner else None,
        meta=domain.meta,
        created_at=domain.created_at.isoformat(),
        updated_at=domain.updated_at.isoformat(),
    )


@router.put("/{domain_id}", response_model=ValueDomainDetail)
async def update_value_domain(
    db: DbSession,
    domain_id: UUID,
    updates: ValueDomainUpdate,
) -> ValueDomainDetail:
    """Update a value domain."""
    repo = ValueDomainRepository(db)
    domain = await repo.get_by_id(domain_id)

    if not domain:
        raise NotFoundError("Value domain", str(domain_id))

    # Apply updates
    if updates.description is not None:
        domain.description = updates.description
    if updates.allowed_values is not None:
        domain.allowed_values = updates.allowed_values
    if updates.pattern_regex is not None:
        domain.pattern_regex = updates.pattern_regex
    if updates.pattern_description is not None:
        domain.pattern_description = updates.pattern_description
    if updates.min_value is not None:
        domain.min_value = updates.min_value
    if updates.max_value is not None:
        domain.max_value = updates.max_value
    if updates.reference_table_urn is not None:
        domain.reference_table_urn = updates.reference_table_urn
    if updates.reference_column_urn is not None:
        domain.reference_column_urn = updates.reference_column_urn
    if updates.owner_id is not None:
        domain.owner_id = UUID(updates.owner_id)
    if updates.is_extensible is not None:
        domain.is_extensible = updates.is_extensible
    if updates.meta is not None:
        domain.meta = updates.meta

    updated = await repo.update(domain)
    await db.commit()
    await db.refresh(updated, ["owner"])

    return ValueDomainDetail(
        id=str(updated.id),
        domain_name=updated.domain_name,
        domain_type=updated.domain_type,
        description=updated.description,
        allowed_values=updated.allowed_values,
        pattern_regex=updated.pattern_regex,
        pattern_description=updated.pattern_description,
        min_value=updated.min_value,
        max_value=updated.max_value,
        reference_table_urn=updated.reference_table_urn,
        reference_column_urn=updated.reference_column_urn,
        is_extensible=updated.is_extensible,
        owner_id=str(updated.owner_id) if updated.owner_id else None,
        owner_name=updated.owner.name if updated.owner else None,
        meta=updated.meta,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
    )


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_value_domain(
    db: DbSession,
    domain_id: UUID,
) -> None:
    """Delete a value domain."""
    repo = ValueDomainRepository(db)
    deleted = await repo.delete_by_id(domain_id)

    if not deleted:
        raise NotFoundError("Value domain", str(domain_id))

    await db.commit()


@router.post("/{domain_id}/validate", response_model=ValueValidationResponse)
async def validate_value(
    db: DbSession,
    domain_id: UUID,
    request: ValueValidationRequest,
) -> ValueValidationResponse:
    """Validate a value against a domain."""
    repo = ValueDomainRepository(db)
    domain = await repo.get_by_id(domain_id)

    if not domain:
        raise NotFoundError("Value domain", str(domain_id))

    # Perform validation using the model's validate_value method
    is_valid = domain.validate_value(request.value)

    message = None
    if not is_valid:
        if domain.domain_type == "enum":
            message = f"Value '{request.value}' not in allowed values"
        elif domain.domain_type == "pattern":
            message = f"Value '{request.value}' does not match pattern: {domain.pattern_regex}"
        elif domain.domain_type == "range":
            message = f"Value '{request.value}' outside range [{domain.min_value}, {domain.max_value}]"
        else:
            message = f"Value '{request.value}' is invalid for domain type '{domain.domain_type}'"

    return ValueValidationResponse(
        valid=is_valid,
        message=message,
        domain_name=domain.domain_name,
        domain_type=domain.domain_type,
    )
