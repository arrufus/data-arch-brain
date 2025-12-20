"""Column profiling models for statistical metadata."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DCSBase, JSONType, fk_ref, get_schema_table_args


class ColumnProfile(DCSBase):
    """Statistical profiling metadata for a column.

    Stores computed statistics, value distributions, and data quality
    indicators for a specific column at a point in time.
    """

    __tablename__ = "column_profiles"
    __table_args__ = (get_schema_table_args(),)

    # Subject
    column_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("columns.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Basic statistics
    total_count: Mapped[Optional[int]] = mapped_column(BigInteger(), nullable=True)
    null_count: Mapped[Optional[int]] = mapped_column(BigInteger(), nullable=True)
    null_percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    distinct_count: Mapped[Optional[int]] = mapped_column(BigInteger(), nullable=True)
    unique_percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    # For numeric columns
    min_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(), nullable=True)
    max_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(), nullable=True)
    mean_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(), nullable=True)
    median_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(), nullable=True)
    std_dev: Mapped[Optional[Decimal]] = mapped_column(Numeric(), nullable=True)
    variance: Mapped[Optional[Decimal]] = mapped_column(Numeric(), nullable=True)
    percentile_25: Mapped[Optional[Decimal]] = mapped_column(Numeric(), nullable=True)
    percentile_75: Mapped[Optional[Decimal]] = mapped_column(Numeric(), nullable=True)

    # For string columns
    min_length: Mapped[Optional[int]] = mapped_column(Integer(), nullable=True)
    max_length: Mapped[Optional[int]] = mapped_column(Integer(), nullable=True)
    avg_length: Mapped[Optional[Decimal]] = mapped_column(Numeric(), nullable=True)

    # For all columns
    most_common_values: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONType(), nullable=True
    )  # [{"value": "foo", "count": 100, "percentage": 10.5}]
    value_distribution: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONType(), nullable=True
    )  # Histogram or frequency distribution

    # Pattern analysis
    detected_patterns: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONType(), nullable=True
    )  # [{"pattern": "^[A-Z]{3}$", "match_count": 50}]

    # Temporal patterns (for timestamps)
    earliest_timestamp: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    latest_timestamp: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Data quality indicators (0-100 scores)
    completeness_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    validity_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    uniqueness_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    # Profiling metadata
    profiled_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
    profiled_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sample_size: Mapped[Optional[int]] = mapped_column(BigInteger(), nullable=True)
    sample_percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    # Metadata
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONType(), nullable=False, default=dict, server_default="{}"
    )

    # Relationships
    column: Mapped["Column"] = relationship("Column", back_populates="profiles")

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<ColumnProfile(id={self.id}, column_id={self.column_id}, "
            f"profiled_at={self.profiled_at})>"
        )

    @property
    def is_numeric_profile(self) -> bool:
        """Check if this profile contains numeric statistics."""
        return self.mean_value is not None or self.median_value is not None

    @property
    def is_string_profile(self) -> bool:
        """Check if this profile contains string statistics."""
        return self.min_length is not None or self.max_length is not None

    @property
    def has_temporal_data(self) -> bool:
        """Check if this profile contains temporal statistics."""
        return self.earliest_timestamp is not None or self.latest_timestamp is not None

    @property
    def overall_quality_score(self) -> Optional[Decimal]:
        """Calculate overall quality score as average of available scores."""
        scores = [
            s
            for s in [self.completeness_score, self.validity_score, self.uniqueness_score]
            if s is not None
        ]
        if not scores:
            return None
        return Decimal(sum(scores) / len(scores))
