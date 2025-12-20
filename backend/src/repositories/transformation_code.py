"""Repository for transformation code."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select

from src.models import TransformationCode
from src.repositories.base import BaseRepository


class TransformationCodeRepository(BaseRepository[TransformationCode]):
    """Repository for transformation code operations."""

    model_class = TransformationCode

    async def get_by_capsule(
        self,
        capsule_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[TransformationCode]:
        """Get all transformation code for a capsule."""
        stmt = (
            select(TransformationCode)
            .where(TransformationCode.capsule_id == capsule_id)
            .order_by(TransformationCode.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_lineage_edge(
        self,
        lineage_edge_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[TransformationCode]:
        """Get all transformation code for a lineage edge."""
        stmt = (
            select(TransformationCode)
            .where(TransformationCode.lineage_edge_id == lineage_edge_id)
            .order_by(TransformationCode.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_language(
        self,
        language: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[TransformationCode]:
        """Get all transformation code by programming language."""
        stmt = (
            select(TransformationCode)
            .where(TransformationCode.language == language)
            .order_by(TransformationCode.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_git_commit(
        self,
        git_commit_sha: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[TransformationCode]:
        """Get all transformation code for a specific git commit."""
        stmt = (
            select(TransformationCode)
            .where(TransformationCode.git_commit_sha == git_commit_sha)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_file_path(
        self,
        file_path: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[TransformationCode]:
        """Get all transformation code from a specific file path."""
        stmt = (
            select(TransformationCode)
            .where(TransformationCode.file_path == file_path)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_capsule(self, capsule_id: UUID) -> int:
        """Count transformation code entries for a capsule."""
        stmt = select(func.count()).select_from(TransformationCode).where(
            TransformationCode.capsule_id == capsule_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_lineage_edge(self, lineage_edge_id: UUID) -> int:
        """Count transformation code entries for a lineage edge."""
        stmt = select(func.count()).select_from(TransformationCode).where(
            TransformationCode.lineage_edge_id == lineage_edge_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_language(self, language: str) -> int:
        """Count transformation code entries by language."""
        stmt = select(func.count()).select_from(TransformationCode).where(
            TransformationCode.language == language
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
