"""Pydantic schemas for data policies."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class DataPolicyBase(BaseModel):
    """Base schema for data policies."""

    # Classification
    sensitivity_level: str = Field(..., description="Sensitivity level (public, internal, confidential, etc.)")
    classification_tags: list[str] = Field(default_factory=list, description="Classification tags (GDPR, PCI, etc.)")

    # Retention policy
    retention_period_days: Optional[int] = Field(None, description="Retention period in days")
    retention_start: Optional[str] = Field(None, description="Retention start reference (ingestion, last_modified, etc.)")
    deletion_action: Optional[str] = Field(None, description="Deletion action (hard_delete, anonymize, archive)")
    legal_hold: bool = Field(False, description="Whether data is under legal hold")

    # Geographic restrictions
    allowed_regions: list[str] = Field(default_factory=list, description="Allowed regions")
    restricted_regions: list[str] = Field(default_factory=list, description="Restricted regions")
    data_residency: Optional[str] = Field(None, description="Data residency requirement")
    cross_border_transfer: bool = Field(True, description="Whether cross-border transfer is allowed")

    # Access control
    min_access_level: Optional[str] = Field(None, description="Minimum access level required")
    allowed_roles: list[str] = Field(default_factory=list, description="Allowed roles")
    denied_roles: list[str] = Field(default_factory=list, description="Denied roles")

    # Approved uses
    approved_purposes: list[str] = Field(default_factory=list, description="Approved purposes")
    prohibited_purposes: list[str] = Field(default_factory=list, description="Prohibited purposes")

    # Masking/anonymization
    requires_masking: bool = Field(False, description="Whether data requires masking")
    masking_method: Optional[str] = Field(None, description="Masking method")
    masking_conditions: Optional[dict[str, Any]] = Field(None, description="Masking conditions")

    # Encryption
    encryption_required: bool = Field(False, description="Whether encryption is required")
    encryption_method: Optional[str] = Field(None, description="Encryption method")
    encryption_at_rest: bool = Field(False, description="Encryption at rest required")
    encryption_in_transit: bool = Field(True, description="Encryption in transit required")

    # Compliance tracking
    compliance_frameworks: list[str] = Field(default_factory=list, description="Compliance frameworks")
    consent_required: bool = Field(False, description="Whether consent is required")
    right_to_erasure: bool = Field(False, description="Right to erasure (GDPR Article 17)")

    # Audit requirements
    audit_log_required: bool = Field(False, description="Whether audit logging is required")
    audit_retention_days: Optional[int] = Field(None, description="Audit log retention in days")

    # Governance
    policy_owner_id: Optional[str] = Field(None, description="Policy owner ID (UUID)")
    approved_by: Optional[str] = Field(None, description="Approved by")
    approved_at: Optional[str] = Field(None, description="Approval timestamp")
    review_frequency_days: Optional[int] = Field(None, description="Review frequency in days")
    last_reviewed_at: Optional[str] = Field(None, description="Last review timestamp")
    next_review_date: Optional[str] = Field(None, description="Next review date")

    # Status
    policy_status: str = Field("active", description="Policy status (draft, active, deprecated, suspended)")
    effective_from: Optional[str] = Field(None, description="Effective from date")
    effective_to: Optional[str] = Field(None, description="Effective to date")

    # Metadata
    meta: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DataPolicyCreate(DataPolicyBase):
    """Schema for creating a data policy."""

    capsule_id: Optional[str] = Field(None, description="Capsule ID (UUID) - one of capsule_id or column_id required")
    column_id: Optional[str] = Field(None, description="Column ID (UUID) - one of capsule_id or column_id required")


class DataPolicyUpdate(BaseModel):
    """Schema for updating a data policy."""

    sensitivity_level: Optional[str] = None
    classification_tags: Optional[list[str]] = None
    retention_period_days: Optional[int] = None
    retention_start: Optional[str] = None
    deletion_action: Optional[str] = None
    legal_hold: Optional[bool] = None
    allowed_regions: Optional[list[str]] = None
    restricted_regions: Optional[list[str]] = None
    data_residency: Optional[str] = None
    cross_border_transfer: Optional[bool] = None
    min_access_level: Optional[str] = None
    allowed_roles: Optional[list[str]] = None
    denied_roles: Optional[list[str]] = None
    approved_purposes: Optional[list[str]] = None
    prohibited_purposes: Optional[list[str]] = None
    requires_masking: Optional[bool] = None
    masking_method: Optional[str] = None
    masking_conditions: Optional[dict[str, Any]] = None
    encryption_required: Optional[bool] = None
    encryption_method: Optional[str] = None
    encryption_at_rest: Optional[bool] = None
    encryption_in_transit: Optional[bool] = None
    compliance_frameworks: Optional[list[str]] = None
    consent_required: Optional[bool] = None
    right_to_erasure: Optional[bool] = None
    audit_log_required: Optional[bool] = None
    audit_retention_days: Optional[int] = None
    policy_owner_id: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    review_frequency_days: Optional[int] = None
    last_reviewed_at: Optional[str] = None
    next_review_date: Optional[str] = None
    policy_status: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class DataPolicySummary(BaseModel):
    """Summary view of a data policy."""

    id: str
    capsule_id: Optional[str] = None
    column_id: Optional[str] = None
    sensitivity_level: str
    classification_tags: list[str]
    policy_status: str
    requires_masking: bool
    encryption_required: bool

    class Config:
        from_attributes = True


class DataPolicyDetail(DataPolicyBase):
    """Detailed view of a data policy."""

    id: str
    capsule_id: Optional[str] = None
    column_id: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class DataPolicyListResponse(BaseModel):
    """Response for data policy list."""

    data: list[DataPolicySummary]
    pagination: dict
