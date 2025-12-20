"""Pydantic schemas for value domains."""

from typing import Optional, Any
from pydantic import BaseModel, Field


class ValueDomainBase(BaseModel):
    """Base schema for value domains."""

    domain_name: str = Field(..., min_length=1, max_length=255, description="Unique domain name")
    domain_type: str = Field(
        ...,
        pattern="^(enum|pattern|range|reference_data)$",
        description="Type of domain"
    )
    description: Optional[str] = Field(None, description="Domain description")
    is_extensible: bool = Field(False, description="Whether new values can be added")
    meta: dict = Field(default_factory=dict, description="Additional metadata")


class ValueDomainCreate(ValueDomainBase):
    """Schema for creating a value domain."""

    # For enum domains
    allowed_values: Optional[list[dict[str, Any]]] = Field(
        None,
        description="Allowed values with labels/descriptions"
    )

    # For pattern domains
    pattern_regex: Optional[str] = Field(None, description="Validation regex")
    pattern_description: Optional[str] = Field(None, description="Pattern description")

    # For range domains
    min_value: Optional[str] = Field(None, description="Minimum value")
    max_value: Optional[str] = Field(None, description="Maximum value")

    # For reference data domains
    reference_table_urn: Optional[str] = Field(None, description="Referenced table URN")
    reference_column_urn: Optional[str] = Field(None, description="Referenced column URN")

    # Ownership
    owner_id: Optional[str] = Field(None, description="Owner ID (UUID)")


class ValueDomainUpdate(BaseModel):
    """Schema for updating a value domain."""

    description: Optional[str] = None
    allowed_values: Optional[list[dict[str, Any]]] = None
    pattern_regex: Optional[str] = None
    pattern_description: Optional[str] = None
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    reference_table_urn: Optional[str] = None
    reference_column_urn: Optional[str] = None
    owner_id: Optional[str] = None
    is_extensible: Optional[bool] = None
    meta: Optional[dict] = None


class ValueDomainSummary(BaseModel):
    """Summary view of a value domain."""

    id: str
    domain_name: str
    domain_type: str
    description: Optional[str] = None
    is_extensible: bool
    owner_name: Optional[str] = None
    value_count: int = 0

    class Config:
        from_attributes = True


class ValueDomainDetail(ValueDomainBase):
    """Detailed view of a value domain."""

    id: str
    allowed_values: Optional[list[dict[str, Any]]] = None
    pattern_regex: Optional[str] = None
    pattern_description: Optional[str] = None
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    reference_table_urn: Optional[str] = None
    reference_column_urn: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ValueDomainListResponse(BaseModel):
    """Response for value domain list."""

    data: list[ValueDomainSummary]
    pagination: dict


class ValueValidationRequest(BaseModel):
    """Schema for validating a value against a domain."""

    value: str = Field(..., description="Value to validate")


class ValueValidationResponse(BaseModel):
    """Response for value validation."""

    valid: bool
    message: Optional[str] = None
    domain_name: str
    domain_type: str
