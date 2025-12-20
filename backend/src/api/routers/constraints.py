"""Column constraint endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.api.exceptions import NotFoundError
from src.api.schemas.constraint import (
    ColumnConstraintCreate,
    ColumnConstraintDetail,
    ColumnConstraintListResponse,
    ColumnConstraintSummary,
    ColumnConstraintUpdate,
)
from src.database import DbSession
from src.models import ColumnConstraint, ConstraintType
from src.repositories import ColumnConstraintRepository, ColumnRepository

router = APIRouter(prefix="/constraints", tags=["constraints"])


@router.post("", response_model=ColumnConstraintDetail, status_code=status.HTTP_201_CREATED)
async def create_constraint(
    db: DbSession,
    constraint: ColumnConstraintCreate,
) -> ColumnConstraintDetail:
    """Create a new column constraint."""
    column_repo = ColumnRepository(db)
    constraint_repo = ColumnConstraintRepository(db)

    # Verify column exists
    column = await column_repo.get_by_id(UUID(constraint.column_id))
    if not column:
        raise NotFoundError("Column", str(constraint.column_id))

    # Create constraint
    new_constraint = ColumnConstraint(
        column_id=UUID(constraint.column_id),
        constraint_type=constraint.constraint_type,
        constraint_name=constraint.constraint_name,
        referenced_table_urn=constraint.referenced_table_urn,
        referenced_column_urn=constraint.referenced_column_urn,
        on_delete_action=constraint.on_delete_action,
        on_update_action=constraint.on_update_action,
        check_expression=constraint.check_expression,
        default_value=constraint.default_value,
        default_expression=constraint.default_expression,
        is_enforced=constraint.is_enforced,
        is_deferrable=constraint.is_deferrable,
        meta=constraint.meta,
    )

    created = await constraint_repo.create(new_constraint)
    await db.commit()

    return ColumnConstraintDetail(
        id=str(created.id),
        column_id=str(created.column_id),
        constraint_type=created.constraint_type,
        constraint_name=created.constraint_name,
        referenced_table_urn=created.referenced_table_urn,
        referenced_column_urn=created.referenced_column_urn,
        on_delete_action=created.on_delete_action,
        on_update_action=created.on_update_action,
        check_expression=created.check_expression,
        default_value=created.default_value,
        default_expression=created.default_expression,
        is_enforced=created.is_enforced,
        is_deferrable=created.is_deferrable,
        meta=created.meta,
        created_at=created.created_at.isoformat(),
        updated_at=created.updated_at.isoformat(),
    )


@router.get("", response_model=ColumnConstraintListResponse)
async def list_constraints(
    db: DbSession,
    constraint_type: Optional[str] = Query(None, description="Filter by constraint type"),
    column_id: Optional[str] = Query(None, description="Filter by column ID"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> ColumnConstraintListResponse:
    """List column constraints with optional filters."""
    repo = ColumnConstraintRepository(db)

    if column_id:
        constraints = await repo.get_by_column(UUID(column_id), offset, limit)
        total = await repo.count_by_column(UUID(column_id))
    elif constraint_type:
        constraints = await repo.get_by_type(constraint_type, offset, limit)
        total = await repo.count()
    else:
        constraints = await repo.get_all(offset, limit)
        total = await repo.count()

    data = [
        ColumnConstraintSummary(
            id=str(c.id),
            column_id=str(c.column_id),
            constraint_type=c.constraint_type,
            constraint_name=c.constraint_name,
            is_enforced=c.is_enforced,
        )
        for c in constraints
    ]

    return ColumnConstraintListResponse(
        data=data,
        pagination={
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": offset + limit < total,
        },
    )


@router.get("/primary-keys", response_model=ColumnConstraintListResponse)
async def list_primary_keys(
    db: DbSession,
    capsule_id: Optional[str] = Query(None, description="Filter by capsule ID"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> ColumnConstraintListResponse:
    """List all primary key constraints."""
    repo = ColumnConstraintRepository(db)

    capsule_uuid = UUID(capsule_id) if capsule_id else None
    constraints = await repo.get_primary_keys(capsule_uuid)

    # Apply pagination manually for this query
    paginated = constraints[offset:offset + limit]
    total = len(constraints)

    data = [
        ColumnConstraintSummary(
            id=str(c.id),
            column_id=str(c.column_id),
            constraint_type=c.constraint_type,
            constraint_name=c.constraint_name,
            is_enforced=c.is_enforced,
        )
        for c in paginated
    ]

    return ColumnConstraintListResponse(
        data=data,
        pagination={
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": offset + limit < total,
        },
    )


@router.get("/foreign-keys", response_model=ColumnConstraintListResponse)
async def list_foreign_keys(
    db: DbSession,
    capsule_id: Optional[str] = Query(None, description="Filter by capsule ID"),
    referenced_table: Optional[str] = Query(None, description="Filter by referenced table URN"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> ColumnConstraintListResponse:
    """List all foreign key constraints."""
    repo = ColumnConstraintRepository(db)

    if referenced_table:
        constraints = await repo.get_by_referenced_table(referenced_table, offset, limit)
        total = await repo.count()
    else:
        capsule_uuid = UUID(capsule_id) if capsule_id else None
        constraints = await repo.get_foreign_keys(capsule_uuid)
        # Apply pagination manually
        constraints = constraints[offset:offset + limit]
        total = len(constraints)

    data = [
        ColumnConstraintSummary(
            id=str(c.id),
            column_id=str(c.column_id),
            constraint_type=c.constraint_type,
            constraint_name=c.constraint_name,
            is_enforced=c.is_enforced,
        )
        for c in constraints
    ]

    return ColumnConstraintListResponse(
        data=data,
        pagination={
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": offset + limit < total,
        },
    )


@router.get("/{constraint_id}", response_model=ColumnConstraintDetail)
async def get_constraint(
    db: DbSession,
    constraint_id: UUID,
) -> ColumnConstraintDetail:
    """Get constraint by ID."""
    repo = ColumnConstraintRepository(db)
    constraint = await repo.get_by_id(constraint_id)

    if not constraint:
        raise NotFoundError("Constraint", str(constraint_id))

    return ColumnConstraintDetail(
        id=str(constraint.id),
        column_id=str(constraint.column_id),
        constraint_type=constraint.constraint_type,
        constraint_name=constraint.constraint_name,
        referenced_table_urn=constraint.referenced_table_urn,
        referenced_column_urn=constraint.referenced_column_urn,
        on_delete_action=constraint.on_delete_action,
        on_update_action=constraint.on_update_action,
        check_expression=constraint.check_expression,
        default_value=constraint.default_value,
        default_expression=constraint.default_expression,
        is_enforced=constraint.is_enforced,
        is_deferrable=constraint.is_deferrable,
        meta=constraint.meta,
        created_at=constraint.created_at.isoformat(),
        updated_at=constraint.updated_at.isoformat(),
    )


@router.put("/{constraint_id}", response_model=ColumnConstraintDetail)
async def update_constraint(
    db: DbSession,
    constraint_id: UUID,
    updates: ColumnConstraintUpdate,
) -> ColumnConstraintDetail:
    """Update a constraint."""
    repo = ColumnConstraintRepository(db)
    constraint = await repo.get_by_id(constraint_id)

    if not constraint:
        raise NotFoundError("Constraint", str(constraint_id))

    # Apply updates
    if updates.constraint_name is not None:
        constraint.constraint_name = updates.constraint_name
    if updates.is_enforced is not None:
        constraint.is_enforced = updates.is_enforced
    if updates.is_deferrable is not None:
        constraint.is_deferrable = updates.is_deferrable
    if updates.meta is not None:
        constraint.meta = updates.meta

    updated = await repo.update(constraint)
    await db.commit()

    return ColumnConstraintDetail(
        id=str(updated.id),
        column_id=str(updated.column_id),
        constraint_type=updated.constraint_type,
        constraint_name=updated.constraint_name,
        referenced_table_urn=updated.referenced_table_urn,
        referenced_column_urn=updated.referenced_column_urn,
        on_delete_action=updated.on_delete_action,
        on_update_action=updated.on_update_action,
        check_expression=updated.check_expression,
        default_value=updated.default_value,
        default_expression=updated.default_expression,
        is_enforced=updated.is_enforced,
        is_deferrable=updated.is_deferrable,
        meta=updated.meta,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
    )


@router.delete("/{constraint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_constraint(
    db: DbSession,
    constraint_id: UUID,
) -> None:
    """Delete a constraint."""
    repo = ColumnConstraintRepository(db)
    deleted = await repo.delete_by_id(constraint_id)

    if not deleted:
        raise NotFoundError("Constraint", str(constraint_id))

    await db.commit()
