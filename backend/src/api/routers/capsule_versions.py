"""Capsule version endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.api.exceptions import NotFoundError
from src.api.schemas.capsule_version import (
    CapsuleVersionCreate,
    CapsuleVersionDetail,
    CapsuleVersionListResponse,
    CapsuleVersionSummary,
    CapsuleVersionUpdate,
)
from src.database import DbSession
from src.models import CapsuleVersion
from src.repositories.capsule import CapsuleRepository
from src.repositories.capsule_version import CapsuleVersionRepository

router = APIRouter(prefix="/capsule-versions", tags=["capsule-versions"])


@router.post("", response_model=CapsuleVersionDetail, status_code=status.HTTP_201_CREATED)
async def create_capsule_version(
    db: DbSession,
    version: CapsuleVersionCreate,
) -> CapsuleVersionDetail:
    """Create a new capsule version."""
    # Verify capsule exists
    capsule_repo = CapsuleRepository(db)
    capsule = await capsule_repo.get_by_id(UUID(version.capsule_id))
    if not capsule:
        raise NotFoundError("Capsule", version.capsule_id)

    repo = CapsuleVersionRepository(db)

    # Create version
    new_version = CapsuleVersion(
        capsule_id=UUID(version.capsule_id),
        version_number=version.version_number,
        version_name=version.version_name,
        version_hash=version.version_hash,
        schema_snapshot=version.schema_snapshot,
        change_type=version.change_type,
        change_summary=version.change_summary,
        breaking_change=version.breaking_change,
        upstream_capsule_urns=version.upstream_capsule_urns,
        downstream_capsule_urns=version.downstream_capsule_urns,
        deployed_at=version.deployed_at,
        deployed_by=version.deployed_by,
        deployment_context=version.deployment_context,
        git_commit_sha=version.git_commit_sha,
        git_branch=version.git_branch,
        git_tag=version.git_tag,
        git_repository=version.git_repository,
        is_current=version.is_current,
        meta=version.meta,
    )

    created = await repo.create(new_version)
    await db.commit()

    return CapsuleVersionDetail(
        id=str(created.id),
        capsule_id=str(created.capsule_id),
        version_number=created.version_number,
        version_name=created.version_name,
        version_hash=created.version_hash,
        schema_snapshot=created.schema_snapshot,
        change_type=created.change_type,
        change_summary=created.change_summary,
        breaking_change=created.breaking_change,
        upstream_capsule_urns=created.upstream_capsule_urns,
        downstream_capsule_urns=created.downstream_capsule_urns,
        deployed_at=created.deployed_at,
        deployed_by=created.deployed_by,
        deployment_context=created.deployment_context,
        git_commit_sha=created.git_commit_sha,
        git_branch=created.git_branch,
        git_tag=created.git_tag,
        git_repository=created.git_repository,
        is_current=created.is_current,
        meta=created.meta,
        created_at=created.created_at.isoformat(),
        updated_at=created.updated_at.isoformat(),
    )


@router.get("", response_model=CapsuleVersionListResponse)
async def list_capsule_versions(
    db: DbSession,
    capsule_id: Optional[str] = Query(None, description="Filter by capsule ID"),
    change_type: Optional[str] = Query(None, description="Filter by change type"),
    breaking_only: bool = Query(False, description="Show only breaking changes"),
    current_only: bool = Query(False, description="Show only current versions"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> CapsuleVersionListResponse:
    """List capsule versions with optional filters."""
    repo = CapsuleVersionRepository(db)

    if capsule_id:
        versions = await repo.get_by_capsule(UUID(capsule_id), offset, limit)
        total = await repo.count_by_capsule(UUID(capsule_id))
    elif change_type:
        versions = await repo.get_by_change_type(change_type, offset, limit)
        total = await repo.count()
    elif breaking_only:
        versions = await repo.get_breaking_changes(offset=offset, limit=limit)
        total = await repo.count()
    else:
        versions = await repo.get_all(offset, limit)
        total = await repo.count()

    return CapsuleVersionListResponse(
        data=[
            CapsuleVersionSummary(
                id=str(v.id),
                capsule_id=str(v.capsule_id),
                version_number=v.version_number,
                version_name=v.version_name,
                change_type=v.change_type,
                breaking_change=v.breaking_change,
                is_current=v.is_current,
                created_at=v.created_at.isoformat(),
            )
            for v in versions
        ],
        pagination={
            "offset": offset,
            "limit": limit,
            "total": total,
        },
    )


@router.get("/{version_id}", response_model=CapsuleVersionDetail)
async def get_capsule_version(
    db: DbSession,
    version_id: str,
) -> CapsuleVersionDetail:
    """Get a capsule version by ID."""
    repo = CapsuleVersionRepository(db)
    version = await repo.get_by_id(UUID(version_id))
    if not version:
        raise NotFoundError("CapsuleVersion", version_id)

    return CapsuleVersionDetail(
        id=str(version.id),
        capsule_id=str(version.capsule_id),
        version_number=version.version_number,
        version_name=version.version_name,
        version_hash=version.version_hash,
        schema_snapshot=version.schema_snapshot,
        change_type=version.change_type,
        change_summary=version.change_summary,
        breaking_change=version.breaking_change,
        upstream_capsule_urns=version.upstream_capsule_urns,
        downstream_capsule_urns=version.downstream_capsule_urns,
        deployed_at=version.deployed_at,
        deployed_by=version.deployed_by,
        deployment_context=version.deployment_context,
        git_commit_sha=version.git_commit_sha,
        git_branch=version.git_branch,
        git_tag=version.git_tag,
        git_repository=version.git_repository,
        is_current=version.is_current,
        meta=version.meta,
        created_at=version.created_at.isoformat(),
        updated_at=version.updated_at.isoformat(),
    )


@router.patch("/{version_id}", response_model=CapsuleVersionDetail)
async def update_capsule_version(
    db: DbSession,
    version_id: str,
    updates: CapsuleVersionUpdate,
) -> CapsuleVersionDetail:
    """Update a capsule version."""
    repo = CapsuleVersionRepository(db)
    version = await repo.get_by_id(UUID(version_id))
    if not version:
        raise NotFoundError("CapsuleVersion", version_id)

    # Apply updates
    if updates.version_name is not None:
        version.version_name = updates.version_name
    if updates.change_summary is not None:
        version.change_summary = updates.change_summary
    if updates.deployed_at is not None:
        version.deployed_at = updates.deployed_at
    if updates.deployed_by is not None:
        version.deployed_by = updates.deployed_by
    if updates.deployment_context is not None:
        version.deployment_context = updates.deployment_context
    if updates.is_current is not None:
        version.is_current = updates.is_current
    if updates.meta is not None:
        version.meta = updates.meta

    await repo.update(version)
    await db.commit()

    return CapsuleVersionDetail(
        id=str(version.id),
        capsule_id=str(version.capsule_id),
        version_number=version.version_number,
        version_name=version.version_name,
        version_hash=version.version_hash,
        schema_snapshot=version.schema_snapshot,
        change_type=version.change_type,
        change_summary=version.change_summary,
        breaking_change=version.breaking_change,
        upstream_capsule_urns=version.upstream_capsule_urns,
        downstream_capsule_urns=version.downstream_capsule_urns,
        deployed_at=version.deployed_at,
        deployed_by=version.deployed_by,
        deployment_context=version.deployment_context,
        git_commit_sha=version.git_commit_sha,
        git_branch=version.git_branch,
        git_tag=version.git_tag,
        git_repository=version.git_repository,
        is_current=version.is_current,
        meta=version.meta,
        created_at=version.created_at.isoformat(),
        updated_at=version.updated_at.isoformat(),
    )


@router.delete("/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_capsule_version(
    db: DbSession,
    version_id: str,
) -> None:
    """Delete a capsule version."""
    repo = CapsuleVersionRepository(db)
    version = await repo.get_by_id(UUID(version_id))
    if not version:
        raise NotFoundError("CapsuleVersion", version_id)

    await repo.delete(version)
    await db.commit()
