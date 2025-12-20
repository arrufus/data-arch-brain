"""Catalog endpoints for summarized capsule and column information."""

from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.catalog import (
    CapsuleSummary,
    CatalogListResponse,
    ColumnCatalogListResponse,
    ColumnSummary,
)
from src.database import DbSession

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/capsules", response_model=CatalogListResponse)
async def list_capsule_catalog(
    db: DbSession,
    layer: Optional[str] = Query(None, description="Filter by layer"),
    capsule_type: Optional[str] = Query(None, description="Filter by capsule type"),
    contract_status: Optional[str] = Query(None, description="Filter by contract status"),
    has_quality_rules: Optional[bool] = Query(None, description="Filter capsules with quality rules"),
    has_masking_rules: Optional[bool] = Query(None, description="Filter capsules with masking rules"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> CatalogListResponse:
    """List capsules with summary information from materialized view.

    This endpoint provides a high-performance summary of capsules by querying
    a materialized view that aggregates information from all 7 dimensions.
    """

    # Build query
    query_parts = ["SELECT * FROM dcs.catalog_capsule_summary WHERE 1=1"]
    params = {}

    if layer:
        query_parts.append("AND layer = :layer")
        params["layer"] = layer

    if capsule_type:
        query_parts.append("AND capsule_type = :capsule_type")
        params["capsule_type"] = capsule_type

    if contract_status:
        query_parts.append("AND contract_status = :contract_status")
        params["contract_status"] = contract_status

    if has_quality_rules is not None:
        if has_quality_rules:
            query_parts.append("AND quality_rule_count > 0")
        else:
            query_parts.append("AND quality_rule_count = 0")

    if has_masking_rules is not None:
        if has_masking_rules:
            query_parts.append("AND has_masking_rules = TRUE")
        else:
            query_parts.append("AND has_masking_rules = FALSE")

    # Add ordering and pagination
    query_parts.append("ORDER BY name")
    query_parts.append("LIMIT :limit OFFSET :offset")
    params["limit"] = limit
    params["offset"] = offset

    query_str = " ".join(query_parts)

    # Execute query
    result = await db.execute(text(query_str), params)
    capsules = result.mappings().all()

    # Get total count
    count_query_parts = ["SELECT COUNT(*) FROM dcs.catalog_capsule_summary WHERE 1=1"]
    if layer:
        count_query_parts.append("AND layer = :layer")
    if capsule_type:
        count_query_parts.append("AND capsule_type = :capsule_type")
    if contract_status:
        count_query_parts.append("AND contract_status = :contract_status")
    if has_quality_rules is not None:
        if has_quality_rules:
            count_query_parts.append("AND quality_rule_count > 0")
        else:
            count_query_parts.append("AND quality_rule_count = 0")
    if has_masking_rules is not None:
        if has_masking_rules:
            count_query_parts.append("AND has_masking_rules = TRUE")
        else:
            count_query_parts.append("AND has_masking_rules = FALSE")

    count_query_str = " ".join(count_query_parts)
    count_params = {k: v for k, v in params.items() if k not in ["limit", "offset"]}

    count_result = await db.execute(text(count_query_str), count_params)
    total = count_result.scalar() or 0

    return CatalogListResponse(
        data=[
            CapsuleSummary(
                id=str(c["id"]),
                urn=c["urn"],
                name=c["name"],
                capsule_type=c["capsule_type"],
                layer=c["layer"],
                description=c["description"],
                column_count=c["column_count"] or 0,
                index_count=c["index_count"] or 0,
                pk_count=c["pk_count"] or 0,
                fk_count=c["fk_count"] or 0,
                business_term_count=c["business_term_count"] or 0,
                quality_rule_count=c["quality_rule_count"] or 0,
                enabled_quality_rule_count=c["enabled_quality_rule_count"] or 0,
                avg_column_quality_score=c["avg_column_quality_score"],
                highest_sensitivity=c["highest_sensitivity"],
                has_masking_rules=c["has_masking_rules"] or False,
                masking_rule_count=c["masking_rule_count"] or 0,
                version_count=c["version_count"] or 0,
                transformation_code_count=c["transformation_code_count"] or 0,
                freshness_sla=c["freshness_sla"],
                quality_score_sla=c["quality_score_sla"],
                contract_status=c["contract_status"],
                upstream_count=c["upstream_count"] or 0,
                downstream_count=c["downstream_count"] or 0,
                created_at=c["created_at"].isoformat(),
                updated_at=c["updated_at"].isoformat(),
            )
            for c in capsules
        ],
        pagination={"offset": offset, "limit": limit, "total": total},
    )


@router.get("/columns", response_model=ColumnCatalogListResponse)
async def list_column_catalog(
    db: DbSession,
    capsule_id: Optional[str] = Query(None, description="Filter by capsule ID"),
    data_type: Optional[str] = Query(None, description="Filter by data type"),
    is_primary_key: Optional[bool] = Query(None, description="Filter primary keys"),
    has_masking_rules: Optional[bool] = Query(None, description="Filter columns with masking rules"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> ColumnCatalogListResponse:
    """List columns with summary information from materialized view.

    This endpoint provides column-level catalog information by querying
    a materialized view that aggregates constraint, quality, and policy metadata.
    """

    # Build query
    query_parts = ["SELECT * FROM dcs.catalog_column_summary WHERE 1=1"]
    params = {}

    if capsule_id:
        query_parts.append("AND capsule_id = :capsule_id::uuid")
        params["capsule_id"] = capsule_id

    if data_type:
        query_parts.append("AND data_type = :data_type")
        params["data_type"] = data_type

    if is_primary_key is not None:
        if is_primary_key:
            query_parts.append("AND is_primary_key > 0")
        else:
            query_parts.append("AND is_primary_key = 0")

    if has_masking_rules is not None:
        if has_masking_rules:
            query_parts.append("AND requires_masking = TRUE")
        else:
            query_parts.append("AND requires_masking = FALSE")

    # Add ordering and pagination
    query_parts.append("ORDER BY capsule_name, name")
    query_parts.append("LIMIT :limit OFFSET :offset")
    params["limit"] = limit
    params["offset"] = offset

    query_str = " ".join(query_parts)

    # Execute query
    result = await db.execute(text(query_str), params)
    columns = result.mappings().all()

    # Get total count
    count_query_parts = ["SELECT COUNT(*) FROM dcs.catalog_column_summary WHERE 1=1"]
    if capsule_id:
        count_query_parts.append("AND capsule_id = :capsule_id::uuid")
    if data_type:
        count_query_parts.append("AND data_type = :data_type")
    if is_primary_key is not None:
        if is_primary_key:
            count_query_parts.append("AND is_primary_key > 0")
        else:
            count_query_parts.append("AND is_primary_key = 0")
    if has_masking_rules is not None:
        if has_masking_rules:
            count_query_parts.append("AND requires_masking = TRUE")
        else:
            count_query_parts.append("AND requires_masking = FALSE")

    count_query_str = " ".join(count_query_parts)
    count_params = {k: v for k, v in params.items() if k not in ["limit", "offset"]}

    count_result = await db.execute(text(count_query_str), count_params)
    total = count_result.scalar() or 0

    return ColumnCatalogListResponse(
        data=[
            ColumnSummary(
                id=str(c["id"]),
                urn=c["urn"],
                name=c["name"],
                data_type=c["data_type"],
                capsule_id=str(c["capsule_id"]),
                capsule_urn=c["capsule_urn"],
                capsule_name=c["capsule_name"],
                is_primary_key=c["is_primary_key"] or 0,
                is_foreign_key=c["is_foreign_key"] or 0,
                is_unique=c["is_unique"] or 0,
                is_not_null=c["is_not_null"] or 0,
                business_term_count=c["business_term_count"] or 0,
                overall_quality_score=c["overall_quality_score"],
                completeness_score=c["completeness_score"],
                validity_score=c["validity_score"],
                uniqueness_score=c["uniqueness_score"],
                null_percentage=c["null_percentage"],
                unique_percentage=c["unique_percentage"],
                sensitivity_level=c["sensitivity_level"],
                requires_masking=c["requires_masking"] or False,
                masking_rule_count=c["masking_rule_count"] or 0,
                created_at=c["created_at"].isoformat(),
                updated_at=c["updated_at"].isoformat(),
            )
            for c in columns
        ],
        pagination={"offset": offset, "limit": limit, "total": total},
    )


@router.post("/refresh", status_code=204)
async def refresh_catalog_views(db: DbSession) -> None:
    """Refresh the materialized views for catalog data.

    This endpoint triggers a refresh of the catalog materialized views to ensure
    the summary data is up-to-date with the latest capsule and column information.

    Note: This operation can be expensive on large datasets. Consider using
    CONCURRENTLY option for production or scheduling refreshes during off-peak hours.
    """
    await db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY dcs.catalog_capsule_summary"))
    await db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY dcs.catalog_column_summary"))
    await db.commit()
