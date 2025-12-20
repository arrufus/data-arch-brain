"""Repository for column profiles."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.models import ColumnProfile
from src.repositories.base import BaseRepository


class ColumnProfileRepository(BaseRepository[ColumnProfile]):
    """Repository for column profile operations."""

    model_class = ColumnProfile

    async def get_by_column(
        self,
        column_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ColumnProfile]:
        """Get all profiles for a column."""
        stmt = (
            select(ColumnProfile)
            .where(ColumnProfile.column_id == column_id)
            .order_by(ColumnProfile.profiled_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_latest_profile(
        self,
        column_id: UUID,
    ) -> Optional[ColumnProfile]:
        """Get the most recent profile for a column."""
        stmt = (
            select(ColumnProfile)
            .where(ColumnProfile.column_id == column_id)
            .order_by(ColumnProfile.profiled_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_by_column(self, column_id: UUID) -> int:
        """Count profiles for a column."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(ColumnProfile).where(
            ColumnProfile.column_id == column_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
