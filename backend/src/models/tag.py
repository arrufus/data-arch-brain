"""Tag models for classification and TAGGED_WITH edges.

This module implements the Tag node type and TAGGED_WITH edges
from the property graph specification (Section 5.2).
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import DABBase, JSONType, UUIDType, fk_ref, get_schema_table_args

if TYPE_CHECKING:
    from src.models.capsule import Capsule
    from src.models.column import Column


class Tag(DABBase):
    """Reusable tag for classifying capsules and columns.

    Attributes:
        name: Tag name (e.g., "pii", "gdpr", "tier-1").
        category: Category grouping (e.g., "compliance", "data-quality").
        description: Detailed description of the tag's meaning.
        color: Hex color code for UI display.
        sensitivity_level: Data sensitivity level (e.g., "public", "internal", "confidential", "restricted").
        meta: Additional metadata as JSON.
    """

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Hex color
    sensitivity_level: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)

    # Relationships to edge tables
    capsule_associations: Mapped[list["CapsuleTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )
    column_associations: Mapped[list["ColumnTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )

    @property
    def capsules(self) -> list["Capsule"]:
        """Get all capsules with this tag."""
        return [assoc.capsule for assoc in self.capsule_associations]

    @property
    def columns(self) -> list["Column"]:
        """Get all columns with this tag."""
        return [assoc.column for assoc in self.column_associations]


class CapsuleTag(Base):
    """TAGGED_WITH edge between Capsule and Tag.

    This implements the TAGGED_WITH edge type from the property graph spec,
    representing that a capsule has been tagged with a classification tag.

    Attributes:
        capsule_id: The capsule that is tagged.
        tag_id: The tag applied to the capsule.
        added_by: User/system that added the tag.
        added_at: When the tag was applied.
        meta: Additional edge metadata.
    """

    __tablename__ = "capsule_tags"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid4)

    capsule_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("capsules.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("tags.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    added_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)

    # ORM Relationships
    capsule: Mapped["Capsule"] = relationship(back_populates="tag_associations")
    tag: Mapped["Tag"] = relationship(back_populates="capsule_associations")


class ColumnTag(Base):
    """TAGGED_WITH edge between Column and Tag.

    This implements the TAGGED_WITH edge type from the property graph spec,
    representing that a column has been tagged with a classification tag.

    Attributes:
        column_id: The column that is tagged.
        tag_id: The tag applied to the column.
        added_by: User/system that added the tag.
        added_at: When the tag was applied.
        meta: Additional edge metadata.
    """

    __tablename__ = "column_tags"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid4)

    column_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("columns.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("tags.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    added_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)

    # ORM Relationships
    column: Mapped["Column"] = relationship(back_populates="tag_associations")
    tag: Mapped["Tag"] = relationship(back_populates="column_associations")
