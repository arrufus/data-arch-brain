"""Compliance endpoints for PII tracking."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_session
from src.api.exceptions import NotFoundError
from src.services.compliance import ComplianceService, PIISeverity

router = APIRouter(prefix="/compliance")


class PIIColumnResponse(BaseModel):
    """PII column details."""

    column_id: str
    column_urn: str
    column_name: str
    pii_type: str
    pii_detected_by: Optional[str]
    capsule_id: str
    capsule_urn: str
    capsule_name: str
    capsule_layer: Optional[str]
    data_type: Optional[str]
    description: Optional[str]


class PIITypeSummaryResponse(BaseModel):
    """Summary of PII for a specific type."""

    pii_type: str
    column_count: int
    capsule_count: int
    layers: list[str]
    columns: list[PIIColumnResponse]


class PIILayerSummaryResponse(BaseModel):
    """Summary of PII for a specific layer."""

    layer: str
    column_count: int
    capsule_count: int
    pii_types: list[str]


class PIIInventorySummary(BaseModel):
    """Summary of PII inventory."""

    total_pii_columns: int
    capsules_with_pii: int
    pii_types_found: list[str]


class PIIInventoryResponse(BaseModel):
    """PII inventory response."""

    summary: PIIInventorySummary
    by_pii_type: list[PIITypeSummaryResponse]
    by_layer: list[PIILayerSummaryResponse]


class PIIExposureItem(BaseModel):
    """A PII exposure finding."""

    column_id: str
    column_urn: str
    column_name: str
    pii_type: str
    capsule_id: str
    capsule_urn: str
    capsule_name: str
    layer: str
    severity: str
    reason: str
    recommendation: str
    lineage_path: list[str]


class PIIExposureResponse(BaseModel):
    """PII exposure report response."""

    summary: dict
    exposures: list[PIIExposureItem]


class PIITraceNodeResponse(BaseModel):
    """A node in the PII trace path."""

    column_urn: str
    column_name: str
    capsule_urn: str
    capsule_name: str
    layer: Optional[str]
    pii_type: Optional[str]
    transformation: Optional[str]


class PIITraceResponse(BaseModel):
    """PII trace response."""

    column: PIIColumnResponse
    origin: Optional[PIITraceNodeResponse]
    propagation_path: list[PIITraceNodeResponse]
    terminals: list[PIITraceNodeResponse]
    is_masked_at_terminal: bool
    total_downstream_consumers: int


@router.get("/pii-inventory", response_model=PIIInventoryResponse)
async def get_pii_inventory(
    pii_type: Optional[str] = Query(None, description="Filter by PII type"),
    layer: Optional[str] = Query(None, description="Filter by layer"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    session: AsyncSession = Depends(get_session),
) -> PIIInventoryResponse:
    """Get PII inventory report.

    Returns a comprehensive inventory of all PII columns detected in the
    data architecture, grouped by PII type and layer.
    """
    service = ComplianceService(session)
    inventory = await service.get_pii_inventory(
        pii_type=pii_type,
        layer=layer,
        domain=domain,
    )

    # Convert to response format
    by_pii_type = [
        PIITypeSummaryResponse(
            pii_type=summary.pii_type,
            column_count=summary.column_count,
            capsule_count=summary.capsule_count,
            layers=summary.layers,
            columns=[
                PIIColumnResponse(
                    column_id=str(c.column_id),
                    column_urn=c.column_urn,
                    column_name=c.column_name,
                    pii_type=c.pii_type,
                    pii_detected_by=c.pii_detected_by,
                    capsule_id=str(c.capsule_id),
                    capsule_urn=c.capsule_urn,
                    capsule_name=c.capsule_name,
                    capsule_layer=c.capsule_layer,
                    data_type=c.data_type,
                    description=c.description,
                )
                for c in summary.columns
            ],
        )
        for summary in inventory.by_pii_type
    ]

    by_layer = [
        PIILayerSummaryResponse(
            layer=summary.layer,
            column_count=summary.column_count,
            capsule_count=summary.capsule_count,
            pii_types=summary.pii_types,
        )
        for summary in inventory.by_layer
    ]

    return PIIInventoryResponse(
        summary=PIIInventorySummary(
            total_pii_columns=inventory.total_pii_columns,
            capsules_with_pii=inventory.capsules_with_pii,
            pii_types_found=inventory.pii_types_found,
        ),
        by_pii_type=by_pii_type,
        by_layer=by_layer,
    )


@router.get("/pii-exposure", response_model=PIIExposureResponse)
async def get_pii_exposure(
    layer: Optional[str] = Query(None, description="Layer to check (default: gold/marts)"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    session: AsyncSession = Depends(get_session),
) -> PIIExposureResponse:
    """Get PII exposure report (unmasked PII in consumption layers).

    Identifies PII columns that are exposed (not masked/hashed/encrypted)
    in consumption/gold layers, which may represent a compliance risk.
    """
    service = ComplianceService(session)

    # Convert severity string to enum if provided
    severity_enum = None
    if severity:
        try:
            severity_enum = PIISeverity(severity.lower())
        except ValueError:
            from src.api.exceptions import ValidationError_
            raise ValidationError_(
                f"Invalid severity: {severity}. Must be one of: critical, high, medium, low",
                field="severity"
            )

    report = await service.detect_pii_exposure(
        layer=layer,
        severity=severity_enum,
    )

    exposures = [
        PIIExposureItem(
            column_id=str(e.column_id),
            column_urn=e.column_urn,
            column_name=e.column_name,
            pii_type=e.pii_type,
            capsule_id=str(e.capsule_id),
            capsule_urn=e.capsule_urn,
            capsule_name=e.capsule_name,
            layer=e.layer,
            severity=e.severity.value,
            reason=e.reason,
            recommendation=e.recommendation,
            lineage_path=e.lineage_path,
        )
        for e in report.exposures
    ]

    return PIIExposureResponse(
        summary={
            "exposed_pii_columns": report.exposed_pii_columns,
            "affected_capsules": report.affected_capsules,
            "severity_breakdown": report.severity_breakdown,
        },
        exposures=exposures,
    )


@router.get("/pii-trace/{column_urn:path}", response_model=PIITraceResponse)
async def trace_pii_column(
    column_urn: str,
    max_depth: int = Query(10, description="Maximum depth to trace", ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> PIITraceResponse:
    """Trace a PII column through the data pipeline.

    Shows the complete lineage of a PII column from its origin (source)
    to all terminal nodes (consumers), including any transformations
    applied along the way.
    """
    service = ComplianceService(session)
    trace = await service.trace_pii_column(column_urn, max_depth=max_depth)

    if not trace:
        raise NotFoundError("Column", column_urn)

    return PIITraceResponse(
        column=PIIColumnResponse(
            column_id=str(trace.column.column_id),
            column_urn=trace.column.column_urn,
            column_name=trace.column.column_name,
            pii_type=trace.column.pii_type,
            pii_detected_by=trace.column.pii_detected_by,
            capsule_id=str(trace.column.capsule_id),
            capsule_urn=trace.column.capsule_urn,
            capsule_name=trace.column.capsule_name,
            capsule_layer=trace.column.capsule_layer,
            data_type=trace.column.data_type,
            description=trace.column.description,
        ),
        origin=PIITraceNodeResponse(
            column_urn=trace.origin.column_urn,
            column_name=trace.origin.column_name,
            capsule_urn=trace.origin.capsule_urn,
            capsule_name=trace.origin.capsule_name,
            layer=trace.origin.layer,
            pii_type=trace.origin.pii_type,
            transformation=trace.origin.transformation,
        ) if trace.origin else None,
        propagation_path=[
            PIITraceNodeResponse(
                column_urn=n.column_urn,
                column_name=n.column_name,
                capsule_urn=n.capsule_urn,
                capsule_name=n.capsule_name,
                layer=n.layer,
                pii_type=n.pii_type,
                transformation=n.transformation,
            )
            for n in trace.propagation_path
        ],
        terminals=[
            PIITraceNodeResponse(
                column_urn=n.column_urn,
                column_name=n.column_name,
                capsule_urn=n.capsule_urn,
                capsule_name=n.capsule_name,
                layer=n.layer,
                pii_type=n.pii_type,
                transformation=n.transformation,
            )
            for n in trace.terminals
        ],
        is_masked_at_terminal=trace.is_masked_at_terminal,
        total_downstream_consumers=trace.total_downstream_consumers,
    )
