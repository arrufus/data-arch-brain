"""Repository for capsule indexes."""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select

from src.models import CapsuleIndex
from src.repositories.base import BaseRepository


class CapsuleIndexRepository(BaseRepository[CapsuleIndex]):
    """Repository for capsule index operations."""

    model_class = CapsuleIndex

    async def get_by_capsule(
        self,
        capsule_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[CapsuleIndex]:
        """Get all indexes for a capsule."""
        stmt = (
            select(CapsuleIndex)
            .where(CapsuleIndex.capsule_id == capsule_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_type(
        self,
        index_type: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[CapsuleIndex]:
        """Get all indexes of a specific type."""
        stmt = (
            select(CapsuleIndex)
            .where(CapsuleIndex.index_type == index_type)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_unique_indexes(
        self,
        capsule_id: UUID,
    ) -> Sequence[CapsuleIndex]:
        """Get all unique indexes for a capsule."""
        stmt = select(CapsuleIndex).where(
            CapsuleIndex.capsule_id == capsule_id,
            CapsuleIndex.is_unique == True
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_primary_index(
        self,
        capsule_id: UUID,
    ) -> CapsuleIndex | None:
        """Get the primary key index for a capsule."""
        stmt = select(CapsuleIndex).where(
            CapsuleIndex.capsule_id == capsule_id,
            CapsuleIndex.is_primary == True
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_column_name(
        self,
        capsule_id: UUID,
        column_name: str,
    ) -> Sequence[CapsuleIndex]:
        """Get all indexes that include a specific column."""
        # Note: This queries JSONB array - PostgreSQL specific
        stmt = select(CapsuleIndex).where(
            CapsuleIndex.capsule_id == capsule_id,
            CapsuleIndex.column_names.contains([column_name])
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_capsule(self, capsule_id: UUID) -> int:
        """Count indexes for a capsule."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(CapsuleIndex).where(
            CapsuleIndex.capsule_id == capsule_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
