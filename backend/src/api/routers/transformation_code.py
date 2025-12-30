"""Transformation code endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.api.exceptions import NotFoundError, ValidationError_
from src.api.schemas.transformation_code import (
    TransformationCodeCreate,
    TransformationCodeDetail,
    TransformationCodeListResponse,
    TransformationCodeSummary,
    TransformationCodeUpdate,
)
from src.database import DbSession
from src.models import TransformationCode
from src.repositories.capsule import CapsuleRepository
from src.repositories.lineage import CapsuleLineageRepository
from src.repositories.transformation_code import TransformationCodeRepository

router = APIRouter(prefix="/transformation-code", tags=["transformation-code"])


@router.post("", response_model=TransformationCodeDetail, status_code=status.HTTP_201_CREATED)
async def create_transformation_code(
    db: DbSession,
    code: TransformationCodeCreate,
) -> TransformationCodeDetail:
    """Create new transformation code."""
    # Validate that exactly one of capsule_id or lineage_edge_id is provided
    if not ((code.capsule_id is None) != (code.lineage_edge_id is None)):
        raise ValidationError_("Exactly one of capsule_id or lineage_edge_id must be provided")

    # Verify subject exists
    if code.capsule_id:
        capsule_repo = CapsuleRepository(db)
        subject = await capsule_repo.get_by_id(UUID(code.capsule_id))
        if not subject:
            raise NotFoundError("Capsule", code.capsule_id)
    else:
        lineage_repo = CapsuleLineageRepository(db)
        subject = await lineage_repo.get_by_id(UUID(code.lineage_edge_id))
        if not subject:
            raise NotFoundError("CapsuleLineage", code.lineage_edge_id)

    repo = TransformationCodeRepository(db)

    new_code = TransformationCode(
        capsule_id=UUID(code.capsule_id) if code.capsule_id else None,
        lineage_edge_id=UUID(code.lineage_edge_id) if code.lineage_edge_id else None,
        language=code.language,
        code_text=code.code_text,
        code_hash=code.code_hash,
        function_name=code.function_name,
        file_path=code.file_path,
        line_start=code.line_start,
        line_end=code.line_end,
        git_commit_sha=code.git_commit_sha,
        git_repository=code.git_repository,
        upstream_references=code.upstream_references,
        function_calls=code.function_calls,
        meta=code.meta,
    )

    created = await repo.create(new_code)
    await db.commit()

    return TransformationCodeDetail(
        id=str(created.id),
        capsule_id=str(created.capsule_id) if created.capsule_id else None,
        lineage_edge_id=str(created.lineage_edge_id) if created.lineage_edge_id else None,
        language=created.language,
        code_text=created.code_text,
        code_hash=created.code_hash,
        function_name=created.function_name,
        file_path=created.file_path,
        line_start=created.line_start,
        line_end=created.line_end,
        git_commit_sha=created.git_commit_sha,
        git_repository=created.git_repository,
        upstream_references=created.upstream_references,
        function_calls=created.function_calls,
        meta=created.meta,
        created_at=created.created_at.isoformat(),
        updated_at=created.updated_at.isoformat(),
    )


@router.get("", response_model=TransformationCodeListResponse)
async def list_transformation_code(
    db: DbSession,
    capsule_id: Optional[str] = Query(None),
    capsule_urn: Optional[str] = Query(None, description="Filter by capsule URN"),
    lineage_edge_id: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> TransformationCodeListResponse:
    """List transformation code with filters."""
    repo = TransformationCodeRepository(db)

    # Resolve URN to ID if needed
    resolved_capsule_id = capsule_id
    if capsule_urn and not capsule_id:
        capsule_repo = CapsuleRepository(db)
        capsule = await capsule_repo.get_by_urn(capsule_urn)
        if capsule:
            resolved_capsule_id = str(capsule.id)

    if resolved_capsule_id:
        codes = await repo.get_by_capsule(UUID(resolved_capsule_id), offset, limit)
        total = await repo.count_by_capsule(UUID(resolved_capsule_id))
    elif lineage_edge_id:
        codes = await repo.get_by_lineage_edge(UUID(lineage_edge_id), offset, limit)
        total = await repo.count_by_lineage_edge(UUID(lineage_edge_id))
    elif language:
        codes = await repo.get_by_language(language, offset, limit)
        total = await repo.count_by_language(language)
    else:
        codes = await repo.get_all(offset, limit)
        total = await repo.count()

    return TransformationCodeListResponse(
        data=[
            TransformationCodeSummary(
                id=str(c.id),
                capsule_id=str(c.capsule_id) if c.capsule_id else None,
                lineage_edge_id=str(c.lineage_edge_id) if c.lineage_edge_id else None,
                language=c.language,
                function_name=c.function_name,
                file_path=c.file_path,
            )
            for c in codes
        ],
        pagination={"offset": offset, "limit": limit, "total": total},
    )


@router.get("/{code_id}", response_model=TransformationCodeDetail)
async def get_transformation_code(db: DbSession, code_id: str) -> TransformationCodeDetail:
    """Get transformation code by ID."""
    repo = TransformationCodeRepository(db)
    code = await repo.get_by_id(UUID(code_id))
    if not code:
        raise NotFoundError("TransformationCode", code_id)

    return TransformationCodeDetail(
        id=str(code.id),
        capsule_id=str(code.capsule_id) if code.capsule_id else None,
        lineage_edge_id=str(code.lineage_edge_id) if code.lineage_edge_id else None,
        language=code.language,
        code_text=code.code_text,
        code_hash=code.code_hash,
        function_name=code.function_name,
        file_path=code.file_path,
        line_start=code.line_start,
        line_end=code.line_end,
        git_commit_sha=code.git_commit_sha,
        git_repository=code.git_repository,
        upstream_references=code.upstream_references,
        function_calls=code.function_calls,
        meta=code.meta,
        created_at=code.created_at.isoformat(),
        updated_at=code.updated_at.isoformat(),
    )


@router.patch("/{code_id}", response_model=TransformationCodeDetail)
async def update_transformation_code(
    db: DbSession,
    code_id: str,
    updates: TransformationCodeUpdate,
) -> TransformationCodeDetail:
    """Update transformation code."""
    repo = TransformationCodeRepository(db)
    code = await repo.get_by_id(UUID(code_id))
    if not code:
        raise NotFoundError("TransformationCode", code_id)

    # Apply updates
    update_dict = updates.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(code, field, value)

    await repo.update(code)
    await db.commit()

    return TransformationCodeDetail(
        id=str(code.id),
        capsule_id=str(code.capsule_id) if code.capsule_id else None,
        lineage_edge_id=str(code.lineage_edge_id) if code.lineage_edge_id else None,
        language=code.language,
        code_text=code.code_text,
        code_hash=code.code_hash,
        function_name=code.function_name,
        file_path=code.file_path,
        line_start=code.line_start,
        line_end=code.line_end,
        git_commit_sha=code.git_commit_sha,
        git_repository=code.git_repository,
        upstream_references=code.upstream_references,
        function_calls=code.function_calls,
        meta=code.meta,
        created_at=code.created_at.isoformat(),
        updated_at=code.updated_at.isoformat(),
    )


@router.delete("/{code_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transformation_code(db: DbSession, code_id: str) -> None:
    """Delete transformation code."""
    repo = TransformationCodeRepository(db)
    code = await repo.get_by_id(UUID(code_id))
    if not code:
        raise NotFoundError("TransformationCode", code_id)

    await repo.delete(code)
    await db.commit()
