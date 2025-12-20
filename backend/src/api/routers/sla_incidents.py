"""SLA incident endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.api.exceptions import NotFoundError
from src.api.schemas.sla_incident import (
    SLAIncidentCreate,
    SLAIncidentDetail,
    SLAIncidentListResponse,
    SLAIncidentSummary,
    SLAIncidentUpdate,
)
from src.database import DbSession
from src.models import SLAIncident
from src.repositories.capsule import CapsuleRepository
from src.repositories.capsule_contract import CapsuleContractRepository
from src.repositories.sla_incident import SLAIncidentRepository

router = APIRouter(prefix="/sla-incidents", tags=["sla-incidents"])


@router.post("", response_model=SLAIncidentDetail, status_code=status.HTTP_201_CREATED)
async def create_sla_incident(
    db: DbSession,
    incident: SLAIncidentCreate,
) -> SLAIncidentDetail:
    """Create a new SLA incident."""
    # Verify contract and capsule exist
    contract_repo = CapsuleContractRepository(db)
    contract = await contract_repo.get_by_id(UUID(incident.contract_id))
    if not contract:
        raise NotFoundError("CapsuleContract", incident.contract_id)

    capsule_repo = CapsuleRepository(db)
    capsule = await capsule_repo.get_by_id(UUID(incident.capsule_id))
    if not capsule:
        raise NotFoundError("Capsule", incident.capsule_id)

    repo = SLAIncidentRepository(db)

    new_incident = SLAIncident(
        contract_id=UUID(incident.contract_id),
        capsule_id=UUID(incident.capsule_id),
        incident_type=incident.incident_type,
        incident_severity=incident.incident_severity,
        sla_target=incident.sla_target,
        actual_value=incident.actual_value,
        breach_magnitude=incident.breach_magnitude,
        breach_started_at=incident.breach_started_at,
        breach_ended_at=incident.breach_ended_at,
        breach_duration=incident.breach_duration,
        affected_consumers=incident.affected_consumers,
        downstream_impact=incident.downstream_impact,
        incident_status=incident.incident_status,
        resolution=incident.resolution,
        resolved_by=incident.resolved_by,
        resolved_at=incident.resolved_at,
        root_cause=incident.root_cause,
        root_cause_category=incident.root_cause_category,
        meta=incident.meta,
    )

    created = await repo.create(new_incident)
    await db.commit()

    return SLAIncidentDetail(
        id=str(created.id),
        contract_id=str(created.contract_id),
        capsule_id=str(created.capsule_id),
        incident_type=created.incident_type,
        incident_severity=created.incident_severity,
        sla_target=created.sla_target,
        actual_value=created.actual_value,
        breach_magnitude=created.breach_magnitude,
        breach_started_at=created.breach_started_at,
        breach_ended_at=created.breach_ended_at,
        breach_duration=created.breach_duration,
        affected_consumers=created.affected_consumers,
        downstream_impact=created.downstream_impact,
        incident_status=created.incident_status,
        resolution=created.resolution,
        resolved_by=created.resolved_by,
        resolved_at=created.resolved_at,
        root_cause=created.root_cause,
        root_cause_category=created.root_cause_category,
        meta=created.meta,
        detected_at=created.detected_at.isoformat(),
        created_at=created.created_at.isoformat(),
        updated_at=created.updated_at.isoformat(),
    )


@router.get("", response_model=SLAIncidentListResponse)
async def list_sla_incidents(
    db: DbSession,
    contract_id: Optional[str] = Query(None),
    capsule_id: Optional[str] = Query(None),
    incident_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = Query(None),
    open_only: bool = Query(False),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> SLAIncidentListResponse:
    """List SLA incidents with filters."""
    repo = SLAIncidentRepository(db)

    if contract_id:
        incidents = await repo.get_by_contract(UUID(contract_id), offset, limit)
        total = await repo.count_by_contract(UUID(contract_id))
    elif capsule_id:
        incidents = await repo.get_by_capsule(UUID(capsule_id), offset, limit)
        total = await repo.count_by_capsule(UUID(capsule_id))
    elif incident_type:
        incidents = await repo.get_by_type(incident_type, offset, limit)
        total = await repo.count()
    elif open_only:
        incidents = await repo.get_open_incidents(offset=offset, limit=limit)
        total = await repo.count_open_incidents()
    elif status_filter:
        incidents = await repo.get_by_status(status_filter, offset, limit)
        total = await repo.count_by_status(status_filter)
    elif severity:
        incidents = await repo.get_by_severity(severity, offset, limit)
        total = await repo.count()
    else:
        incidents = await repo.get_all(offset, limit)
        total = await repo.count()

    return SLAIncidentListResponse(
        data=[
            SLAIncidentSummary(
                id=str(i.id),
                contract_id=str(i.contract_id),
                capsule_id=str(i.capsule_id),
                incident_type=i.incident_type,
                incident_severity=i.incident_severity,
                incident_status=i.incident_status,
                detected_at=i.detected_at.isoformat(),
                resolved_at=i.resolved_at.isoformat() if i.resolved_at else None,
            )
            for i in incidents
        ],
        pagination={"offset": offset, "limit": limit, "total": total},
    )


@router.get("/{incident_id}", response_model=SLAIncidentDetail)
async def get_sla_incident(db: DbSession, incident_id: str) -> SLAIncidentDetail:
    """Get an SLA incident by ID."""
    repo = SLAIncidentRepository(db)
    incident = await repo.get_by_id(UUID(incident_id))
    if not incident:
        raise NotFoundError("SLAIncident", incident_id)

    return SLAIncidentDetail(
        id=str(incident.id),
        contract_id=str(incident.contract_id),
        capsule_id=str(incident.capsule_id),
        incident_type=incident.incident_type,
        incident_severity=incident.incident_severity,
        sla_target=incident.sla_target,
        actual_value=incident.actual_value,
        breach_magnitude=incident.breach_magnitude,
        breach_started_at=incident.breach_started_at,
        breach_ended_at=incident.breach_ended_at,
        breach_duration=incident.breach_duration,
        affected_consumers=incident.affected_consumers,
        downstream_impact=incident.downstream_impact,
        incident_status=incident.incident_status,
        resolution=incident.resolution,
        resolved_by=incident.resolved_by,
        resolved_at=incident.resolved_at,
        root_cause=incident.root_cause,
        root_cause_category=incident.root_cause_category,
        meta=incident.meta,
        detected_at=incident.detected_at.isoformat(),
        created_at=incident.created_at.isoformat(),
        updated_at=incident.updated_at.isoformat(),
    )


@router.patch("/{incident_id}", response_model=SLAIncidentDetail)
async def update_sla_incident(
    db: DbSession,
    incident_id: str,
    updates: SLAIncidentUpdate,
) -> SLAIncidentDetail:
    """Update an SLA incident."""
    repo = SLAIncidentRepository(db)
    incident = await repo.get_by_id(UUID(incident_id))
    if not incident:
        raise NotFoundError("SLAIncident", incident_id)

    # Apply updates
    if updates.incident_severity is not None:
        incident.incident_severity = updates.incident_severity
    if updates.breach_ended_at is not None:
        incident.breach_ended_at = updates.breach_ended_at
    if updates.breach_duration is not None:
        incident.breach_duration = updates.breach_duration
    if updates.affected_consumers is not None:
        incident.affected_consumers = updates.affected_consumers
    if updates.downstream_impact is not None:
        incident.downstream_impact = updates.downstream_impact
    if updates.incident_status is not None:
        incident.incident_status = updates.incident_status
    if updates.resolution is not None:
        incident.resolution = updates.resolution
    if updates.resolved_by is not None:
        incident.resolved_by = updates.resolved_by
    if updates.resolved_at is not None:
        incident.resolved_at = updates.resolved_at
    if updates.root_cause is not None:
        incident.root_cause = updates.root_cause
    if updates.root_cause_category is not None:
        incident.root_cause_category = updates.root_cause_category
    if updates.meta is not None:
        incident.meta = updates.meta

    await repo.update(incident)
    await db.commit()

    return SLAIncidentDetail(
        id=str(incident.id),
        contract_id=str(incident.contract_id),
        capsule_id=str(incident.capsule_id),
        incident_type=incident.incident_type,
        incident_severity=incident.incident_severity,
        sla_target=incident.sla_target,
        actual_value=incident.actual_value,
        breach_magnitude=incident.breach_magnitude,
        breach_started_at=incident.breach_started_at,
        breach_ended_at=incident.breach_ended_at,
        breach_duration=incident.breach_duration,
        affected_consumers=incident.affected_consumers,
        downstream_impact=incident.downstream_impact,
        incident_status=incident.incident_status,
        resolution=incident.resolution,
        resolved_by=incident.resolved_by,
        resolved_at=incident.resolved_at,
        root_cause=incident.root_cause,
        root_cause_category=incident.root_cause_category,
        meta=incident.meta,
        detected_at=incident.detected_at.isoformat(),
        created_at=incident.created_at.isoformat(),
        updated_at=incident.updated_at.isoformat(),
    )


@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sla_incident(db: DbSession, incident_id: str) -> None:
    """Delete an SLA incident."""
    repo = SLAIncidentRepository(db)
    incident = await repo.get_by_id(UUID(incident_id))
    if not incident:
        raise NotFoundError("SLAIncident", incident_id)

    await repo.delete(incident)
    await db.commit()
