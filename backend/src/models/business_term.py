"""Business term models for semantic metadata."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import (
    DCSBase,
    JSONType,
    UUIDType,
    fk_ref,
    get_schema_table_args,
)

if TYPE_CHECKING:
    from src.models.capsule import Capsule
    from src.models.column import Column
    from src.models.domain import Domain, Owner


class ApprovalStatus(str, Enum):
    """Business term approval status."""

    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DEPRECATED = "deprecated"


class BusinessTerm(DCSBase):
    """Business glossary term.

    Represents a standardized business term that can be linked to capsules
    and columns to provide consistent semantic meaning across the organization.

    Attributes:
        term_name: Unique name of the term (slug-like identifier).
        display_name: Human-readable display name.
        definition: Detailed definition of the term.
        abbreviation: Common abbreviation or acronym.
        synonyms: Alternative names for the term.
        domain_id: Business domain this term belongs to.
        category: Category grouping (e.g., 'financial', 'customer').
        owner_id: Team or individual who owns this term definition.
        steward_email: Email of the data steward.
        approval_status: Current approval status.
        approved_by: Who approved this term.
        approved_at: When the term was approved.
        meta: Additional metadata as JSON.
        tags: Classification tags.
    """

    __tablename__ = "business_terms"

    # Term definition
    term_name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    abbreviation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    synonyms: Mapped[list] = mapped_column(
        JSONType(), default=list, nullable=False
    )  # ["alt_name1", "alt_name2"]

    # Categorization
    domain_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("domains.id")), nullable=True, index=True
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )

    # Ownership
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("owners.id")), nullable=True
    )
    steward_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Governance
    approval_status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="draft", index=True
    )
    approved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Metadata
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)
    tags: Mapped[list] = mapped_column(JSONType(), default=list, nullable=False)

    # Relationships
    domain: Mapped[Optional["Domain"]] = relationship(back_populates="business_terms")
    owner: Mapped[Optional["Owner"]] = relationship(back_populates="business_terms")
    capsule_associations: Mapped[list["CapsuleBusinessTerm"]] = relationship(
        back_populates="business_term", cascade="all, delete-orphan"
    )
    column_associations: Mapped[list["ColumnBusinessTerm"]] = relationship(
        back_populates="business_term", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<BusinessTerm(term_name={self.term_name}, status={self.approval_status})>"

    @property
    def is_approved(self) -> bool:
        """Check if term is approved."""
        return self.approval_status == ApprovalStatus.APPROVED.value


class RelationshipType(str, Enum):
    """Types of relationships between data assets and business terms."""

    IMPLEMENTS = "implements"  # Asset implements this concept
    RELATED_TO = "related_to"  # Asset is related to this concept
    EXAMPLE_OF = "example_of"  # Asset is an example of this concept
    MEASURES = "measures"  # Asset measures this metric
    DERIVED_FROM = "derived_from"  # Asset is derived from this concept


class CapsuleBusinessTerm(Base):
    """Association between a capsule and a business term.

    Links capsules to business glossary terms to provide semantic context.

    Attributes:
        capsule_id: The capsule being linked.
        business_term_id: The business term being applied.
        relationship_type: Nature of the relationship.
        added_by: Who created this link.
        added_at: When the link was created.
        meta: Additional metadata.
    """

    __tablename__ = "capsule_business_terms"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid4)

    capsule_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("capsules.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    business_term_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("business_terms.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    relationship_type: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="implements"
    )

    # Context
    added_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)

    # ORM Relationships
    capsule: Mapped["Capsule"] = relationship(
        back_populates="business_term_associations"
    )
    business_term: Mapped["BusinessTerm"] = relationship(
        back_populates="capsule_associations"
    )


class ColumnBusinessTerm(Base):
    """Association between a column and a business term.

    Links columns to business glossary terms to provide semantic context.

    Attributes:
        column_id: The column being linked.
        business_term_id: The business term being applied.
        relationship_type: Nature of the relationship.
        added_by: Who created this link.
        added_at: When the link was created.
        meta: Additional metadata.
    """

    __tablename__ = "column_business_terms"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid4)

    column_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("columns.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    business_term_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("business_terms.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    relationship_type: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="implements"
    )

    # Context
    added_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)

    # ORM Relationships
    column: Mapped["Column"] = relationship(back_populates="business_term_associations")
    business_term: Mapped["BusinessTerm"] = relationship(
        back_populates="column_associations"
    )
