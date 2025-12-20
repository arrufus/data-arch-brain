"""Column profile endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query, status

from src.api.exceptions import NotFoundError
from src.api.schemas.column_profile import (
    ColumnProfileCreate,
    ColumnProfileDetail,
    ColumnProfileListResponse,
    ColumnProfileSummary,
)
from src.database import DbSession
from src.models import ColumnProfile
from src.repositories import ColumnProfileRepository, ColumnRepository

router = APIRouter(prefix="/column-profiles", tags=["column-profiles"])


@router.post("", response_model=ColumnProfileDetail, status_code=status.HTTP_201_CREATED)
async def create_column_profile(
    db: DbSession,
    profile: ColumnProfileCreate,
) -> ColumnProfileDetail:
    """Create a new column profile."""
    column_repo = ColumnRepository(db)
    profile_repo = ColumnProfileRepository(db)

    # Verify column exists
    column = await column_repo.get_by_id(UUID(profile.column_id))
    if not column:
        raise NotFoundError("Column", profile.column_id)

    # Create profile
    new_profile = ColumnProfile(
        column_id=UUID(profile.column_id),
        total_count=profile.total_count,
        null_count=profile.null_count,
        null_percentage=profile.null_percentage,
        distinct_count=profile.distinct_count,
        unique_percentage=profile.unique_percentage,
        min_value=profile.min_value,
        max_value=profile.max_value,
        mean_value=profile.mean_value,
        median_value=profile.median_value,
        std_dev=profile.std_dev,
        variance=profile.variance,
        percentile_25=profile.percentile_25,
        percentile_75=profile.percentile_75,
        min_length=profile.min_length,
        max_length=profile.max_length,
        avg_length=profile.avg_length,
        most_common_values=profile.most_common_values,
        value_distribution=profile.value_distribution,
        detected_patterns=profile.detected_patterns,
        earliest_timestamp=profile.earliest_timestamp,
        latest_timestamp=profile.latest_timestamp,
        completeness_score=profile.completeness_score,
        validity_score=profile.validity_score,
        uniqueness_score=profile.uniqueness_score,
        profiled_at=profile.profiled_at,
        profiled_by=profile.profiled_by,
        sample_size=profile.sample_size,
        sample_percentage=profile.sample_percentage,
        meta=profile.meta,
    )

    created = await profile_repo.create(new_profile)
    await db.commit()

    return ColumnProfileDetail(
        id=str(created.id),
        column_id=str(created.column_id),
        total_count=created.total_count,
        null_count=created.null_count,
        null_percentage=created.null_percentage,
        distinct_count=created.distinct_count,
        unique_percentage=created.unique_percentage,
        min_value=created.min_value,
        max_value=created.max_value,
        mean_value=created.mean_value,
        median_value=created.median_value,
        std_dev=created.std_dev,
        variance=created.variance,
        percentile_25=created.percentile_25,
        percentile_75=created.percentile_75,
        min_length=created.min_length,
        max_length=created.max_length,
        avg_length=created.avg_length,
        most_common_values=created.most_common_values,
        value_distribution=created.value_distribution,
        detected_patterns=created.detected_patterns,
        earliest_timestamp=created.earliest_timestamp.isoformat() if created.earliest_timestamp else None,
        latest_timestamp=created.latest_timestamp.isoformat() if created.latest_timestamp else None,
        completeness_score=created.completeness_score,
        validity_score=created.validity_score,
        uniqueness_score=created.uniqueness_score,
        profiled_at=created.profiled_at.isoformat(),
        profiled_by=created.profiled_by,
        sample_size=created.sample_size,
        sample_percentage=created.sample_percentage,
        meta=created.meta,
        created_at=created.created_at.isoformat(),
        updated_at=created.updated_at.isoformat(),
    )


@router.get("", response_model=ColumnProfileListResponse)
async def list_column_profiles(
    db: DbSession,
    column_id: str = Query(..., description="Filter by column ID (required)"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> ColumnProfileListResponse:
    """List column profiles for a specific column."""
    repo = ColumnProfileRepository(db)

    profiles = await repo.get_by_column(UUID(column_id), offset, limit)
    total = await repo.count_by_column(UUID(column_id))

    data = [
        ColumnProfileSummary(
            id=str(p.id),
            column_id=str(p.column_id),
            total_count=p.total_count,
            null_percentage=p.null_percentage,
            distinct_count=p.distinct_count,
            completeness_score=p.completeness_score,
            validity_score=p.validity_score,
            uniqueness_score=p.uniqueness_score,
            profiled_at=p.profiled_at.isoformat(),
        )
        for p in profiles
    ]

    return ColumnProfileListResponse(
        data=data,
        pagination={
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": offset + limit < total,
        },
    )


@router.get("/latest", response_model=ColumnProfileDetail)
async def get_latest_profile(
    db: DbSession,
    column_id: str = Query(..., description="Column ID"),
) -> ColumnProfileDetail:
    """Get the most recent profile for a column."""
    repo = ColumnProfileRepository(db)
    profile = await repo.get_latest_profile(UUID(column_id))

    if not profile:
        raise NotFoundError("ColumnProfile", f"No profile found for column {column_id}")

    return ColumnProfileDetail(
        id=str(profile.id),
        column_id=str(profile.column_id),
        total_count=profile.total_count,
        null_count=profile.null_count,
        null_percentage=profile.null_percentage,
        distinct_count=profile.distinct_count,
        unique_percentage=profile.unique_percentage,
        min_value=profile.min_value,
        max_value=profile.max_value,
        mean_value=profile.mean_value,
        median_value=profile.median_value,
        std_dev=profile.std_dev,
        variance=profile.variance,
        percentile_25=profile.percentile_25,
        percentile_75=profile.percentile_75,
        min_length=profile.min_length,
        max_length=profile.max_length,
        avg_length=profile.avg_length,
        most_common_values=profile.most_common_values,
        value_distribution=profile.value_distribution,
        detected_patterns=profile.detected_patterns,
        earliest_timestamp=profile.earliest_timestamp.isoformat() if profile.earliest_timestamp else None,
        latest_timestamp=profile.latest_timestamp.isoformat() if profile.latest_timestamp else None,
        completeness_score=profile.completeness_score,
        validity_score=profile.validity_score,
        uniqueness_score=profile.uniqueness_score,
        profiled_at=profile.profiled_at.isoformat(),
        profiled_by=profile.profiled_by,
        sample_size=profile.sample_size,
        sample_percentage=profile.sample_percentage,
        meta=profile.meta,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
    )


@router.get("/{profile_id}", response_model=ColumnProfileDetail)
async def get_column_profile(
    db: DbSession,
    profile_id: UUID,
) -> ColumnProfileDetail:
    """Get column profile by ID."""
    repo = ColumnProfileRepository(db)
    profile = await repo.get_by_id(profile_id)

    if not profile:
        raise NotFoundError("ColumnProfile", str(profile_id))

    return ColumnProfileDetail(
        id=str(profile.id),
        column_id=str(profile.column_id),
        total_count=profile.total_count,
        null_count=profile.null_count,
        null_percentage=profile.null_percentage,
        distinct_count=profile.distinct_count,
        unique_percentage=profile.unique_percentage,
        min_value=profile.min_value,
        max_value=profile.max_value,
        mean_value=profile.mean_value,
        median_value=profile.median_value,
        std_dev=profile.std_dev,
        variance=profile.variance,
        percentile_25=profile.percentile_25,
        percentile_75=profile.percentile_75,
        min_length=profile.min_length,
        max_length=profile.max_length,
        avg_length=profile.avg_length,
        most_common_values=profile.most_common_values,
        value_distribution=profile.value_distribution,
        detected_patterns=profile.detected_patterns,
        earliest_timestamp=profile.earliest_timestamp.isoformat() if profile.earliest_timestamp else None,
        latest_timestamp=profile.latest_timestamp.isoformat() if profile.latest_timestamp else None,
        completeness_score=profile.completeness_score,
        validity_score=profile.validity_score,
        uniqueness_score=profile.uniqueness_score,
        profiled_at=profile.profiled_at.isoformat(),
        profiled_by=profile.profiled_by,
        sample_size=profile.sample_size,
        sample_percentage=profile.sample_percentage,
        meta=profile.meta,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
    )


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_column_profile(
    db: DbSession,
    profile_id: UUID,
) -> None:
    """Delete a column profile."""
    repo = ColumnProfileRepository(db)
    deleted = await repo.delete_by_id(profile_id)

    if not deleted:
        raise NotFoundError("ColumnProfile", str(profile_id))

    await db.commit()
