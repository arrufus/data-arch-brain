"""Domain and ownership models."""

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DABBase, JSONType, fk_ref

if TYPE_CHECKING:
    from src.models.capsule import Capsule


class Owner(DABBase):
    """Team or individual owning data assets."""

    __tablename__ = "owners"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_type: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="team"
    )
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    slack_channel: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)

    # Relationships
    capsules: Mapped[list["Capsule"]] = relationship(back_populates="owner")
    domains: Mapped[list["Domain"]] = relationship(back_populates="owner")


class Domain(DABBase):
    """Business domain for organizing capsules."""

    __tablename__ = "domains"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("domains.id")), nullable=True
    )
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("owners.id")), nullable=True
    )
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)

    # Relationships
    parent: Mapped[Optional["Domain"]] = relationship(
        "Domain", remote_side="Domain.id", back_populates="children"
    )
    children: Mapped[list["Domain"]] = relationship("Domain", back_populates="parent")
    owner: Mapped[Optional["Owner"]] = relationship(back_populates="domains")
    capsules: Mapped[list["Capsule"]] = relationship(back_populates="domain")
