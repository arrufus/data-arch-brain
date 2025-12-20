"""Pydantic schemas for capsule indexes."""

from typing import Optional
from pydantic import BaseModel, Field


class CapsuleIndexBase(BaseModel):
    """Base schema for capsule indexes."""

    index_name: str = Field(..., description="Name of the index")
    index_type: str = Field("btree", description="Type of index")
    is_unique: bool = Field(False, description="Whether index is unique")
    is_primary: bool = Field(False, description="Whether this is primary key index")
    column_names: list[str] = Field(..., description="Column names in the index")
    column_expressions: Optional[list[str]] = Field(None, description="Column expressions for expression indexes")
    is_partial: bool = Field(False, description="Whether this is a partial index")
    partial_predicate: Optional[str] = Field(None, description="WHERE clause for partial index")
    tablespace: Optional[str] = Field(None, description="Tablespace name")
    fill_factor: Optional[int] = Field(None, ge=10, le=100, description="Index fill factor")
    meta: dict = Field(default_factory=dict, description="Additional metadata")


class CapsuleIndexCreate(CapsuleIndexBase):
    """Schema for creating a capsule index."""

    capsule_id: str = Field(..., description="Capsule ID (UUID)")


class CapsuleIndexUpdate(BaseModel):
    """Schema for updating a capsule index."""

    is_unique: Optional[bool] = None
    fill_factor: Optional[int] = Field(None, ge=10, le=100)
    meta: Optional[dict] = None


class CapsuleIndexSummary(BaseModel):
    """Summary view of a capsule index."""

    id: str
    capsule_id: str
    index_name: str
    index_type: str
    is_unique: bool
    is_primary: bool
    column_names: list[str]

    class Config:
        from_attributes = True


class CapsuleIndexDetail(CapsuleIndexBase):
    """Detailed view of a capsule index."""

    id: str
    capsule_id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CapsuleIndexListResponse(BaseModel):
    """Response for capsule index list."""

    data: list[CapsuleIndexSummary]
    pagination: dict
