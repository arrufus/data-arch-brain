"""Pydantic schemas for capsule versions."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class CapsuleVersionBase(BaseModel):
    """Base schema for capsule versions."""

    version_number: int = Field(..., description="Version number")
    version_name: Optional[str] = Field(None, description="Version name (e.g., v1.2.0)")
    version_hash: Optional[str] = Field(None, description="Content hash")
    schema_snapshot: dict[str, Any] = Field(..., description="Full schema at this version")
    change_type: Optional[str] = Field(None, description="Type of change (created, schema_change, deleted, metadata_change)")
    change_summary: Optional[str] = Field(None, description="Summary of changes")
    breaking_change: bool = Field(False, description="Whether this is a breaking change")
    upstream_capsule_urns: list[str] = Field(default_factory=list, description="URNs of upstream capsules")
    downstream_capsule_urns: list[str] = Field(default_factory=list, description="URNs of downstream capsules")
    deployed_at: Optional[datetime] = Field(None, description="Deployment timestamp")
    deployed_by: Optional[str] = Field(None, description="Who deployed this version")
    deployment_context: Optional[dict[str, Any]] = Field(None, description="Deployment context (CI/CD, git commit, etc.)")
    git_commit_sha: Optional[str] = Field(None, description="Git commit SHA")
    git_branch: Optional[str] = Field(None, description="Git branch")
    git_tag: Optional[str] = Field(None, description="Git tag")
    git_repository: Optional[str] = Field(None, description="Git repository URL")
    is_current: bool = Field(False, description="Whether this is the current version")
    meta: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CapsuleVersionCreate(CapsuleVersionBase):
    """Schema for creating a capsule version."""

    capsule_id: str = Field(..., description="Capsule ID (UUID)")


class CapsuleVersionUpdate(BaseModel):
    """Schema for updating a capsule version."""

    version_name: Optional[str] = None
    change_summary: Optional[str] = None
    deployed_at: Optional[datetime] = None
    deployed_by: Optional[str] = None
    deployment_context: Optional[dict[str, Any]] = None
    is_current: Optional[bool] = None
    meta: Optional[dict[str, Any]] = None


class CapsuleVersionSummary(BaseModel):
    """Summary view of a capsule version."""

    id: str
    capsule_id: str
    version_number: int
    version_name: Optional[str] = None
    change_type: Optional[str] = None
    breaking_change: bool
    is_current: bool
    created_at: str

    class Config:
        from_attributes = True


class CapsuleVersionDetail(CapsuleVersionBase):
    """Detailed view of a capsule version."""

    id: str
    capsule_id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CapsuleVersionListResponse(BaseModel):
    """Response for capsule version list."""

    data: list[CapsuleVersionSummary]
    pagination: dict
