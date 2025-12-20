"""Pydantic schemas for business terms."""

from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class BusinessTermBase(BaseModel):
    """Base schema for business terms."""

    term_name: str = Field(..., min_length=1, max_length=255, description="Unique term name")
    display_name: Optional[str] = Field(None, max_length=255, description="Display name")
    definition: str = Field(..., min_length=10, description="Term definition")
    abbreviation: Optional[str] = Field(None, max_length=50, description="Abbreviation")
    synonyms: list[str] = Field(default_factory=list, description="Alternative names")
    category: Optional[str] = Field(None, max_length=100, description="Category grouping")
    steward_email: Optional[EmailStr] = Field(None, description="Data steward email")
    tags: list[str] = Field(default_factory=list, description="Classification tags")
    meta: dict = Field(default_factory=dict, description="Additional metadata")


class BusinessTermCreate(BusinessTermBase):
    """Schema for creating a business term."""

    domain_id: Optional[str] = Field(None, description="Domain ID (UUID)")
    owner_id: Optional[str] = Field(None, description="Owner ID (UUID)")


class BusinessTermUpdate(BaseModel):
    """Schema for updating a business term."""

    display_name: Optional[str] = None
    definition: Optional[str] = Field(None, min_length=10)
    abbreviation: Optional[str] = None
    synonyms: Optional[list[str]] = None
    category: Optional[str] = None
    domain_id: Optional[str] = None
    owner_id: Optional[str] = None
    steward_email: Optional[EmailStr] = None
    approval_status: Optional[str] = Field(None, pattern="^(draft|under_review|approved|deprecated)$")
    tags: Optional[list[str]] = None
    meta: Optional[dict] = None


class BusinessTermSummary(BaseModel):
    """Summary view of a business term."""

    id: str
    term_name: str
    display_name: Optional[str] = None
    definition: str
    abbreviation: Optional[str] = None
    category: Optional[str] = None
    approval_status: str
    domain_name: Optional[str] = None
    owner_name: Optional[str] = None

    class Config:
        from_attributes = True


class BusinessTermDetail(BusinessTermBase):
    """Detailed view of a business term."""

    id: str
    domain_id: Optional[str] = None
    domain_name: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    approval_status: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class BusinessTermListResponse(BaseModel):
    """Response for business term list."""

    data: list[BusinessTermSummary]
    pagination: dict


class CapsuleBusinessTermCreate(BaseModel):
    """Schema for linking a capsule to a business term."""

    capsule_id: str = Field(..., description="Capsule ID (UUID)")
    business_term_id: str = Field(..., description="Business Term ID (UUID)")
    relationship_type: str = Field(
        "implements",
        pattern="^(implements|related_to|example_of|measures|derived_from)$",
        description="Relationship type"
    )
    added_by: Optional[str] = Field(None, description="Who added this link")
    meta: dict = Field(default_factory=dict, description="Additional metadata")


class ColumnBusinessTermCreate(BaseModel):
    """Schema for linking a column to a business term."""

    column_id: str = Field(..., description="Column ID (UUID)")
    business_term_id: str = Field(..., description="Business Term ID (UUID)")
    relationship_type: str = Field(
        "implements",
        pattern="^(implements|related_to|example_of|measures|derived_from)$",
        description="Relationship type"
    )
    added_by: Optional[str] = Field(None, description="Who added this link")
    meta: dict = Field(default_factory=dict, description="Additional metadata")


class BusinessTermApprovalRequest(BaseModel):
    """Schema for approving a business term."""

    approved_by: str = Field(..., description="Who approved the term")
    approval_status: str = Field(
        "approved",
        pattern="^(under_review|approved|deprecated)$",
        description="New approval status"
    )
