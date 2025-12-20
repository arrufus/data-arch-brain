"""Pydantic schemas for column constraints."""

from typing import Optional
from pydantic import BaseModel, Field


class ColumnConstraintBase(BaseModel):
    """Base schema for column constraints."""

    constraint_type: str = Field(..., description="Type of constraint")
    constraint_name: Optional[str] = Field(None, description="Name of the constraint")
    referenced_table_urn: Optional[str] = Field(None, description="Referenced table URN (for FKs)")
    referenced_column_urn: Optional[str] = Field(None, description="Referenced column URN (for FKs)")
    on_delete_action: Optional[str] = Field(None, description="ON DELETE action")
    on_update_action: Optional[str] = Field(None, description="ON UPDATE action")
    check_expression: Optional[str] = Field(None, description="Check constraint expression")
    default_value: Optional[str] = Field(None, description="Default value")
    default_expression: Optional[str] = Field(None, description="Default expression")
    is_enforced: bool = Field(True, description="Whether constraint is enforced")
    is_deferrable: bool = Field(False, description="Whether constraint is deferrable")
    meta: dict = Field(default_factory=dict, description="Additional metadata")


class ColumnConstraintCreate(ColumnConstraintBase):
    """Schema for creating a column constraint."""

    column_id: str = Field(..., description="Column ID (UUID)")


class ColumnConstraintUpdate(BaseModel):
    """Schema for updating a column constraint."""

    constraint_name: Optional[str] = None
    is_enforced: Optional[bool] = None
    is_deferrable: Optional[bool] = None
    meta: Optional[dict] = None


class ColumnConstraintSummary(BaseModel):
    """Summary view of a column constraint."""

    id: str
    column_id: str
    constraint_type: str
    constraint_name: Optional[str] = None
    is_enforced: bool

    class Config:
        from_attributes = True


class ColumnConstraintDetail(ColumnConstraintBase):
    """Detailed view of a column constraint."""

    id: str
    column_id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ColumnConstraintListResponse(BaseModel):
    """Response for column constraint list."""

    data: list[ColumnConstraintSummary]
    pagination: dict
