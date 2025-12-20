"""Catalog summary schemas."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CapsuleSummary(BaseModel):
    """Summary information for a capsule from the materialized view."""

    id: str
    urn: str
    name: str
    capsule_type: str
    layer: Optional[str] = None
    description: Optional[str] = None

    # Structural metadata (Dimension 2)
    column_count: int = 0
    index_count: int = 0
    pk_count: int = 0
    fk_count: int = 0

    # Semantic metadata (Dimension 3)
    business_term_count: int = 0

    # Quality expectations (Dimension 4)
    quality_rule_count: int = 0
    enabled_quality_rule_count: int = 0
    avg_column_quality_score: Optional[Decimal] = None

    # Policy metadata (Dimension 5)
    highest_sensitivity: Optional[str] = None
    has_masking_rules: bool = False
    masking_rule_count: int = 0

    # Provenance (Dimension 6)
    version_count: int = 0
    transformation_code_count: int = 0

    # Operational contracts (Dimension 7)
    freshness_sla: Optional[timedelta] = None
    quality_score_sla: Optional[Decimal] = None
    contract_status: Optional[str] = None

    # Lineage
    upstream_count: int = 0
    downstream_count: int = 0

    # Timestamps
    created_at: str
    updated_at: str

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class ColumnSummary(BaseModel):
    """Summary information for a column from the materialized view."""

    id: str
    urn: str
    name: str
    data_type: str
    capsule_id: str
    capsule_urn: str
    capsule_name: str

    # Constraints
    is_primary_key: int = 0
    is_foreign_key: int = 0
    is_unique: int = 0
    is_not_null: int = 0

    # Business terms
    business_term_count: int = 0

    # Quality
    overall_quality_score: Optional[Decimal] = None
    completeness_score: Optional[Decimal] = None
    validity_score: Optional[Decimal] = None
    uniqueness_score: Optional[Decimal] = None
    null_percentage: Optional[Decimal] = None
    unique_percentage: Optional[Decimal] = None

    # Policy
    sensitivity_level: Optional[str] = None
    requires_masking: bool = False
    masking_rule_count: int = 0

    # Timestamps
    created_at: str
    updated_at: str

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class CatalogListResponse(BaseModel):
    """Response for capsule catalog list endpoint."""

    data: list[CapsuleSummary]
    pagination: dict[str, int] = Field(
        description="Pagination info with offset, limit, and total"
    )


class ColumnCatalogListResponse(BaseModel):
    """Response for column catalog list endpoint."""

    data: list[ColumnSummary]
    pagination: dict[str, int] = Field(
        description="Pagination info with offset, limit, and total"
    )
