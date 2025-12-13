"""Repository for SourceSystem data access."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.source_system import SourceSystem
from src.repositories.base import BaseRepository


class SourceSystemRepository(BaseRepository[SourceSystem]):
    """Repository for source system operations."""

    model_class = SourceSystem

    async def get_by_name(self, name: str) -> Optional[SourceSystem]:
        """Get source system by name."""
        stmt = select(SourceSystem).where(SourceSystem.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_type(
        self,
        source_type: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[SourceSystem]:
        """Get source systems by type."""
        stmt = (
            select(SourceSystem)
            .where(SourceSystem.source_type == source_type)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_or_create(
        self,
        name: str,
        source_type: str,
        description: Optional[str] = None,
    ) -> tuple[SourceSystem, bool]:
        """
        Get existing source system or create new one.
        Returns (source_system, created) where created is True if new.
        """
        existing = await self.get_by_name(name)
        if existing:
            return existing, False

        source_system = SourceSystem(
            name=name,
            source_type=source_type,
            description=description,
        )
        self.session.add(source_system)
        await self.session.flush()
        await self.session.refresh(source_system)
        return source_system, True
