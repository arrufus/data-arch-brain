"""Source system model for metadata origins."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType

if TYPE_CHECKING:
    from src.models.capsule import Capsule


class SourceSystem(DCSBase):
    """Metadata source (dbt, Snowflake, BigQuery, etc.)."""

    __tablename__ = "source_systems"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    connection_info: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)

    # Relationships
    capsules: Mapped[list["Capsule"]] = relationship(back_populates="source_system")
