"""Pydantic schemas for column profiles."""

from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, Field


class ColumnProfileBase(BaseModel):
    """Base schema for column profiles."""

    # Basic statistics
    total_count: Optional[int] = Field(None, description="Total row count")
    null_count: Optional[int] = Field(None, description="Number of null values")
    null_percentage: Optional[Decimal] = Field(None, description="Percentage of nulls")
    distinct_count: Optional[int] = Field(None, description="Number of distinct values")
    unique_percentage: Optional[Decimal] = Field(None, description="Percentage of unique values")

    # For numeric columns
    min_value: Optional[Decimal] = Field(None, description="Minimum value")
    max_value: Optional[Decimal] = Field(None, description="Maximum value")
    mean_value: Optional[Decimal] = Field(None, description="Mean value")
    median_value: Optional[Decimal] = Field(None, description="Median value")
    std_dev: Optional[Decimal] = Field(None, description="Standard deviation")
    variance: Optional[Decimal] = Field(None, description="Variance")
    percentile_25: Optional[Decimal] = Field(None, description="25th percentile")
    percentile_75: Optional[Decimal] = Field(None, description="75th percentile")

    # For string columns
    min_length: Optional[int] = Field(None, description="Minimum string length")
    max_length: Optional[int] = Field(None, description="Maximum string length")
    avg_length: Optional[Decimal] = Field(None, description="Average string length")

    # For all columns
    most_common_values: Optional[list[dict[str, Any]]] = Field(
        None, description="Most common values with counts"
    )
    value_distribution: Optional[dict[str, Any]] = Field(
        None, description="Value distribution histogram"
    )
    detected_patterns: Optional[list[dict[str, Any]]] = Field(
        None, description="Detected patterns in data"
    )

    # Temporal patterns
    earliest_timestamp: Optional[str] = Field(None, description="Earliest timestamp value")
    latest_timestamp: Optional[str] = Field(None, description="Latest timestamp value")

    # Data quality indicators (0-100 scores)
    completeness_score: Optional[Decimal] = Field(None, description="Completeness score (0-100)")
    validity_score: Optional[Decimal] = Field(None, description="Validity score (0-100)")
    uniqueness_score: Optional[Decimal] = Field(None, description="Uniqueness score (0-100)")

    # Profiling metadata
    profiled_at: str = Field(..., description="When profile was generated")
    profiled_by: Optional[str] = Field(None, description="Who/what generated the profile")
    sample_size: Optional[int] = Field(None, description="Number of rows sampled")
    sample_percentage: Optional[Decimal] = Field(None, description="Percentage of data sampled")

    # Metadata
    meta: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ColumnProfileCreate(ColumnProfileBase):
    """Schema for creating a column profile."""

    column_id: str = Field(..., description="Column ID (UUID)")


class ColumnProfileSummary(BaseModel):
    """Summary view of a column profile."""

    id: str
    column_id: str
    total_count: Optional[int] = None
    null_percentage: Optional[Decimal] = None
    distinct_count: Optional[int] = None
    completeness_score: Optional[Decimal] = None
    validity_score: Optional[Decimal] = None
    uniqueness_score: Optional[Decimal] = None
    profiled_at: str

    class Config:
        from_attributes = True


class ColumnProfileDetail(ColumnProfileBase):
    """Detailed view of a column profile."""

    id: str
    column_id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ColumnProfileListResponse(BaseModel):
    """Response for column profile list."""

    data: list[ColumnProfileSummary]
    pagination: dict
