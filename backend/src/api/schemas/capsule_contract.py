"""Pydantic schemas for capsule contracts."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, Field


class CapsuleContractBase(BaseModel):
    """Base schema for capsule contracts."""

    contract_version: str = Field(..., description="Contract version")
    contract_status: str = Field("active", description="Contract status (draft, proposed, active, deprecated, breached)")

    # Freshness SLA
    freshness_sla: Optional[timedelta] = Field(None, description="Freshness SLA (e.g., 4 hours)")
    freshness_schedule: Optional[str] = Field(None, description="Freshness schedule (hourly, daily_8am, cron:...)")
    last_updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # Completeness SLA
    completeness_sla: Optional[Decimal] = Field(None, description="Expected completeness percentage (e.g., 99.9)")
    expected_row_count_min: Optional[int] = Field(None, description="Minimum expected row count")
    expected_row_count_max: Optional[int] = Field(None, description="Maximum expected row count")

    # Availability SLA
    availability_sla: Optional[Decimal] = Field(None, description="Uptime percentage (e.g., 99.9)")
    max_downtime: Optional[timedelta] = Field(None, description="Maximum downtime per period")

    # Quality SLA
    quality_score_sla: Optional[Decimal] = Field(None, description="Minimum quality score (0-100)")
    critical_quality_rules: list[str] = Field(default_factory=list, description="Critical rule IDs that must pass")

    # Latency SLA
    query_latency_p95: Optional[int] = Field(None, description="P95 query latency in ms")
    query_latency_p99: Optional[int] = Field(None, description="P99 query latency in ms")

    # Schema stability
    schema_change_policy: Optional[str] = Field(None, description="Schema change policy (strict, backwards_compatible, flexible, unrestricted)")
    breaking_change_notice_days: Optional[int] = Field(None, description="Days of notice before breaking change")

    # Support
    support_level: Optional[str] = Field(None, description="Support level (none, best_effort, business_hours, 24x7, critical)")
    support_contact: Optional[str] = Field(None, description="Support contact")
    support_slack_channel: Optional[str] = Field(None, description="Support Slack channel")
    support_oncall: Optional[str] = Field(None, description="On-call contact")

    # Maintenance windows
    maintenance_windows: list[dict[str, Any]] = Field(default_factory=list, description="Maintenance windows")

    # Deprecation
    deprecation_policy: Optional[str] = Field(None, description="Deprecation policy (immediate, 30_days, 90_days, never)")
    deprecation_date: Optional[date] = Field(None, description="Deprecation date")
    replacement_capsule_urn: Optional[str] = Field(None, description="Replacement capsule URN")

    # Consumers
    known_consumers: list[dict[str, Any]] = Field(default_factory=list, description="Known consumers")
    consumer_notification_required: bool = Field(True, description="Whether to notify consumers")

    # Performance targets
    target_row_count: Optional[int] = Field(None, description="Target row count")
    target_size_bytes: Optional[int] = Field(None, description="Target size in bytes")
    target_column_count: Optional[int] = Field(None, description="Target column count")

    # Cost allocation
    cost_center: Optional[str] = Field(None, description="Cost center")
    billing_tags: dict[str, Any] = Field(default_factory=dict, description="Billing tags")

    # Metadata
    meta: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Governance
    contract_owner_id: Optional[str] = Field(None, description="Contract owner ID (UUID)")
    approved_by: Optional[str] = Field(None, description="Approver name")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")


class CapsuleContractCreate(CapsuleContractBase):
    """Schema for creating a capsule contract."""

    capsule_id: str = Field(..., description="Capsule ID (UUID)")


class CapsuleContractUpdate(BaseModel):
    """Schema for updating a capsule contract."""

    contract_status: Optional[str] = None
    freshness_sla: Optional[timedelta] = None
    freshness_schedule: Optional[str] = None
    last_updated_at: Optional[datetime] = None
    completeness_sla: Optional[Decimal] = None
    expected_row_count_min: Optional[int] = None
    expected_row_count_max: Optional[int] = None
    availability_sla: Optional[Decimal] = None
    max_downtime: Optional[timedelta] = None
    quality_score_sla: Optional[Decimal] = None
    critical_quality_rules: Optional[list[str]] = None
    query_latency_p95: Optional[int] = None
    query_latency_p99: Optional[int] = None
    schema_change_policy: Optional[str] = None
    breaking_change_notice_days: Optional[int] = None
    support_level: Optional[str] = None
    support_contact: Optional[str] = None
    support_slack_channel: Optional[str] = None
    support_oncall: Optional[str] = None
    maintenance_windows: Optional[list[dict[str, Any]]] = None
    deprecation_policy: Optional[str] = None
    deprecation_date: Optional[date] = None
    replacement_capsule_urn: Optional[str] = None
    known_consumers: Optional[list[dict[str, Any]]] = None
    consumer_notification_required: Optional[bool] = None
    target_row_count: Optional[int] = None
    target_size_bytes: Optional[int] = None
    target_column_count: Optional[int] = None
    cost_center: Optional[str] = None
    billing_tags: Optional[dict[str, Any]] = None
    meta: Optional[dict[str, Any]] = None
    contract_owner_id: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


class CapsuleContractSummary(BaseModel):
    """Summary view of a capsule contract."""

    id: str
    capsule_id: str
    contract_version: str
    contract_status: str
    support_level: Optional[str] = None
    deprecation_date: Optional[date] = None
    created_at: str

    class Config:
        from_attributes = True


class CapsuleContractDetail(CapsuleContractBase):
    """Detailed view of a capsule contract."""

    id: str
    capsule_id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CapsuleContractListResponse(BaseModel):
    """Response for capsule contract list."""

    data: list[CapsuleContractSummary]
    pagination: dict
