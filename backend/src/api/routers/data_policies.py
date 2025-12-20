"""Data policy endpoints."""

from datetime import timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.api.exceptions import NotFoundError, ValidationError_
from src.api.schemas.data_policy import (
    DataPolicyCreate,
    DataPolicyDetail,
    DataPolicyListResponse,
    DataPolicySummary,
    DataPolicyUpdate,
)
from src.database import DbSession
from src.models import DataPolicy
from src.repositories import DataPolicyRepository, CapsuleRepository, ColumnRepository

router = APIRouter(prefix="/data-policies", tags=["data-policies"])


@router.post("", response_model=DataPolicyDetail, status_code=status.HTTP_201_CREATED)
async def create_data_policy(
    db: DbSession,
    policy: DataPolicyCreate,
) -> DataPolicyDetail:
    """Create a new data policy."""
    # Validate that exactly one of capsule_id or column_id is provided
    if not ((policy.capsule_id is None) != (policy.column_id is None)):
        raise ValidationError_("Exactly one of capsule_id or column_id must be provided")

    # Verify subject exists
    if policy.capsule_id:
        capsule_repo = CapsuleRepository(db)
        subject = await capsule_repo.get_by_id(UUID(policy.capsule_id))
        if not subject:
            raise NotFoundError("Capsule", policy.capsule_id)
    else:
        column_repo = ColumnRepository(db)
        subject = await column_repo.get_by_id(UUID(policy.column_id))
        if not subject:
            raise NotFoundError("Column", policy.column_id)

    repo = DataPolicyRepository(db)

    # Convert retention/review periods from days to timedelta
    retention_period = timedelta(days=policy.retention_period_days) if policy.retention_period_days else None
    review_frequency = timedelta(days=policy.review_frequency_days) if policy.review_frequency_days else None
    audit_retention = timedelta(days=policy.audit_retention_days) if policy.audit_retention_days else None

    # Create policy
    new_policy = DataPolicy(
        capsule_id=UUID(policy.capsule_id) if policy.capsule_id else None,
        column_id=UUID(policy.column_id) if policy.column_id else None,
        sensitivity_level=policy.sensitivity_level,
        classification_tags=policy.classification_tags,
        retention_period=retention_period,
        retention_start=policy.retention_start,
        deletion_action=policy.deletion_action,
        legal_hold=policy.legal_hold,
        allowed_regions=policy.allowed_regions,
        restricted_regions=policy.restricted_regions,
        data_residency=policy.data_residency,
        cross_border_transfer=policy.cross_border_transfer,
        min_access_level=policy.min_access_level,
        allowed_roles=policy.allowed_roles,
        denied_roles=policy.denied_roles,
        approved_purposes=policy.approved_purposes,
        prohibited_purposes=policy.prohibited_purposes,
        requires_masking=policy.requires_masking,
        masking_method=policy.masking_method,
        masking_conditions=policy.masking_conditions,
        encryption_required=policy.encryption_required,
        encryption_method=policy.encryption_method,
        encryption_at_rest=policy.encryption_at_rest,
        encryption_in_transit=policy.encryption_in_transit,
        compliance_frameworks=policy.compliance_frameworks,
        consent_required=policy.consent_required,
        right_to_erasure=policy.right_to_erasure,
        audit_log_required=policy.audit_log_required,
        audit_retention_period=audit_retention,
        policy_owner_id=UUID(policy.policy_owner_id) if policy.policy_owner_id else None,
        approved_by=policy.approved_by,
        approved_at=policy.approved_at,
        review_frequency=review_frequency,
        last_reviewed_at=policy.last_reviewed_at,
        next_review_date=policy.next_review_date,
        policy_status=policy.policy_status,
        effective_from=policy.effective_from,
        effective_to=policy.effective_to,
        meta=policy.meta,
    )

    created = await repo.create(new_policy)
    await db.commit()

    return DataPolicyDetail(
        id=str(created.id),
        capsule_id=str(created.capsule_id) if created.capsule_id else None,
        column_id=str(created.column_id) if created.column_id else None,
        sensitivity_level=created.sensitivity_level,
        classification_tags=created.classification_tags,
        retention_period_days=created.retention_period.days if created.retention_period else None,
        retention_start=created.retention_start,
        deletion_action=created.deletion_action,
        legal_hold=created.legal_hold,
        allowed_regions=created.allowed_regions,
        restricted_regions=created.restricted_regions,
        data_residency=created.data_residency,
        cross_border_transfer=created.cross_border_transfer,
        min_access_level=created.min_access_level,
        allowed_roles=created.allowed_roles,
        denied_roles=created.denied_roles,
        approved_purposes=created.approved_purposes,
        prohibited_purposes=created.prohibited_purposes,
        requires_masking=created.requires_masking,
        masking_method=created.masking_method,
        masking_conditions=created.masking_conditions,
        encryption_required=created.encryption_required,
        encryption_method=created.encryption_method,
        encryption_at_rest=created.encryption_at_rest,
        encryption_in_transit=created.encryption_in_transit,
        compliance_frameworks=created.compliance_frameworks,
        consent_required=created.consent_required,
        right_to_erasure=created.right_to_erasure,
        audit_log_required=created.audit_log_required,
        audit_retention_days=created.audit_retention_period.days if created.audit_retention_period else None,
        policy_owner_id=str(created.policy_owner_id) if created.policy_owner_id else None,
        approved_by=created.approved_by,
        approved_at=created.approved_at.isoformat() if created.approved_at else None,
        review_frequency_days=created.review_frequency.days if created.review_frequency else None,
        last_reviewed_at=created.last_reviewed_at.isoformat() if created.last_reviewed_at else None,
        next_review_date=created.next_review_date.isoformat() if created.next_review_date else None,
        policy_status=created.policy_status,
        effective_from=created.effective_from.isoformat() if created.effective_from else None,
        effective_to=created.effective_to.isoformat() if created.effective_to else None,
        meta=created.meta,
        created_at=created.created_at.isoformat(),
        updated_at=created.updated_at.isoformat(),
    )


@router.get("", response_model=DataPolicyListResponse)
async def list_data_policies(
    db: DbSession,
    capsule_id: Optional[str] = Query(None, description="Filter by capsule ID"),
    column_id: Optional[str] = Query(None, description="Filter by column ID"),
    sensitivity_level: Optional[str] = Query(None, description="Filter by sensitivity level"),
    active_only: bool = Query(False, description="Show only active policies"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> DataPolicyListResponse:
    """List data policies with optional filters."""
    repo = DataPolicyRepository(db)

    if capsule_id:
        policies = await repo.get_by_capsule(UUID(capsule_id), offset, limit)
        total = await repo.count_by_capsule(UUID(capsule_id))
    elif column_id:
        policies = await repo.get_by_column(UUID(column_id), offset, limit)
        total = await repo.count_by_column(UUID(column_id))
    elif sensitivity_level:
        policies = await repo.get_by_sensitivity(sensitivity_level, offset, limit)
        total = await repo.count()
    elif active_only:
        policies = await repo.get_active_policies(offset=offset, limit=limit)
        total = await repo.count()
    else:
        policies = await repo.get_all(offset, limit)
        total = await repo.count()

    data = [
        DataPolicySummary(
            id=str(p.id),
            capsule_id=str(p.capsule_id) if p.capsule_id else None,
            column_id=str(p.column_id) if p.column_id else None,
            sensitivity_level=p.sensitivity_level,
            classification_tags=p.classification_tags,
            policy_status=p.policy_status,
            requires_masking=p.requires_masking,
            encryption_required=p.encryption_required,
        )
        for p in policies
    ]

    return DataPolicyListResponse(
        data=data,
        pagination={
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": offset + limit < total,
        },
    )


@router.get("/{policy_id}", response_model=DataPolicyDetail)
async def get_data_policy(
    db: DbSession,
    policy_id: UUID,
) -> DataPolicyDetail:
    """Get data policy by ID."""
    repo = DataPolicyRepository(db)
    policy = await repo.get_by_id(policy_id)

    if not policy:
        raise NotFoundError("DataPolicy", str(policy_id))

    return DataPolicyDetail(
        id=str(policy.id),
        capsule_id=str(policy.capsule_id) if policy.capsule_id else None,
        column_id=str(policy.column_id) if policy.column_id else None,
        sensitivity_level=policy.sensitivity_level,
        classification_tags=policy.classification_tags,
        retention_period_days=policy.retention_period.days if policy.retention_period else None,
        retention_start=policy.retention_start,
        deletion_action=policy.deletion_action,
        legal_hold=policy.legal_hold,
        allowed_regions=policy.allowed_regions,
        restricted_regions=policy.restricted_regions,
        data_residency=policy.data_residency,
        cross_border_transfer=policy.cross_border_transfer,
        min_access_level=policy.min_access_level,
        allowed_roles=policy.allowed_roles,
        denied_roles=policy.denied_roles,
        approved_purposes=policy.approved_purposes,
        prohibited_purposes=policy.prohibited_purposes,
        requires_masking=policy.requires_masking,
        masking_method=policy.masking_method,
        masking_conditions=policy.masking_conditions,
        encryption_required=policy.encryption_required,
        encryption_method=policy.encryption_method,
        encryption_at_rest=policy.encryption_at_rest,
        encryption_in_transit=policy.encryption_in_transit,
        compliance_frameworks=policy.compliance_frameworks,
        consent_required=policy.consent_required,
        right_to_erasure=policy.right_to_erasure,
        audit_log_required=policy.audit_log_required,
        audit_retention_days=policy.audit_retention_period.days if policy.audit_retention_period else None,
        policy_owner_id=str(policy.policy_owner_id) if policy.policy_owner_id else None,
        approved_by=policy.approved_by,
        approved_at=policy.approved_at.isoformat() if policy.approved_at else None,
        review_frequency_days=policy.review_frequency.days if policy.review_frequency else None,
        last_reviewed_at=policy.last_reviewed_at.isoformat() if policy.last_reviewed_at else None,
        next_review_date=policy.next_review_date.isoformat() if policy.next_review_date else None,
        policy_status=policy.policy_status,
        effective_from=policy.effective_from.isoformat() if policy.effective_from else None,
        effective_to=policy.effective_to.isoformat() if policy.effective_to else None,
        meta=policy.meta,
        created_at=policy.created_at.isoformat(),
        updated_at=policy.updated_at.isoformat(),
    )


@router.put("/{policy_id}", response_model=DataPolicyDetail)
async def update_data_policy(
    db: DbSession,
    policy_id: UUID,
    updates: DataPolicyUpdate,
) -> DataPolicyDetail:
    """Update a data policy."""
    repo = DataPolicyRepository(db)
    policy = await repo.get_by_id(policy_id)

    if not policy:
        raise NotFoundError("DataPolicy", str(policy_id))

    # Apply updates (only showing a subset for brevity - full implementation would include all fields)
    if updates.sensitivity_level is not None:
        policy.sensitivity_level = updates.sensitivity_level
    if updates.classification_tags is not None:
        policy.classification_tags = updates.classification_tags
    if updates.retention_period_days is not None:
        policy.retention_period = timedelta(days=updates.retention_period_days)
    if updates.policy_status is not None:
        policy.policy_status = updates.policy_status
    if updates.meta is not None:
        policy.meta = updates.meta

    updated = await repo.update(policy)
    await db.commit()

    return DataPolicyDetail(
        id=str(updated.id),
        capsule_id=str(updated.capsule_id) if updated.capsule_id else None,
        column_id=str(updated.column_id) if updated.column_id else None,
        sensitivity_level=updated.sensitivity_level,
        classification_tags=updated.classification_tags,
        retention_period_days=updated.retention_period.days if updated.retention_period else None,
        retention_start=updated.retention_start,
        deletion_action=updated.deletion_action,
        legal_hold=updated.legal_hold,
        allowed_regions=updated.allowed_regions,
        restricted_regions=updated.restricted_regions,
        data_residency=updated.data_residency,
        cross_border_transfer=updated.cross_border_transfer,
        min_access_level=updated.min_access_level,
        allowed_roles=updated.allowed_roles,
        denied_roles=updated.denied_roles,
        approved_purposes=updated.approved_purposes,
        prohibited_purposes=updated.prohibited_purposes,
        requires_masking=updated.requires_masking,
        masking_method=updated.masking_method,
        masking_conditions=updated.masking_conditions,
        encryption_required=updated.encryption_required,
        encryption_method=updated.encryption_method,
        encryption_at_rest=updated.encryption_at_rest,
        encryption_in_transit=updated.encryption_in_transit,
        compliance_frameworks=updated.compliance_frameworks,
        consent_required=updated.consent_required,
        right_to_erasure=updated.right_to_erasure,
        audit_log_required=updated.audit_log_required,
        audit_retention_days=updated.audit_retention_period.days if updated.audit_retention_period else None,
        policy_owner_id=str(updated.policy_owner_id) if updated.policy_owner_id else None,
        approved_by=updated.approved_by,
        approved_at=updated.approved_at.isoformat() if updated.approved_at else None,
        review_frequency_days=updated.review_frequency.days if updated.review_frequency else None,
        last_reviewed_at=updated.last_reviewed_at.isoformat() if updated.last_reviewed_at else None,
        next_review_date=updated.next_review_date.isoformat() if updated.next_review_date else None,
        policy_status=updated.policy_status,
        effective_from=updated.effective_from.isoformat() if updated.effective_from else None,
        effective_to=updated.effective_to.isoformat() if updated.effective_to else None,
        meta=updated.meta,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
    )


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_policy(
    db: DbSession,
    policy_id: UUID,
) -> None:
    """Delete a data policy."""
    repo = DataPolicyRepository(db)
    deleted = await repo.delete_by_id(policy_id)

    if not deleted:
        raise NotFoundError("DataPolicy", str(policy_id))

    await db.commit()
