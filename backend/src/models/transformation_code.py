"""Transformation code models for capturing transformation logic."""

from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType, fk_ref, get_schema_table_args


class CodeLanguage(str, Enum):
    """Programming languages for transformation code."""

    SQL = "sql"
    PYTHON = "python"
    SPARK_SQL = "spark_sql"
    DBT = "dbt"
    R = "r"
    SCALA = "scala"
    JAVA = "java"


class TransformationCode(DCSBase):
    """Transformation code for capsules and lineage edges.

    Captures the actual code that transforms data, including metadata
    about the code location, dependencies, and git context.
    """

    __tablename__ = "transformation_code"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN capsule_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN lineage_edge_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="transformation_code_has_subject",
        ),
        get_schema_table_args(),
    )

    # Subject (one of these must be set)
    capsule_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("capsules.id"), ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    lineage_edge_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("capsule_lineage.id"), ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Code
    language: Mapped[CodeLanguage] = mapped_column(String(50), nullable=False)
    code_text: Mapped[str] = mapped_column(Text(), nullable=False)
    code_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Code metadata
    function_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    line_start: Mapped[Optional[int]] = mapped_column(nullable=True)
    line_end: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Git context
    git_commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    git_repository: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Dependencies
    upstream_references: Mapped[list[str]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )
    function_calls: Mapped[list[str]] = mapped_column(
        JSONType(), nullable=False, default=list, server_default="[]"
    )

    # Metadata
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONType(), nullable=False, default=dict, server_default="{}"
    )

    # Relationships
    capsule: Mapped[Optional["Capsule"]] = relationship(
        "Capsule", back_populates="transformation_codes", foreign_keys=[capsule_id]
    )
    lineage_edge: Mapped[Optional["CapsuleLineage"]] = relationship(
        "CapsuleLineage", back_populates="transformation_codes", foreign_keys=[lineage_edge_id]
    )

    def __repr__(self) -> str:
        """String representation."""
        subject = f"capsule={self.capsule_id}" if self.capsule_id else f"edge={self.lineage_edge_id}"
        return (
            f"<TransformationCode(id={self.id}, language={self.language}, {subject})>"
        )

    @property
    def subject_type(self) -> str:
        """Return the subject type (capsule or lineage_edge)."""
        return "capsule" if self.capsule_id else "lineage_edge"

    @property
    def has_file_location(self) -> bool:
        """Check if code has file location information."""
        return bool(self.file_path and (self.line_start is not None or self.line_end is not None))

    @property
    def has_git_context(self) -> bool:
        """Check if code has git context."""
        return bool(self.git_commit_sha or self.git_repository)

    @property
    def has_dependencies(self) -> bool:
        """Check if code has dependency information."""
        return bool(
            (self.upstream_references and len(self.upstream_references) > 0)
            or (self.function_calls and len(self.function_calls) > 0)
        )
