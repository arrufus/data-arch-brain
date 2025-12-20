"""Capsule index endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.api.exceptions import NotFoundError
from src.api.schemas.index import (
    CapsuleIndexCreate,
    CapsuleIndexDetail,
    CapsuleIndexListResponse,
    CapsuleIndexSummary,
    CapsuleIndexUpdate,
)
from src.database import DbSession
from src.models import CapsuleIndex
from src.repositories import CapsuleIndexRepository, CapsuleRepository

router = APIRouter(prefix="/indexes", tags=["indexes"])


@router.post("", response_model=CapsuleIndexDetail, status_code=status.HTTP_201_CREATED)
async def create_index(
    db: DbSession,
    index: CapsuleIndexCreate,
) -> CapsuleIndexDetail:
    """Create a new capsule index."""
    capsule_repo = CapsuleRepository(db)
    index_repo = CapsuleIndexRepository(db)

    # Verify capsule exists
    capsule = await capsule_repo.get_by_id(UUID(index.capsule_id))
    if not capsule:
        raise NotFoundError("Capsule", str(index.capsule_id))

    # Create index
    new_index = CapsuleIndex(
        capsule_id=UUID(index.capsule_id),
        index_name=index.index_name,
        index_type=index.index_type,
        is_unique=index.is_unique,
        is_primary=index.is_primary,
        column_names=index.column_names,
        column_expressions=index.column_expressions,
        is_partial=index.is_partial,
        partial_predicate=index.partial_predicate,
        tablespace=index.tablespace,
        fill_factor=index.fill_factor,
        meta=index.meta,
    )

    created = await index_repo.create(new_index)
    await db.commit()

    return CapsuleIndexDetail(
        id=str(created.id),
        capsule_id=str(created.capsule_id),
        index_name=created.index_name,
        index_type=created.index_type,
        is_unique=created.is_unique,
        is_primary=created.is_primary,
        column_names=created.column_names,
        column_expressions=created.column_expressions,
        is_partial=created.is_partial,
        partial_predicate=created.partial_predicate,
        tablespace=created.tablespace,
        fill_factor=created.fill_factor,
        meta=created.meta,
        created_at=created.created_at.isoformat(),
        updated_at=created.updated_at.isoformat(),
    )


@router.get("", response_model=CapsuleIndexListResponse)
async def list_indexes(
    db: DbSession,
    capsule_id: Optional[str] = Query(None, description="Filter by capsule ID"),
    index_type: Optional[str] = Query(None, description="Filter by index type"),
    unique_only: bool = Query(False, description="Only return unique indexes"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> CapsuleIndexListResponse:
    """List capsule indexes with optional filters."""
    repo = CapsuleIndexRepository(db)

    if capsule_id:
        if unique_only:
            indexes = await repo.get_unique_indexes(UUID(capsule_id))
            indexes = indexes[offset:offset + limit]
            total = len(indexes)
        else:
            indexes = await repo.get_by_capsule(UUID(capsule_id), offset, limit)
            total = await repo.count_by_capsule(UUID(capsule_id))
    elif index_type:
        indexes = await repo.get_by_type(index_type, offset, limit)
        total = await repo.count()
    else:
        indexes = await repo.get_all(offset, limit)
        total = await repo.count()

    data = [
        CapsuleIndexSummary(
            id=str(idx.id),
            capsule_id=str(idx.capsule_id),
            index_name=idx.index_name,
            index_type=idx.index_type,
            is_unique=idx.is_unique,
            is_primary=idx.is_primary,
            column_names=idx.column_names,
        )
        for idx in indexes
    ]

    return CapsuleIndexListResponse(
        data=data,
        pagination={
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": offset + limit < total,
        },
    )


@router.get("/{index_id}", response_model=CapsuleIndexDetail)
async def get_index(
    db: DbSession,
    index_id: UUID,
) -> CapsuleIndexDetail:
    """Get index by ID."""
    repo = CapsuleIndexRepository(db)
    index = await repo.get_by_id(index_id)

    if not index:
        raise NotFoundError("Index", str(index_id))

    return CapsuleIndexDetail(
        id=str(index.id),
        capsule_id=str(index.capsule_id),
        index_name=index.index_name,
        index_type=index.index_type,
        is_unique=index.is_unique,
        is_primary=index.is_primary,
        column_names=index.column_names,
        column_expressions=index.column_expressions,
        is_partial=index.is_partial,
        partial_predicate=index.partial_predicate,
        tablespace=index.tablespace,
        fill_factor=index.fill_factor,
        meta=index.meta,
        created_at=index.created_at.isoformat(),
        updated_at=index.updated_at.isoformat(),
    )


@router.put("/{index_id}", response_model=CapsuleIndexDetail)
async def update_index(
    db: DbSession,
    index_id: UUID,
    updates: CapsuleIndexUpdate,
) -> CapsuleIndexDetail:
    """Update an index."""
    repo = CapsuleIndexRepository(db)
    index = await repo.get_by_id(index_id)

    if not index:
        raise NotFoundError("Index", str(index_id))

    # Apply updates
    if updates.is_unique is not None:
        index.is_unique = updates.is_unique
    if updates.fill_factor is not None:
        index.fill_factor = updates.fill_factor
    if updates.meta is not None:
        index.meta = updates.meta

    updated = await repo.update(index)
    await db.commit()

    return CapsuleIndexDetail(
        id=str(updated.id),
        capsule_id=str(updated.capsule_id),
        index_name=updated.index_name,
        index_type=updated.index_type,
        is_unique=updated.is_unique,
        is_primary=updated.is_primary,
        column_names=updated.column_names,
        column_expressions=updated.column_expressions,
        is_partial=updated.is_partial,
        partial_predicate=updated.partial_predicate,
        tablespace=updated.tablespace,
        fill_factor=updated.fill_factor,
        meta=updated.meta,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
    )


@router.delete("/{index_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_index(
    db: DbSession,
    index_id: UUID,
) -> None:
    """Delete an index."""
    repo = CapsuleIndexRepository(db)
    deleted = await repo.delete_by_id(index_id)

    if not deleted:
        raise NotFoundError("Index", str(index_id))

    await db.commit()
