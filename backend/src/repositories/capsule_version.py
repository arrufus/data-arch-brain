"""Repository for capsule versions."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select

from src.models import CapsuleVersion
from src.repositories.base import BaseRepository


class CapsuleVersionRepository(BaseRepository[CapsuleVersion]):
    """Repository for capsule version operations."""

    model_class = CapsuleVersion

    async def get_by_capsule(
        self,
        capsule_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[CapsuleVersion]:
        """Get all versions for a capsule, ordered by version number descending."""
        stmt = (
            select(CapsuleVersion)
            .where(CapsuleVersion.capsule_id == capsule_id)
            .order_by(CapsuleVersion.version_number.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_current_version(
        self,
        capsule_id: UUID,
    ) -> Optional[CapsuleVersion]:
        """Get the current version for a capsule."""
        stmt = (
            select(CapsuleVersion)
            .where(CapsuleVersion.capsule_id == capsule_id)
            .where(CapsuleVersion.is_current == True)  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_version_number(
        self,
        capsule_id: UUID,
        version_number: int,
    ) -> Optional[CapsuleVersion]:
        """Get a specific version by capsule ID and version number."""
        stmt = (
            select(CapsuleVersion)
            .where(CapsuleVersion.capsule_id == capsule_id)
            .where(CapsuleVersion.version_number == version_number)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_change_type(
        self,
        change_type: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[CapsuleVersion]:
        """Get all versions by change type."""
        stmt = (
            select(CapsuleVersion)
            .where(CapsuleVersion.change_type == change_type)
            .order_by(CapsuleVersion.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_breaking_changes(
        self,
        capsule_id: Optional[UUID] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[CapsuleVersion]:
        """Get all versions with breaking changes."""
        stmt = select(CapsuleVersion).where(CapsuleVersion.breaking_change == True)  # noqa: E712

        if capsule_id:
            stmt = stmt.where(CapsuleVersion.capsule_id == capsule_id)

        stmt = stmt.order_by(CapsuleVersion.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_git_commit(
        self,
        git_commit_sha: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[CapsuleVersion]:
        """Get all versions for a specific git commit."""
        stmt = (
            select(CapsuleVersion)
            .where(CapsuleVersion.git_commit_sha == git_commit_sha)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_capsule(self, capsule_id: UUID) -> int:
        """Count versions for a capsule."""
        stmt = select(func.count()).select_from(CapsuleVersion).where(
            CapsuleVersion.capsule_id == capsule_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_latest_version_number(self, capsule_id: UUID) -> int:
        """Get the latest version number for a capsule."""
        stmt = (
            select(func.max(CapsuleVersion.version_number))
            .where(CapsuleVersion.capsule_id == capsule_id)
        )
        result = await self.session.execute(stmt)
        version = result.scalar()
        return version if version is not None else 0
