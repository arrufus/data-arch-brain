"""Pydantic schemas for quality rules."""

from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, Field


class QualityRuleBase(BaseModel):
    """Base schema for quality rules."""

    rule_name: str = Field(..., description="Name of the quality rule")
    rule_type: str = Field(..., description="Type of rule (not_null, pattern_match, etc.)")
    rule_category: Optional[str] = Field(None, description="Category (completeness, validity, etc.)")
    rule_config: dict[str, Any] = Field(..., description="Rule configuration (JSONB)")
    threshold_value: Optional[Decimal] = Field(None, description="Threshold numeric value")
    threshold_operator: Optional[str] = Field(None, description="Threshold operator (>, >=, <, <=, =, !=)")
    threshold_percent: Optional[Decimal] = Field(None, description="Threshold percentage")
    expected_value: Optional[str] = Field(None, description="Expected value")
    expected_range_min: Optional[Decimal] = Field(None, description="Expected minimum value")
    expected_range_max: Optional[Decimal] = Field(None, description="Expected maximum value")
    expected_pattern: Optional[str] = Field(None, description="Expected regex pattern")
    severity: str = Field("warning", description="Severity level (info, warning, error, critical)")
    blocking: bool = Field(False, description="Whether rule blocks pipeline on failure")
    is_enabled: bool = Field(True, description="Whether rule is enabled")
    description: Optional[str] = Field(None, description="Rule description")
    meta: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class QualityRuleCreate(QualityRuleBase):
    """Schema for creating a quality rule."""

    capsule_id: Optional[str] = Field(None, description="Capsule ID (UUID) - one of capsule_id or column_id required")
    column_id: Optional[str] = Field(None, description="Column ID (UUID) - one of capsule_id or column_id required")


class QualityRuleUpdate(BaseModel):
    """Schema for updating a quality rule."""

    rule_name: Optional[str] = None
    rule_category: Optional[str] = None
    rule_config: Optional[dict[str, Any]] = None
    threshold_value: Optional[Decimal] = None
    threshold_operator: Optional[str] = None
    threshold_percent: Optional[Decimal] = None
    expected_value: Optional[str] = None
    expected_range_min: Optional[Decimal] = None
    expected_range_max: Optional[Decimal] = None
    expected_pattern: Optional[str] = None
    severity: Optional[str] = None
    blocking: Optional[bool] = None
    is_enabled: Optional[bool] = None
    description: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class QualityRuleSummary(BaseModel):
    """Summary view of a quality rule."""

    id: str
    capsule_id: Optional[str] = None
    column_id: Optional[str] = None
    rule_name: str
    rule_type: str
    rule_category: Optional[str] = None
    severity: str
    is_enabled: bool

    class Config:
        from_attributes = True


class QualityRuleDetail(QualityRuleBase):
    """Detailed view of a quality rule."""

    id: str
    capsule_id: Optional[str] = None
    column_id: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class QualityRuleListResponse(BaseModel):
    """Response for quality rule list."""

    data: list[QualityRuleSummary]
    pagination: dict
