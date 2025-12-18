"""Base repository pattern for data access."""

from typing import Any, Generic, Optional, Sequence, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import DCSBase

ModelT = TypeVar("ModelT", bound=DCSBase)


class BaseRepository(Generic[ModelT]):
    """Generic repository base class with common CRUD operations."""

    model_class: type[ModelT]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: UUID) -> Optional[ModelT]:
        """Get entity by ID."""
        return await self.session.get(self.model_class, id)

    async def get_by_ids(self, ids: list[UUID]) -> Sequence[ModelT]:
        """Get multiple entities by IDs."""
        if not ids:
            return []
        stmt = select(self.model_class).where(self.model_class.id.in_(ids))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ModelT]:
        """Get all entities with pagination."""
        stmt = select(self.model_class).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        """Count all entities."""
        stmt = select(func.count()).select_from(self.model_class)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def create(self, entity: ModelT) -> ModelT:
        """Create a new entity."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def create_many(self, entities: list[ModelT]) -> list[ModelT]:
        """Create multiple entities."""
        self.session.add_all(entities)
        await self.session.flush()
        for entity in entities:
            await self.session.refresh(entity)
        return entities

    async def update(self, entity: ModelT) -> ModelT:
        """Update an entity."""
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        """Delete an entity."""
        await self.session.delete(entity)
        await self.session.flush()

    async def delete_by_id(self, id: UUID) -> bool:
        """Delete entity by ID. Returns True if deleted."""
        entity = await self.get_by_id(id)
        if entity:
            await self.delete(entity)
            return True
        return False

    async def exists(self, id: UUID) -> bool:
        """Check if entity exists by ID."""
        stmt = select(func.count()).select_from(self.model_class).where(
            self.model_class.id == id
        )
        result = await self.session.execute(stmt)
        return (result.scalar() or 0) > 0
