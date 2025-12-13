"""Tag model for classification."""

from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import DABBase, JSONType


class Tag(DABBase):
    """Reusable tag for classifying capsules and columns."""

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Hex color
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict, nullable=False)
