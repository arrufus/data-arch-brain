"""Business term endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.api.exceptions import NotFoundError
from src.api.schemas.business_term import (
    BusinessTermApprovalRequest,
    BusinessTermCreate,
    BusinessTermDetail,
    BusinessTermListResponse,
    BusinessTermSummary,
    BusinessTermUpdate,
    CapsuleBusinessTermCreate,
    ColumnBusinessTermCreate,
)
from src.database import DbSession
from src.models import BusinessTerm, CapsuleBusinessTerm, ColumnBusinessTerm
from src.repositories import (
    BusinessTermRepository,
    CapsuleBusinessTermRepository,
    CapsuleRepository,
    ColumnBusinessTermRepository,
    ColumnRepository,
)

router = APIRouter(prefix="/business-terms", tags=["business-terms"])


@router.post("", response_model=BusinessTermDetail, status_code=status.HTTP_201_CREATED)
async def create_business_term(
    db: DbSession,
    term: BusinessTermCreate,
) -> BusinessTermDetail:
    """Create a new business term."""
    repo = BusinessTermRepository(db)

    # Check if term name already exists
    existing = await repo.get_by_name(term.term_name)
    if existing:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Business term '{term.term_name}' already exists"
        )

    # Create term
    new_term = BusinessTerm(
        term_name=term.term_name,
        display_name=term.display_name,
        definition=term.definition,
        abbreviation=term.abbreviation,
        synonyms=term.synonyms,
        domain_id=UUID(term.domain_id) if term.domain_id else None,
        category=term.category,
        owner_id=UUID(term.owner_id) if term.owner_id else None,
        steward_email=term.steward_email,
        approval_status="draft",
        tags=term.tags,
        meta=term.meta,
    )

    created = await repo.create(new_term)
    await db.commit()
    await db.refresh(created, ["domain", "owner"])

    return BusinessTermDetail(
        id=str(created.id),
        term_name=created.term_name,
        display_name=created.display_name,
        definition=created.definition,
        abbreviation=created.abbreviation,
        synonyms=created.synonyms,
        category=created.category,
        domain_id=str(created.domain_id) if created.domain_id else None,
        domain_name=created.domain.name if created.domain else None,
        owner_id=str(created.owner_id) if created.owner_id else None,
        owner_name=created.owner.name if created.owner else None,
        steward_email=created.steward_email,
        approval_status=created.approval_status,
        approved_by=created.approved_by,
        approved_at=created.approved_at.isoformat() if created.approved_at else None,
        tags=created.tags,
        meta=created.meta,
        created_at=created.created_at.isoformat(),
        updated_at=created.updated_at.isoformat(),
    )


@router.get("", response_model=BusinessTermListResponse)
async def list_business_terms(
    db: DbSession,
    search: Optional[str] = Query(None, description="Search term name or definition"),
    domain_id: Optional[str] = Query(None, description="Filter by domain"),
    category: Optional[str] = Query(None, description="Filter by category"),
    approval_status: Optional[str] = Query(None, description="Filter by approval status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> BusinessTermListResponse:
    """List business terms with optional filters."""
    repo = BusinessTermRepository(db)

    if search:
        terms = await repo.search(search, offset, limit)
    elif domain_id:
        terms = await repo.get_by_domain(UUID(domain_id), offset, limit)
    elif category:
        terms = await repo.get_by_category(category, offset, limit)
    elif approval_status:
        terms = await repo.get_by_status(approval_status, offset, limit)
    else:
        terms = await repo.get_all(offset, limit)

    total = await repo.count()

    data = []
    for term in terms:
        await db.refresh(term, ["domain", "owner"])
        data.append(BusinessTermSummary(
            id=str(term.id),
            term_name=term.term_name,
            display_name=term.display_name,
            definition=term.definition,
            abbreviation=term.abbreviation,
            category=term.category,
            approval_status=term.approval_status,
            domain_name=term.domain.name if term.domain else None,
            owner_name=term.owner.name if term.owner else None,
        ))

    return BusinessTermListResponse(
        data=data,
        pagination={
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": offset + limit < total,
        },
    )


@router.get("/categories", response_model=list[str])
async def list_categories(db: DbSession) -> list[str]:
    """Get all unique business term categories."""
    repo = BusinessTermRepository(db)
    categories = await repo.get_categories()
    return list(categories)


@router.get("/{term_id}", response_model=BusinessTermDetail)
async def get_business_term(
    db: DbSession,
    term_id: UUID,
) -> BusinessTermDetail:
    """Get business term by ID."""
    repo = BusinessTermRepository(db)
    term = await repo.get_by_id(term_id)

    if not term:
        raise NotFoundError("Business term", str(term_id))

    await db.refresh(term, ["domain", "owner"])

    return BusinessTermDetail(
        id=str(term.id),
        term_name=term.term_name,
        display_name=term.display_name,
        definition=term.definition,
        abbreviation=term.abbreviation,
        synonyms=term.synonyms,
        category=term.category,
        domain_id=str(term.domain_id) if term.domain_id else None,
        domain_name=term.domain.name if term.domain else None,
        owner_id=str(term.owner_id) if term.owner_id else None,
        owner_name=term.owner.name if term.owner else None,
        steward_email=term.steward_email,
        approval_status=term.approval_status,
        approved_by=term.approved_by,
        approved_at=term.approved_at.isoformat() if term.approved_at else None,
        tags=term.tags,
        meta=term.meta,
        created_at=term.created_at.isoformat(),
        updated_at=term.updated_at.isoformat(),
    )


@router.put("/{term_id}", response_model=BusinessTermDetail)
async def update_business_term(
    db: DbSession,
    term_id: UUID,
    updates: BusinessTermUpdate,
) -> BusinessTermDetail:
    """Update a business term."""
    repo = BusinessTermRepository(db)
    term = await repo.get_by_id(term_id)

    if not term:
        raise NotFoundError("Business term", str(term_id))

    # Apply updates
    if updates.display_name is not None:
        term.display_name = updates.display_name
    if updates.definition is not None:
        term.definition = updates.definition
    if updates.abbreviation is not None:
        term.abbreviation = updates.abbreviation
    if updates.synonyms is not None:
        term.synonyms = updates.synonyms
    if updates.category is not None:
        term.category = updates.category
    if updates.domain_id is not None:
        term.domain_id = UUID(updates.domain_id)
    if updates.owner_id is not None:
        term.owner_id = UUID(updates.owner_id)
    if updates.steward_email is not None:
        term.steward_email = updates.steward_email
    if updates.approval_status is not None:
        term.approval_status = updates.approval_status
    if updates.tags is not None:
        term.tags = updates.tags
    if updates.meta is not None:
        term.meta = updates.meta

    updated = await repo.update(term)
    await db.commit()
    await db.refresh(updated, ["domain", "owner"])

    return BusinessTermDetail(
        id=str(updated.id),
        term_name=updated.term_name,
        display_name=updated.display_name,
        definition=updated.definition,
        abbreviation=updated.abbreviation,
        synonyms=updated.synonyms,
        category=updated.category,
        domain_id=str(updated.domain_id) if updated.domain_id else None,
        domain_name=updated.domain.name if updated.domain else None,
        owner_id=str(updated.owner_id) if updated.owner_id else None,
        owner_name=updated.owner.name if updated.owner else None,
        steward_email=updated.steward_email,
        approval_status=updated.approval_status,
        approved_by=updated.approved_by,
        approved_at=updated.approved_at.isoformat() if updated.approved_at else None,
        tags=updated.tags,
        meta=updated.meta,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
    )


@router.delete("/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business_term(
    db: DbSession,
    term_id: UUID,
) -> None:
    """Delete a business term."""
    repo = BusinessTermRepository(db)
    deleted = await repo.delete_by_id(term_id)

    if not deleted:
        raise NotFoundError("Business term", str(term_id))

    await db.commit()


@router.post("/{term_id}/approve", response_model=BusinessTermDetail)
async def approve_business_term(
    db: DbSession,
    term_id: UUID,
    approval: BusinessTermApprovalRequest,
) -> BusinessTermDetail:
    """Approve or change approval status of a business term."""
    repo = BusinessTermRepository(db)
    term = await repo.get_by_id(term_id)

    if not term:
        raise NotFoundError("Business term", str(term_id))

    # Update approval
    term.approval_status = approval.approval_status
    term.approved_by = approval.approved_by
    term.approved_at = datetime.utcnow() if approval.approval_status == "approved" else None

    updated = await repo.update(term)
    await db.commit()
    await db.refresh(updated, ["domain", "owner"])

    return BusinessTermDetail(
        id=str(updated.id),
        term_name=updated.term_name,
        display_name=updated.display_name,
        definition=updated.definition,
        abbreviation=updated.abbreviation,
        synonyms=updated.synonyms,
        category=updated.category,
        domain_id=str(updated.domain_id) if updated.domain_id else None,
        domain_name=updated.domain.name if updated.domain else None,
        owner_id=str(updated.owner_id) if updated.owner_id else None,
        owner_name=updated.owner.name if updated.owner else None,
        steward_email=updated.steward_email,
        approval_status=updated.approval_status,
        approved_by=updated.approved_by,
        approved_at=updated.approved_at.isoformat() if updated.approved_at else None,
        tags=updated.tags,
        meta=updated.meta,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
    )


@router.post("/capsule-associations", status_code=status.HTTP_201_CREATED)
async def link_capsule_to_term(
    db: DbSession,
    association: CapsuleBusinessTermCreate,
) -> dict:
    """Link a capsule to a business term."""
    capsule_repo = CapsuleRepository(db)
    term_repo = BusinessTermRepository(db)
    assoc_repo = CapsuleBusinessTermRepository(db)

    # Verify capsule exists
    capsule = await capsule_repo.get_by_id(UUID(association.capsule_id))
    if not capsule:
        raise NotFoundError("Capsule", str(association.capsule_id))

    # Verify term exists
    term = await term_repo.get_by_id(UUID(association.business_term_id))
    if not term:
        raise NotFoundError("Business term", str(association.business_term_id))

    # Check if association already exists
    exists = await assoc_repo.exists_association(
        UUID(association.capsule_id),
        UUID(association.business_term_id)
    )
    if exists:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Association already exists"
        )

    # Create association
    new_assoc = CapsuleBusinessTerm(
        capsule_id=UUID(association.capsule_id),
        business_term_id=UUID(association.business_term_id),
        relationship_type=association.relationship_type,
        added_by=association.added_by,
        meta=association.meta,
    )

    created = await assoc_repo.create(new_assoc)
    await db.commit()

    return {
        "id": str(created.id),
        "capsule_id": str(created.capsule_id),
        "business_term_id": str(created.business_term_id),
        "relationship_type": created.relationship_type,
        "added_by": created.added_by,
        "added_at": created.added_at.isoformat(),
    }


@router.post("/column-associations", status_code=status.HTTP_201_CREATED)
async def link_column_to_term(
    db: DbSession,
    association: ColumnBusinessTermCreate,
) -> dict:
    """Link a column to a business term."""
    column_repo = ColumnRepository(db)
    term_repo = BusinessTermRepository(db)
    assoc_repo = ColumnBusinessTermRepository(db)

    # Verify column exists
    column = await column_repo.get_by_id(UUID(association.column_id))
    if not column:
        raise NotFoundError("Column", str(association.column_id))

    # Verify term exists
    term = await term_repo.get_by_id(UUID(association.business_term_id))
    if not term:
        raise NotFoundError("Business term", str(association.business_term_id))

    # Check if association already exists
    exists = await assoc_repo.exists_association(
        UUID(association.column_id),
        UUID(association.business_term_id)
    )
    if exists:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Association already exists"
        )

    # Create association
    new_assoc = ColumnBusinessTerm(
        column_id=UUID(association.column_id),
        business_term_id=UUID(association.business_term_id),
        relationship_type=association.relationship_type,
        added_by=association.added_by,
        meta=association.meta,
    )

    created = await assoc_repo.create(new_assoc)
    await db.commit()

    return {
        "id": str(created.id),
        "column_id": str(created.column_id),
        "business_term_id": str(created.business_term_id),
        "relationship_type": created.relationship_type,
        "added_by": created.added_by,
        "added_at": created.added_at.isoformat(),
    }
