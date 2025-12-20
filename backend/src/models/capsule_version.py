"""Capsule version models for tracking schema evolution and changes."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType, fk_ref, get_schema_table_args


class ChangeType(str, Enum):
    """Types of changes tracked in capsule versions."""

    CREATED = "created"
    SCHEMA_CHANGE = "schema_change"
    DELETED = "deleted"
    METADATA_CHANGE = "metadata_change"


class CapsuleVersion(DCSBase):
    """Capsule version tracking for schema evolution.

    Tracks changes to capsules over time, including schema snapshots,
    deployment context, and git integration.
    """

    __tablename__ = "capsule_versions"
    __table_args__ = (
        UniqueConstraint("capsule_id", "version_number", name="capsule_version_unique"),
        get_schema_table_args(),
    )

    # Capsule reference
    capsule_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("capsules.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Version identification
    version_number: Mapped[int] = mapped_column(nullable=False)
    version_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    version_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Schema snapshot
    schema_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False)

    # Change tracking
    change_type: Mapped[Optional[ChangeType]] = mapped_column(String(50), nullable=True)
    change_summary: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    breaking_change: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )

    # Lineage snapshot
    upstream_capsule_urns: Mapped[list[str]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )
    downstream_capsule_urns: Mapped[list[str]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )

    # Deployment
    deployed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    deployed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deployment_context: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONType(), nullable=True
    )

    # Git integration
    git_commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    git_branch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    git_tag: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    git_repository: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status
    is_current: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false", index=True
    )

    # Metadata
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONType(), nullable=False, default=dict, server_default="{}"
    )

    # Relationships
    capsule: Mapped["Capsule"] = relationship(
        "Capsule", back_populates="versions", foreign_keys=[capsule_id]
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<CapsuleVersion(id={self.id}, capsule_id={self.capsule_id}, "
            f"version={self.version_number}, is_current={self.is_current})>"
        )

    @property
    def has_git_context(self) -> bool:
        """Check if version has git context."""
        return bool(self.git_commit_sha or self.git_branch or self.git_tag)

    @property
    def is_breaking_change(self) -> bool:
        """Check if this is a breaking change."""
        return self.breaking_change

    @property
    def has_deployment_info(self) -> bool:
        """Check if version has deployment information."""
        return bool(self.deployed_at or self.deployed_by or self.deployment_context)
