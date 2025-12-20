"""Pydantic schemas for masking rules."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class MaskingRuleBase(BaseModel):
    """Base schema for masking rules."""

    rule_name: str = Field(..., description="Name of the masking rule")
    masking_method: str = Field(..., description="Masking method (redaction, hashing, tokenization, etc.)")
    method_config: dict[str, Any] = Field(..., description="Method-specific configuration")

    # Conditional masking
    apply_condition: Optional[str] = Field(None, description="SQL WHERE clause for conditional masking")
    applies_to_roles: list[str] = Field(default_factory=list, description="Roles that see masked data")
    exempt_roles: list[str] = Field(default_factory=list, description="Roles that see unmasked data")

    # Preservation options
    preserve_length: bool = Field(False, description="Preserve original data length")
    preserve_format: bool = Field(False, description="Preserve original data format")
    preserve_type: bool = Field(True, description="Preserve original data type")
    preserve_null: bool = Field(True, description="Preserve null values")

    # Reversibility
    is_reversible: bool = Field(False, description="Whether masking is reversible")
    tokenization_vault: Optional[str] = Field(None, description="Token vault reference")

    # Status
    is_enabled: bool = Field(True, description="Whether rule is enabled")

    # Metadata
    description: Optional[str] = Field(None, description="Rule description")
    meta: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class MaskingRuleCreate(MaskingRuleBase):
    """Schema for creating a masking rule."""

    column_id: str = Field(..., description="Column ID (UUID)")


class MaskingRuleUpdate(BaseModel):
    """Schema for updating a masking rule."""

    rule_name: Optional[str] = None
    masking_method: Optional[str] = None
    method_config: Optional[dict[str, Any]] = None
    apply_condition: Optional[str] = None
    applies_to_roles: Optional[list[str]] = None
    exempt_roles: Optional[list[str]] = None
    preserve_length: Optional[bool] = None
    preserve_format: Optional[bool] = None
    preserve_type: Optional[bool] = None
    preserve_null: Optional[bool] = None
    is_reversible: Optional[bool] = None
    tokenization_vault: Optional[str] = None
    is_enabled: Optional[bool] = None
    description: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class MaskingRuleSummary(BaseModel):
    """Summary view of a masking rule."""

    id: str
    column_id: str
    rule_name: str
    masking_method: str
    is_enabled: bool
    is_reversible: bool

    class Config:
        from_attributes = True


class MaskingRuleDetail(MaskingRuleBase):
    """Detailed view of a masking rule."""

    id: str
    column_id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class MaskingRuleListResponse(BaseModel):
    """Response for masking rule list."""

    data: list[MaskingRuleSummary]
    pagination: dict
