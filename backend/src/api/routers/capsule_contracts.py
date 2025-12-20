"""Capsule contract endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.api.exceptions import NotFoundError
from src.api.schemas.capsule_contract import (
    CapsuleContractCreate,
    CapsuleContractDetail,
    CapsuleContractListResponse,
    CapsuleContractSummary,
    CapsuleContractUpdate,
)
from src.database import DbSession
from src.models import CapsuleContract
from src.repositories.capsule import CapsuleRepository
from src.repositories.capsule_contract import CapsuleContractRepository

router = APIRouter(prefix="/capsule-contracts", tags=["capsule-contracts"])


@router.post("", response_model=CapsuleContractDetail, status_code=status.HTTP_201_CREATED)
async def create_capsule_contract(
    db: DbSession,
    contract: CapsuleContractCreate,
) -> CapsuleContractDetail:
    """Create a new capsule contract."""
    # Verify capsule exists
    capsule_repo = CapsuleRepository(db)
    capsule = await capsule_repo.get_by_id(UUID(contract.capsule_id))
    if not capsule:
        raise NotFoundError("Capsule", contract.capsule_id)

    repo = CapsuleContractRepository(db)

    new_contract = CapsuleContract(
        capsule_id=UUID(contract.capsule_id),
        contract_version=contract.contract_version,
        contract_status=contract.contract_status,
        freshness_sla=contract.freshness_sla,
        freshness_schedule=contract.freshness_schedule,
        last_updated_at=contract.last_updated_at,
        completeness_sla=contract.completeness_sla,
        expected_row_count_min=contract.expected_row_count_min,
        expected_row_count_max=contract.expected_row_count_max,
        availability_sla=contract.availability_sla,
        max_downtime=contract.max_downtime,
        quality_score_sla=contract.quality_score_sla,
        critical_quality_rules=contract.critical_quality_rules,
        query_latency_p95=contract.query_latency_p95,
        query_latency_p99=contract.query_latency_p99,
        schema_change_policy=contract.schema_change_policy,
        breaking_change_notice_days=contract.breaking_change_notice_days,
        support_level=contract.support_level,
        support_contact=contract.support_contact,
        support_slack_channel=contract.support_slack_channel,
        support_oncall=contract.support_oncall,
        maintenance_windows=contract.maintenance_windows,
        deprecation_policy=contract.deprecation_policy,
        deprecation_date=contract.deprecation_date,
        replacement_capsule_urn=contract.replacement_capsule_urn,
        known_consumers=contract.known_consumers,
        consumer_notification_required=contract.consumer_notification_required,
        target_row_count=contract.target_row_count,
        target_size_bytes=contract.target_size_bytes,
        target_column_count=contract.target_column_count,
        cost_center=contract.cost_center,
        billing_tags=contract.billing_tags,
        meta=contract.meta,
        contract_owner_id=UUID(contract.contract_owner_id) if contract.contract_owner_id else None,
        approved_by=contract.approved_by,
        approved_at=contract.approved_at,
    )

    created = await repo.create(new_contract)
    await db.commit()

    return CapsuleContractDetail(
        id=str(created.id),
        capsule_id=str(created.capsule_id),
        contract_version=created.contract_version,
        contract_status=created.contract_status,
        freshness_sla=created.freshness_sla,
        freshness_schedule=created.freshness_schedule,
        last_updated_at=created.last_updated_at,
        completeness_sla=created.completeness_sla,
        expected_row_count_min=created.expected_row_count_min,
        expected_row_count_max=created.expected_row_count_max,
        availability_sla=created.availability_sla,
        max_downtime=created.max_downtime,
        quality_score_sla=created.quality_score_sla,
        critical_quality_rules=created.critical_quality_rules,
        query_latency_p95=created.query_latency_p95,
        query_latency_p99=created.query_latency_p99,
        schema_change_policy=created.schema_change_policy,
        breaking_change_notice_days=created.breaking_change_notice_days,
        support_level=created.support_level,
        support_contact=created.support_contact,
        support_slack_channel=created.support_slack_channel,
        support_oncall=created.support_oncall,
        maintenance_windows=created.maintenance_windows,
        deprecation_policy=created.deprecation_policy,
        deprecation_date=created.deprecation_date,
        replacement_capsule_urn=created.replacement_capsule_urn,
        known_consumers=created.known_consumers,
        consumer_notification_required=created.consumer_notification_required,
        target_row_count=created.target_row_count,
        target_size_bytes=created.target_size_bytes,
        target_column_count=created.target_column_count,
        cost_center=created.cost_center,
        billing_tags=created.billing_tags,
        meta=created.meta,
        contract_owner_id=str(created.contract_owner_id) if created.contract_owner_id else None,
        approved_by=created.approved_by,
        approved_at=created.approved_at,
        created_at=created.created_at.isoformat(),
        updated_at=created.updated_at.isoformat(),
    )


@router.get("", response_model=CapsuleContractListResponse)
async def list_capsule_contracts(
    db: DbSession,
    capsule_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    support_level: Optional[str] = Query(None),
    active_only: bool = Query(False),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> CapsuleContractListResponse:
    """List capsule contracts with filters."""
    repo = CapsuleContractRepository(db)

    if capsule_id:
        contracts = await repo.get_by_capsule(UUID(capsule_id), offset, limit)
        total = await repo.count_by_capsule(UUID(capsule_id))
    elif active_only:
        contracts = await repo.get_active_contracts(offset=offset, limit=limit)
        total = await repo.count_by_status("active")
    elif status_filter:
        contracts = await repo.get_by_status(status_filter, offset, limit)
        total = await repo.count_by_status(status_filter)
    elif support_level:
        contracts = await repo.get_by_support_level(support_level, offset, limit)
        total = await repo.count()
    else:
        contracts = await repo.get_all(offset, limit)
        total = await repo.count()

    return CapsuleContractListResponse(
        data=[
            CapsuleContractSummary(
                id=str(c.id),
                capsule_id=str(c.capsule_id),
                contract_version=c.contract_version,
                contract_status=c.contract_status,
                support_level=c.support_level,
                deprecation_date=c.deprecation_date,
                created_at=c.created_at.isoformat(),
            )
            for c in contracts
        ],
        pagination={"offset": offset, "limit": limit, "total": total},
    )


@router.get("/{contract_id}", response_model=CapsuleContractDetail)
async def get_capsule_contract(db: DbSession, contract_id: str) -> CapsuleContractDetail:
    """Get a capsule contract by ID."""
    repo = CapsuleContractRepository(db)
    contract = await repo.get_by_id(UUID(contract_id))
    if not contract:
        raise NotFoundError("CapsuleContract", contract_id)

    return CapsuleContractDetail(
        id=str(contract.id),
        capsule_id=str(contract.capsule_id),
        contract_version=contract.contract_version,
        contract_status=contract.contract_status,
        freshness_sla=contract.freshness_sla,
        freshness_schedule=contract.freshness_schedule,
        last_updated_at=contract.last_updated_at,
        completeness_sla=contract.completeness_sla,
        expected_row_count_min=contract.expected_row_count_min,
        expected_row_count_max=contract.expected_row_count_max,
        availability_sla=contract.availability_sla,
        max_downtime=contract.max_downtime,
        quality_score_sla=contract.quality_score_sla,
        critical_quality_rules=contract.critical_quality_rules,
        query_latency_p95=contract.query_latency_p95,
        query_latency_p99=contract.query_latency_p99,
        schema_change_policy=contract.schema_change_policy,
        breaking_change_notice_days=contract.breaking_change_notice_days,
        support_level=contract.support_level,
        support_contact=contract.support_contact,
        support_slack_channel=contract.support_slack_channel,
        support_oncall=contract.support_oncall,
        maintenance_windows=contract.maintenance_windows,
        deprecation_policy=contract.deprecation_policy,
        deprecation_date=contract.deprecation_date,
        replacement_capsule_urn=contract.replacement_capsule_urn,
        known_consumers=contract.known_consumers,
        consumer_notification_required=contract.consumer_notification_required,
        target_row_count=contract.target_row_count,
        target_size_bytes=contract.target_size_bytes,
        target_column_count=contract.target_column_count,
        cost_center=contract.cost_center,
        billing_tags=contract.billing_tags,
        meta=contract.meta,
        contract_owner_id=str(contract.contract_owner_id) if contract.contract_owner_id else None,
        approved_by=contract.approved_by,
        approved_at=contract.approved_at,
        created_at=contract.created_at.isoformat(),
        updated_at=contract.updated_at.isoformat(),
    )


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_capsule_contract(db: DbSession, contract_id: str) -> None:
    """Delete a capsule contract."""
    repo = CapsuleContractRepository(db)
    contract = await repo.get_by_id(UUID(contract_id))
    if not contract:
        raise NotFoundError("CapsuleContract", contract_id)

    await repo.delete(contract)
    await db.commit()
