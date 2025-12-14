"""API router for violation management."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_session
from src.models.violation import ViolationStatus
from src.repositories.violation import ViolationRepository
from src.services.conformance import ConformanceService

router = APIRouter(prefix="/violations", tags=["violations"])


# Pydantic models for API
class ViolationResponse(BaseModel):
    """Response model for a single violation."""
    
    id: UUID
    rule_id: UUID
    rule_name: Optional[str] = None
    capsule_id: Optional[UUID] = None
    capsule_urn: Optional[str] = None
    column_id: Optional[UUID] = None
    column_name: Optional[str] = None
    severity: str
    message: str
    details: dict = Field(default_factory=dict)
    status: str
    detected_at: str
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    
    class Config:
        from_attributes = True


class ViolationListResponse(BaseModel):
    """Response model for listing violations."""
    
    violations: list[ViolationResponse]
    total: int
    offset: int
    limit: int


class ViolationSummaryResponse(BaseModel):
    """Response model for violation summary."""
    
    open_violations: int
    by_severity: dict[str, int]
    by_category: dict[str, int]


class UpdateViolationStatusRequest(BaseModel):
    """Request model for updating violation status."""
    
    status: ViolationStatus
    resolved_by: Optional[str] = None


class BulkUpdateStatusRequest(BaseModel):
    """Request model for bulk updating violation status."""
    
    violation_ids: list[UUID]
    status: ViolationStatus
    resolved_by: Optional[str] = None


class BulkUpdateResponse(BaseModel):
    """Response model for bulk update operations."""
    
    updated_count: int


def _violation_to_response(violation) -> ViolationResponse:
    """Convert a Violation model to a response."""
    return ViolationResponse(
        id=violation.id,
        rule_id=violation.rule_id,
        rule_name=violation.rule.name if violation.rule else None,
        capsule_id=violation.capsule_id,
        capsule_urn=violation.capsule.urn if violation.capsule else None,
        column_id=violation.column_id,
        column_name=violation.column.name if violation.column else None,
        severity=violation.severity,
        message=violation.message,
        details=violation.details or {},
        status=violation.status,
        detected_at=violation.detected_at.isoformat() if violation.detected_at else None,
        resolved_at=violation.resolved_at.isoformat() if violation.resolved_at else None,
        resolved_by=violation.resolved_by,
    )


@router.get("", response_model=ViolationListResponse)
async def list_violations(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    category: Optional[str] = Query(None, description="Filter by rule category"),
    rule_set: Optional[str] = Query(None, description="Filter by rule set"),
    capsule_id: Optional[UUID] = Query(None, description="Filter by capsule ID"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> ViolationListResponse:
    """List violations with optional filters."""
    repo = ViolationRepository(session)
    
    violations = await repo.list_violations(
        status=status,
        severity=severity,
        category=category,
        rule_set=rule_set,
        capsule_id=capsule_id,
        limit=limit,
        offset=offset,
    )
    
    total = await repo.count_violations(status=status, severity=severity)
    
    return ViolationListResponse(
        violations=[_violation_to_response(v) for v in violations],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/summary", response_model=ViolationSummaryResponse)
async def get_violation_summary(
    session: AsyncSession = Depends(get_session),
) -> ViolationSummaryResponse:
    """Get summary statistics about violations."""
    service = ConformanceService(session)
    summary = await service.get_violation_summary()
    return ViolationSummaryResponse(**summary)


@router.get("/{violation_id}", response_model=ViolationResponse)
async def get_violation(
    violation_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ViolationResponse:
    """Get a specific violation by ID."""
    repo = ViolationRepository(session)
    violation = await repo.get_by_id(violation_id)
    
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    
    return _violation_to_response(violation)


@router.patch("/{violation_id}/status", response_model=ViolationResponse)
async def update_violation_status(
    violation_id: UUID,
    request: UpdateViolationStatusRequest,
    session: AsyncSession = Depends(get_session),
) -> ViolationResponse:
    """Update the status of a violation."""
    repo = ViolationRepository(session)
    
    violation = await repo.update_status(
        violation_id=violation_id,
        status=request.status,
        resolved_by=request.resolved_by,
    )
    
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    
    await session.commit()
    return _violation_to_response(violation)


@router.post("/{violation_id}/acknowledge", response_model=ViolationResponse)
async def acknowledge_violation(
    violation_id: UUID,
    resolved_by: Optional[str] = Query(None, description="Who is acknowledging"),
    session: AsyncSession = Depends(get_session),
) -> ViolationResponse:
    """Acknowledge a violation."""
    repo = ViolationRepository(session)
    
    violation = await repo.update_status(
        violation_id=violation_id,
        status=ViolationStatus.ACKNOWLEDGED,
        resolved_by=resolved_by,
    )
    
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    
    await session.commit()
    return _violation_to_response(violation)


@router.post("/{violation_id}/resolve", response_model=ViolationResponse)
async def resolve_violation(
    violation_id: UUID,
    resolved_by: Optional[str] = Query(None, description="Who is resolving"),
    session: AsyncSession = Depends(get_session),
) -> ViolationResponse:
    """Resolve a violation."""
    repo = ViolationRepository(session)
    
    violation = await repo.update_status(
        violation_id=violation_id,
        status=ViolationStatus.RESOLVED,
        resolved_by=resolved_by,
    )
    
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    
    await session.commit()
    return _violation_to_response(violation)


@router.post("/{violation_id}/false-positive", response_model=ViolationResponse)
async def mark_false_positive(
    violation_id: UUID,
    resolved_by: Optional[str] = Query(None, description="Who is marking as false positive"),
    session: AsyncSession = Depends(get_session),
) -> ViolationResponse:
    """Mark a violation as a false positive."""
    repo = ViolationRepository(session)
    
    violation = await repo.update_status(
        violation_id=violation_id,
        status=ViolationStatus.FALSE_POSITIVE,
        resolved_by=resolved_by,
    )
    
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    
    await session.commit()
    return _violation_to_response(violation)


@router.post("/bulk/status", response_model=BulkUpdateResponse)
async def bulk_update_status(
    request: BulkUpdateStatusRequest,
    session: AsyncSession = Depends(get_session),
) -> BulkUpdateResponse:
    """Update status for multiple violations at once."""
    repo = ViolationRepository(session)
    
    count = await repo.bulk_update_status(
        violation_ids=request.violation_ids,
        status=request.status,
        resolved_by=request.resolved_by,
    )
    
    await session.commit()
    return BulkUpdateResponse(updated_count=count)
