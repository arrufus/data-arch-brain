"""Capsule index models for structural metadata."""

from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType, fk_ref

if TYPE_CHECKING:
    from src.models.capsule import Capsule


class IndexType(str, Enum):
    """Types of database indexes."""

    BTREE = "btree"
    HASH = "hash"
    GIN = "gin"
    GIST = "gist"
    BRIN = "brin"
    SPGIST = "spgist"


class CapsuleIndex(DCSBase):
    """Index definition for a capsule (table).

    Represents database indexes including B-tree, hash, GIN, GiST, and BRIN indexes.
    Supports composite indexes, unique indexes, partial indexes, and expression indexes.

    Attributes:
        capsule_id: Reference to the capsule (table) this index is on.
        index_name: Name of the index.
        index_type: Type of index (btree, hash, gin, etc.).
        is_unique: Whether this is a unique index.
        is_primary: Whether this is the primary key index.
        column_names: Ordered list of column names in the index.
        column_expressions: For expression indexes, the expressions used.
        is_partial: Whether this is a partial index.
        partial_predicate: WHERE clause for partial index.
        tablespace: Tablespace where index is stored.
        fill_factor: Index fill factor (storage parameter).
        meta: Additional metadata as JSON.
    """

    __tablename__ = "capsule_indexes"

    # Parent reference
    capsule_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("capsules.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Index definition
    index_name: Mapped[str] = mapped_column(String(255), nullable=False)
    index_type: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="btree"
    )
    is_unique: Mapped[bool] = mapped_column(Boolean, server_default="false")
    is_primary: Mapped[bool] = mapped_column(Boolean, server_default="false")

    # Columns in index (ordered)
    column_names: Mapped[list] = mapped_column(
        JSONType(), nullable=False
    )  # ["col1", "col2"]
    column_expressions: Mapped[Optional[list]] = mapped_column(
        JSONType(), nullable=True
    )  # For expression indexes

    # Index properties
    is_partial: Mapped[bool] = mapped_column(Boolean, server_default="false")
    partial_predicate: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # WHERE clause

    # Storage
    tablespace: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fill_factor: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Metadata
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)

    # Relationships
    capsule: Mapped["Capsule"] = relationship(back_populates="indexes")

    def __repr__(self) -> str:
        """String representation."""
        return f"<CapsuleIndex(name={self.index_name}, type={self.index_type}, capsule_id={self.capsule_id})>"

    @property
    def column_count(self) -> int:
        """Get number of columns in this index."""
        return len(self.column_names) if self.column_names else 0

    @property
    def is_composite(self) -> bool:
        """Check if this is a composite index (multiple columns)."""
        return self.column_count > 1
