"""Masking rule endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query, status

from src.api.exceptions import NotFoundError
from src.api.schemas.masking_rule import (
    MaskingRuleCreate,
    MaskingRuleDetail,
    MaskingRuleListResponse,
    MaskingRuleSummary,
    MaskingRuleUpdate,
)
from src.database import DbSession
from src.models import MaskingRule
from src.repositories import MaskingRuleRepository, ColumnRepository

router = APIRouter(prefix="/masking-rules", tags=["masking-rules"])


@router.post("", response_model=MaskingRuleDetail, status_code=status.HTTP_201_CREATED)
async def create_masking_rule(
    db: DbSession,
    rule: MaskingRuleCreate,
) -> MaskingRuleDetail:
    """Create a new masking rule."""
    column_repo = ColumnRepository(db)
    rule_repo = MaskingRuleRepository(db)

    # Verify column exists
    column = await column_repo.get_by_id(UUID(rule.column_id))
    if not column:
        raise NotFoundError("Column", rule.column_id)

    # Create rule
    new_rule = MaskingRule(
        column_id=UUID(rule.column_id),
        rule_name=rule.rule_name,
        masking_method=rule.masking_method,
        method_config=rule.method_config,
        apply_condition=rule.apply_condition,
        applies_to_roles=rule.applies_to_roles,
        exempt_roles=rule.exempt_roles,
        preserve_length=rule.preserve_length,
        preserve_format=rule.preserve_format,
        preserve_type=rule.preserve_type,
        preserve_null=rule.preserve_null,
        is_reversible=rule.is_reversible,
        tokenization_vault=rule.tokenization_vault,
        is_enabled=rule.is_enabled,
        description=rule.description,
        meta=rule.meta,
    )

    created = await rule_repo.create(new_rule)
    await db.commit()

    return MaskingRuleDetail(
        id=str(created.id),
        column_id=str(created.column_id),
        rule_name=created.rule_name,
        masking_method=created.masking_method,
        method_config=created.method_config,
        apply_condition=created.apply_condition,
        applies_to_roles=created.applies_to_roles,
        exempt_roles=created.exempt_roles,
        preserve_length=created.preserve_length,
        preserve_format=created.preserve_format,
        preserve_type=created.preserve_type,
        preserve_null=created.preserve_null,
        is_reversible=created.is_reversible,
        tokenization_vault=created.tokenization_vault,
        is_enabled=created.is_enabled,
        description=created.description,
        meta=created.meta,
        created_at=created.created_at.isoformat(),
        updated_at=created.updated_at.isoformat(),
    )


@router.get("", response_model=MaskingRuleListResponse)
async def list_masking_rules(
    db: DbSession,
    column_id: str = Query(..., description="Filter by column ID (required)"),
    enabled_only: bool = Query(False, description="Show only enabled rules"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> MaskingRuleListResponse:
    """List masking rules for a specific column."""
    repo = MaskingRuleRepository(db)

    if enabled_only:
        rules = await repo.get_enabled_rules(UUID(column_id), offset, limit)
    else:
        rules = await repo.get_by_column(UUID(column_id), offset, limit)

    total = await repo.count_by_column(UUID(column_id))

    data = [
        MaskingRuleSummary(
            id=str(r.id),
            column_id=str(r.column_id),
            rule_name=r.rule_name,
            masking_method=r.masking_method,
            is_enabled=r.is_enabled,
            is_reversible=r.is_reversible,
        )
        for r in rules
    ]

    return MaskingRuleListResponse(
        data=data,
        pagination={
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": offset + limit < total,
        },
    )


@router.get("/{rule_id}", response_model=MaskingRuleDetail)
async def get_masking_rule(
    db: DbSession,
    rule_id: UUID,
) -> MaskingRuleDetail:
    """Get masking rule by ID."""
    repo = MaskingRuleRepository(db)
    rule = await repo.get_by_id(rule_id)

    if not rule:
        raise NotFoundError("MaskingRule", str(rule_id))

    return MaskingRuleDetail(
        id=str(rule.id),
        column_id=str(rule.column_id),
        rule_name=rule.rule_name,
        masking_method=rule.masking_method,
        method_config=rule.method_config,
        apply_condition=rule.apply_condition,
        applies_to_roles=rule.applies_to_roles,
        exempt_roles=rule.exempt_roles,
        preserve_length=rule.preserve_length,
        preserve_format=rule.preserve_format,
        preserve_type=rule.preserve_type,
        preserve_null=rule.preserve_null,
        is_reversible=rule.is_reversible,
        tokenization_vault=rule.tokenization_vault,
        is_enabled=rule.is_enabled,
        description=rule.description,
        meta=rule.meta,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat(),
    )


@router.put("/{rule_id}", response_model=MaskingRuleDetail)
async def update_masking_rule(
    db: DbSession,
    rule_id: UUID,
    updates: MaskingRuleUpdate,
) -> MaskingRuleDetail:
    """Update a masking rule."""
    repo = MaskingRuleRepository(db)
    rule = await repo.get_by_id(rule_id)

    if not rule:
        raise NotFoundError("MaskingRule", str(rule_id))

    # Apply updates
    if updates.rule_name is not None:
        rule.rule_name = updates.rule_name
    if updates.masking_method is not None:
        rule.masking_method = updates.masking_method
    if updates.method_config is not None:
        rule.method_config = updates.method_config
    if updates.apply_condition is not None:
        rule.apply_condition = updates.apply_condition
    if updates.applies_to_roles is not None:
        rule.applies_to_roles = updates.applies_to_roles
    if updates.exempt_roles is not None:
        rule.exempt_roles = updates.exempt_roles
    if updates.preserve_length is not None:
        rule.preserve_length = updates.preserve_length
    if updates.preserve_format is not None:
        rule.preserve_format = updates.preserve_format
    if updates.preserve_type is not None:
        rule.preserve_type = updates.preserve_type
    if updates.preserve_null is not None:
        rule.preserve_null = updates.preserve_null
    if updates.is_reversible is not None:
        rule.is_reversible = updates.is_reversible
    if updates.tokenization_vault is not None:
        rule.tokenization_vault = updates.tokenization_vault
    if updates.is_enabled is not None:
        rule.is_enabled = updates.is_enabled
    if updates.description is not None:
        rule.description = updates.description
    if updates.meta is not None:
        rule.meta = updates.meta

    updated = await repo.update(rule)
    await db.commit()

    return MaskingRuleDetail(
        id=str(updated.id),
        column_id=str(updated.column_id),
        rule_name=updated.rule_name,
        masking_method=updated.masking_method,
        method_config=updated.method_config,
        apply_condition=updated.apply_condition,
        applies_to_roles=updated.applies_to_roles,
        exempt_roles=updated.exempt_roles,
        preserve_length=updated.preserve_length,
        preserve_format=updated.preserve_format,
        preserve_type=updated.preserve_type,
        preserve_null=updated.preserve_null,
        is_reversible=updated.is_reversible,
        tokenization_vault=updated.tokenization_vault,
        is_enabled=updated.is_enabled,
        description=updated.description,
        meta=updated.meta,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
    )


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_masking_rule(
    db: DbSession,
    rule_id: UUID,
) -> None:
    """Delete a masking rule."""
    repo = MaskingRuleRepository(db)
    deleted = await repo.delete_by_id(rule_id)

    if not deleted:
        raise NotFoundError("MaskingRule", str(rule_id))

    await db.commit()
