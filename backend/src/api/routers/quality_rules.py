"""Quality rule endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.api.exceptions import NotFoundError, ValidationError_
from src.api.schemas.quality_rule import (
    QualityRuleCreate,
    QualityRuleDetail,
    QualityRuleListResponse,
    QualityRuleSummary,
    QualityRuleUpdate,
)
from src.database import DbSession
from src.models import QualityRule
from src.repositories import QualityRuleRepository, CapsuleRepository, ColumnRepository

router = APIRouter(prefix="/quality-rules", tags=["quality-rules"])


@router.post("", response_model=QualityRuleDetail, status_code=status.HTTP_201_CREATED)
async def create_quality_rule(
    db: DbSession,
    rule: QualityRuleCreate,
) -> QualityRuleDetail:
    """Create a new quality rule."""
    # Validate that exactly one of capsule_id or column_id is provided
    if not ((rule.capsule_id is None) != (rule.column_id is None)):
        raise ValidationError_("Exactly one of capsule_id or column_id must be provided")

    # Verify subject exists
    if rule.capsule_id:
        capsule_repo = CapsuleRepository(db)
        subject = await capsule_repo.get_by_id(UUID(rule.capsule_id))
        if not subject:
            raise NotFoundError("Capsule", rule.capsule_id)
    else:
        column_repo = ColumnRepository(db)
        subject = await column_repo.get_by_id(UUID(rule.column_id))
        if not subject:
            raise NotFoundError("Column", rule.column_id)

    repo = QualityRuleRepository(db)

    # Create rule
    new_rule = QualityRule(
        capsule_id=UUID(rule.capsule_id) if rule.capsule_id else None,
        column_id=UUID(rule.column_id) if rule.column_id else None,
        rule_name=rule.rule_name,
        rule_type=rule.rule_type,
        rule_category=rule.rule_category,
        rule_config=rule.rule_config,
        threshold_value=rule.threshold_value,
        threshold_operator=rule.threshold_operator,
        threshold_percent=rule.threshold_percent,
        expected_value=rule.expected_value,
        expected_range_min=rule.expected_range_min,
        expected_range_max=rule.expected_range_max,
        expected_pattern=rule.expected_pattern,
        severity=rule.severity,
        blocking=rule.blocking,
        is_enabled=rule.is_enabled,
        description=rule.description,
        meta=rule.meta,
    )

    created = await repo.create(new_rule)
    await db.commit()

    return QualityRuleDetail(
        id=str(created.id),
        capsule_id=str(created.capsule_id) if created.capsule_id else None,
        column_id=str(created.column_id) if created.column_id else None,
        rule_name=created.rule_name,
        rule_type=created.rule_type,
        rule_category=created.rule_category,
        rule_config=created.rule_config,
        threshold_value=created.threshold_value,
        threshold_operator=created.threshold_operator,
        threshold_percent=created.threshold_percent,
        expected_value=created.expected_value,
        expected_range_min=created.expected_range_min,
        expected_range_max=created.expected_range_max,
        expected_pattern=created.expected_pattern,
        severity=created.severity,
        blocking=created.blocking,
        is_enabled=created.is_enabled,
        description=created.description,
        meta=created.meta,
        created_at=created.created_at.isoformat(),
        updated_at=created.updated_at.isoformat(),
    )


@router.get("", response_model=QualityRuleListResponse)
async def list_quality_rules(
    db: DbSession,
    capsule_id: Optional[str] = Query(None, description="Filter by capsule ID"),
    column_id: Optional[str] = Query(None, description="Filter by column ID"),
    rule_type: Optional[str] = Query(None, description="Filter by rule type"),
    rule_category: Optional[str] = Query(None, description="Filter by rule category"),
    enabled_only: bool = Query(False, description="Show only enabled rules"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> QualityRuleListResponse:
    """List quality rules with optional filters."""
    repo = QualityRuleRepository(db)

    if capsule_id:
        rules = await repo.get_by_capsule(UUID(capsule_id), offset, limit)
        total = await repo.count_by_capsule(UUID(capsule_id))
    elif column_id:
        rules = await repo.get_by_column(UUID(column_id), offset, limit)
        total = await repo.count_by_column(UUID(column_id))
    elif rule_type:
        rules = await repo.get_by_type(rule_type, offset, limit)
        total = await repo.count()
    elif rule_category:
        rules = await repo.get_by_category(rule_category, offset, limit)
        total = await repo.count()
    elif enabled_only:
        rules = await repo.get_enabled_rules(offset=offset, limit=limit)
        total = await repo.count()
    else:
        rules = await repo.get_all(offset, limit)
        total = await repo.count()

    data = [
        QualityRuleSummary(
            id=str(r.id),
            capsule_id=str(r.capsule_id) if r.capsule_id else None,
            column_id=str(r.column_id) if r.column_id else None,
            rule_name=r.rule_name,
            rule_type=r.rule_type,
            rule_category=r.rule_category,
            severity=r.severity,
            is_enabled=r.is_enabled,
        )
        for r in rules
    ]

    return QualityRuleListResponse(
        data=data,
        pagination={
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": offset + limit < total,
        },
    )


@router.get("/{rule_id}", response_model=QualityRuleDetail)
async def get_quality_rule(
    db: DbSession,
    rule_id: UUID,
) -> QualityRuleDetail:
    """Get quality rule by ID."""
    repo = QualityRuleRepository(db)
    rule = await repo.get_by_id(rule_id)

    if not rule:
        raise NotFoundError("QualityRule", str(rule_id))

    return QualityRuleDetail(
        id=str(rule.id),
        capsule_id=str(rule.capsule_id) if rule.capsule_id else None,
        column_id=str(rule.column_id) if rule.column_id else None,
        rule_name=rule.rule_name,
        rule_type=rule.rule_type,
        rule_category=rule.rule_category,
        rule_config=rule.rule_config,
        threshold_value=rule.threshold_value,
        threshold_operator=rule.threshold_operator,
        threshold_percent=rule.threshold_percent,
        expected_value=rule.expected_value,
        expected_range_min=rule.expected_range_min,
        expected_range_max=rule.expected_range_max,
        expected_pattern=rule.expected_pattern,
        severity=rule.severity,
        blocking=rule.blocking,
        is_enabled=rule.is_enabled,
        description=rule.description,
        meta=rule.meta,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat(),
    )


@router.put("/{rule_id}", response_model=QualityRuleDetail)
async def update_quality_rule(
    db: DbSession,
    rule_id: UUID,
    updates: QualityRuleUpdate,
) -> QualityRuleDetail:
    """Update a quality rule."""
    repo = QualityRuleRepository(db)
    rule = await repo.get_by_id(rule_id)

    if not rule:
        raise NotFoundError("QualityRule", str(rule_id))

    # Apply updates
    if updates.rule_name is not None:
        rule.rule_name = updates.rule_name
    if updates.rule_category is not None:
        rule.rule_category = updates.rule_category
    if updates.rule_config is not None:
        rule.rule_config = updates.rule_config
    if updates.threshold_value is not None:
        rule.threshold_value = updates.threshold_value
    if updates.threshold_operator is not None:
        rule.threshold_operator = updates.threshold_operator
    if updates.threshold_percent is not None:
        rule.threshold_percent = updates.threshold_percent
    if updates.expected_value is not None:
        rule.expected_value = updates.expected_value
    if updates.expected_range_min is not None:
        rule.expected_range_min = updates.expected_range_min
    if updates.expected_range_max is not None:
        rule.expected_range_max = updates.expected_range_max
    if updates.expected_pattern is not None:
        rule.expected_pattern = updates.expected_pattern
    if updates.severity is not None:
        rule.severity = updates.severity
    if updates.blocking is not None:
        rule.blocking = updates.blocking
    if updates.is_enabled is not None:
        rule.is_enabled = updates.is_enabled
    if updates.description is not None:
        rule.description = updates.description
    if updates.meta is not None:
        rule.meta = updates.meta

    updated = await repo.update(rule)
    await db.commit()

    return QualityRuleDetail(
        id=str(updated.id),
        capsule_id=str(updated.capsule_id) if updated.capsule_id else None,
        column_id=str(updated.column_id) if updated.column_id else None,
        rule_name=updated.rule_name,
        rule_type=updated.rule_type,
        rule_category=updated.rule_category,
        rule_config=updated.rule_config,
        threshold_value=updated.threshold_value,
        threshold_operator=updated.threshold_operator,
        threshold_percent=updated.threshold_percent,
        expected_value=updated.expected_value,
        expected_range_min=updated.expected_range_min,
        expected_range_max=updated.expected_range_max,
        expected_pattern=updated.expected_pattern,
        severity=updated.severity,
        blocking=updated.blocking,
        is_enabled=updated.is_enabled,
        description=updated.description,
        meta=updated.meta,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
    )


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quality_rule(
    db: DbSession,
    rule_id: UUID,
) -> None:
    """Delete a quality rule."""
    repo = QualityRuleRepository(db)
    deleted = await repo.delete_by_id(rule_id)

    if not deleted:
        raise NotFoundError("QualityRule", str(rule_id))

    await db.commit()
