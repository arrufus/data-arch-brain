"""Pydantic schemas for transformation code."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class TransformationCodeBase(BaseModel):
    """Base schema for transformation code."""

    language: str = Field(..., description="Programming language (sql, python, spark_sql, dbt, etc.)")
    code_text: str = Field(..., description="Transformation code text")
    code_hash: Optional[str] = Field(None, description="Hash of the code")
    function_name: Optional[str] = Field(None, description="Function name")
    file_path: Optional[str] = Field(None, description="File path in repository")
    line_start: Optional[int] = Field(None, description="Starting line number")
    line_end: Optional[int] = Field(None, description="Ending line number")
    git_commit_sha: Optional[str] = Field(None, description="Git commit SHA")
    git_repository: Optional[str] = Field(None, description="Git repository URL")
    upstream_references: list[str] = Field(default_factory=list, description="Upstream tables/columns referenced")
    function_calls: list[str] = Field(default_factory=list, description="UDFs called")
    meta: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TransformationCodeCreate(TransformationCodeBase):
    """Schema for creating transformation code."""

    capsule_id: Optional[str] = Field(None, description="Capsule ID (UUID) - one of capsule_id or lineage_edge_id required")
    lineage_edge_id: Optional[str] = Field(None, description="Lineage edge ID (UUID) - one of capsule_id or lineage_edge_id required")


class TransformationCodeUpdate(BaseModel):
    """Schema for updating transformation code."""

    code_text: Optional[str] = None
    code_hash: Optional[str] = None
    function_name: Optional[str] = None
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    git_commit_sha: Optional[str] = None
    git_repository: Optional[str] = None
    upstream_references: Optional[list[str]] = None
    function_calls: Optional[list[str]] = None
    meta: Optional[dict[str, Any]] = None


class TransformationCodeSummary(BaseModel):
    """Summary view of transformation code."""

    id: str
    capsule_id: Optional[str] = None
    lineage_edge_id: Optional[str] = None
    language: str
    function_name: Optional[str] = None
    file_path: Optional[str] = None

    class Config:
        from_attributes = True


class TransformationCodeDetail(TransformationCodeBase):
    """Detailed view of transformation code."""

    id: str
    capsule_id: Optional[str] = None
    lineage_edge_id: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TransformationCodeListResponse(BaseModel):
    """Response for transformation code list."""

    data: list[TransformationCodeSummary]
    pagination: dict
