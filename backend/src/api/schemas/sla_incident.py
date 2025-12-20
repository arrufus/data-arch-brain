"""Pydantic schemas for SLA incidents."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, Field


class SLAIncidentBase(BaseModel):
    """Base schema for SLA incidents."""

    incident_type: str = Field(..., description="Incident type (freshness, completeness, availability, quality, latency, schema_change)")
    incident_severity: str = Field("medium", description="Incident severity (low, medium, high, critical)")

    # What was violated
    sla_target: Optional[Decimal] = Field(None, description="SLA target value")
    actual_value: Optional[Decimal] = Field(None, description="Actual value observed")
    breach_magnitude: Optional[Decimal] = Field(None, description="Magnitude of SLA breach")

    # Timeline
    breach_started_at: Optional[datetime] = Field(None, description="When breach started")
    breach_ended_at: Optional[datetime] = Field(None, description="When breach ended")
    breach_duration: Optional[timedelta] = Field(None, description="Duration of breach")

    # Impact
    affected_consumers: list[dict[str, Any]] = Field(default_factory=list, description="Affected consumers")
    downstream_impact: Optional[str] = Field(None, description="Description of downstream impact")

    # Resolution
    incident_status: str = Field("open", description="Incident status (open, investigating, mitigated, resolved, closed, false_positive)")
    resolution: Optional[str] = Field(None, description="Resolution description")
    resolved_by: Optional[str] = Field(None, description="Who resolved the incident")
    resolved_at: Optional[datetime] = Field(None, description="When incident was resolved")

    # Root cause
    root_cause: Optional[str] = Field(None, description="Root cause description")
    root_cause_category: Optional[str] = Field(None, description="Root cause category (pipeline_failure, data_quality, infrastructure, dependency)")

    # Metadata
    meta: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SLAIncidentCreate(SLAIncidentBase):
    """Schema for creating an SLA incident."""

    contract_id: str = Field(..., description="Contract ID (UUID)")
    capsule_id: str = Field(..., description="Capsule ID (UUID)")


class SLAIncidentUpdate(BaseModel):
    """Schema for updating an SLA incident."""

    incident_severity: Optional[str] = None
    breach_ended_at: Optional[datetime] = None
    breach_duration: Optional[timedelta] = None
    affected_consumers: Optional[list[dict[str, Any]]] = None
    downstream_impact: Optional[str] = None
    incident_status: Optional[str] = None
    resolution: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    root_cause: Optional[str] = None
    root_cause_category: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class SLAIncidentSummary(BaseModel):
    """Summary view of an SLA incident."""

    id: str
    contract_id: str
    capsule_id: str
    incident_type: str
    incident_severity: str
    incident_status: str
    detected_at: str
    resolved_at: Optional[str] = None

    class Config:
        from_attributes = True


class SLAIncidentDetail(SLAIncidentBase):
    """Detailed view of an SLA incident."""

    id: str
    contract_id: str
    capsule_id: str
    detected_at: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SLAIncidentListResponse(BaseModel):
    """Response for SLA incident list."""

    data: list[SLAIncidentSummary]
    pagination: dict
