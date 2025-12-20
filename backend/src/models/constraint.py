"""Column constraint models for structural metadata."""

from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType, fk_ref

if TYPE_CHECKING:
    from src.models.column import Column


class ConstraintType(str, Enum):
    """Types of database constraints."""

    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"
    UNIQUE = "unique"
    CHECK = "check"
    NOT_NULL = "not_null"
    DEFAULT = "default"


class OnDeleteAction(str, Enum):
    """Foreign key on delete actions."""

    CASCADE = "CASCADE"
    SET_NULL = "SET NULL"
    RESTRICT = "RESTRICT"
    NO_ACTION = "NO ACTION"
    SET_DEFAULT = "SET DEFAULT"


class ColumnConstraint(DCSBase):
    """Constraint definition for a column.

    Represents various types of database constraints including primary keys,
    foreign keys, unique constraints, check constraints, and default values.

    Attributes:
        column_id: Reference to the column this constraint applies to.
        constraint_type: Type of constraint (primary_key, foreign_key, etc.).
        constraint_name: Name of the constraint in the database.
        referenced_table_urn: For foreign keys, the URN of the referenced table.
        referenced_column_urn: For foreign keys, the URN of the referenced column.
        on_delete_action: Action to take when referenced row is deleted.
        on_update_action: Action to take when referenced row is updated.
        check_expression: SQL expression for check constraints.
        default_value: Literal default value.
        default_expression: Expression for computed default.
        is_enforced: Whether the constraint is actively enforced.
        is_deferrable: Whether constraint checking can be deferred.
        meta: Additional metadata as JSON.
    """

    __tablename__ = "column_constraints"

    # Parent reference
    column_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("columns.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Constraint definition
    constraint_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    constraint_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Foreign key references
    referenced_table_urn: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, index=True
    )
    referenced_column_urn: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    on_delete_action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    on_update_action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Check constraints
    check_expression: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Default constraints
    default_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_expression: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Enforcement
    is_enforced: Mapped[bool] = mapped_column(Boolean, server_default="true")
    is_deferrable: Mapped[bool] = mapped_column(Boolean, server_default="false")

    # Metadata
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)

    # Relationships
    column: Mapped["Column"] = relationship(back_populates="constraints")

    def __repr__(self) -> str:
        """String representation."""
        return f"<ColumnConstraint(type={self.constraint_type}, column_id={self.column_id})>"
