"""Repository for Tag data access and TAGGED_WITH edge management."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.middleware import sanitize_search_query
from src.models.tag import CapsuleTag, ColumnTag, Tag
from src.repositories.base import BaseRepository


class TagRepository(BaseRepository[Tag]):
    """Repository for tag operations."""

    model_class = Tag

    async def get_by_name(self, name: str) -> Optional[Tag]:
        """Get tag by name (case-insensitive)."""
        stmt = select(Tag).where(func.lower(Tag.name) == name.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_associations(self, id: UUID) -> Optional[Tag]:
        """Get tag by ID with associations eagerly loaded."""
        stmt = (
            select(Tag)
            .options(
                selectinload(Tag.capsule_associations).selectinload(CapsuleTag.capsule),
                selectinload(Tag.column_associations).selectinload(ColumnTag.column),
            )
            .where(Tag.id == id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        name: str,
        category: Optional[str] = None,
        description: Optional[str] = None,
        sensitivity_level: Optional[str] = None,
    ) -> tuple[Tag, bool]:
        """
        Get existing tag or create new one.
        Returns (tag, created) where created is True if new.
        """
        existing = await self.get_by_name(name)
        if existing:
            return existing, False

        tag = Tag(
            name=name,
            category=category,
            description=description,
            sensitivity_level=sensitivity_level,
        )
        self.session.add(tag)
        await self.session.flush()
        await self.session.refresh(tag)
        return tag, True

    async def get_by_category(
        self, category: str, offset: int = 0, limit: int = 100
    ) -> Sequence[Tag]:
        """Get all tags in a category."""
        stmt = (
            select(Tag)
            .where(Tag.category == category)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_sensitivity_level(
        self, sensitivity_level: str, offset: int = 0, limit: int = 100
    ) -> Sequence[Tag]:
        """Get all tags with a specific sensitivity level."""
        stmt = (
            select(Tag)
            .where(Tag.sensitivity_level == sensitivity_level)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Tag]:
        """Search tags by name or description."""
        safe_query = sanitize_search_query(query)
        if not safe_query:
            return []

        search_pattern = f"%{safe_query}%"
        stmt = select(Tag).where(
            Tag.name.ilike(search_pattern) | Tag.description.ilike(search_pattern)
        )

        if category:
            stmt = stmt.where(Tag.category == category)

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_categories(self) -> list[str]:
        """Get all distinct tag categories."""
        stmt = (
            select(Tag.category)
            .where(Tag.category.isnot(None))
            .distinct()
            .order_by(Tag.category)
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]


class CapsuleTagRepository:
    """Repository for capsule-tag associations (TAGGED_WITH edges).

    Note: This doesn't inherit from BaseRepository since CapsuleTag
    uses a different base class.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: UUID) -> Optional[CapsuleTag]:
        """Get association by ID."""
        return await self.session.get(CapsuleTag, id)

    async def get_association(
        self, capsule_id: UUID, tag_id: UUID
    ) -> Optional[CapsuleTag]:
        """Get specific capsule-tag association."""
        stmt = select(CapsuleTag).where(
            CapsuleTag.capsule_id == capsule_id,
            CapsuleTag.tag_id == tag_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_tag_to_capsule(
        self,
        capsule_id: UUID,
        tag_id: UUID,
        added_by: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> CapsuleTag:
        """Add a tag to a capsule (create TAGGED_WITH edge)."""
        association = CapsuleTag(
            capsule_id=capsule_id,
            tag_id=tag_id,
            added_by=added_by,
            meta=meta or {},
        )
        self.session.add(association)
        await self.session.flush()
        await self.session.refresh(association)
        return association

    async def remove_tag_from_capsule(
        self, capsule_id: UUID, tag_id: UUID
    ) -> bool:
        """Remove a tag from a capsule. Returns True if removed."""
        association = await self.get_association(capsule_id, tag_id)
        if association:
            await self.session.delete(association)
            await self.session.flush()
            return True
        return False

    async def get_tags_for_capsule(
        self, capsule_id: UUID
    ) -> Sequence[CapsuleTag]:
        """Get all tag associations for a capsule."""
        stmt = (
            select(CapsuleTag)
            .options(selectinload(CapsuleTag.tag))
            .where(CapsuleTag.capsule_id == capsule_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_capsules_for_tag(
        self, tag_id: UUID, offset: int = 0, limit: int = 100
    ) -> Sequence[CapsuleTag]:
        """Get all capsule associations for a tag."""
        stmt = (
            select(CapsuleTag)
            .options(selectinload(CapsuleTag.capsule))
            .where(CapsuleTag.tag_id == tag_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_capsules_with_tag(self, tag_id: UUID) -> int:
        """Count capsules with a specific tag."""
        stmt = (
            select(func.count())
            .select_from(CapsuleTag)
            .where(CapsuleTag.tag_id == tag_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0


class ColumnTagRepository:
    """Repository for column-tag associations (TAGGED_WITH edges).

    Note: This doesn't inherit from BaseRepository since ColumnTag
    uses a different base class.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: UUID) -> Optional[ColumnTag]:
        """Get association by ID."""
        return await self.session.get(ColumnTag, id)

    async def get_association(
        self, column_id: UUID, tag_id: UUID
    ) -> Optional[ColumnTag]:
        """Get specific column-tag association."""
        stmt = select(ColumnTag).where(
            ColumnTag.column_id == column_id,
            ColumnTag.tag_id == tag_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_tag_to_column(
        self,
        column_id: UUID,
        tag_id: UUID,
        added_by: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> ColumnTag:
        """Add a tag to a column (create TAGGED_WITH edge)."""
        association = ColumnTag(
            column_id=column_id,
            tag_id=tag_id,
            added_by=added_by,
            meta=meta or {},
        )
        self.session.add(association)
        await self.session.flush()
        await self.session.refresh(association)
        return association

    async def remove_tag_from_column(
        self, column_id: UUID, tag_id: UUID
    ) -> bool:
        """Remove a tag from a column. Returns True if removed."""
        association = await self.get_association(column_id, tag_id)
        if association:
            await self.session.delete(association)
            await self.session.flush()
            return True
        return False

    async def get_tags_for_column(
        self, column_id: UUID
    ) -> Sequence[ColumnTag]:
        """Get all tag associations for a column."""
        stmt = (
            select(ColumnTag)
            .options(selectinload(ColumnTag.tag))
            .where(ColumnTag.column_id == column_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_columns_for_tag(
        self, tag_id: UUID, offset: int = 0, limit: int = 100
    ) -> Sequence[ColumnTag]:
        """Get all column associations for a tag."""
        stmt = (
            select(ColumnTag)
            .options(selectinload(ColumnTag.column))
            .where(ColumnTag.tag_id == tag_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_columns_with_tag(self, tag_id: UUID) -> int:
        """Count columns with a specific tag."""
        stmt = (
            select(func.count())
            .select_from(ColumnTag)
            .where(ColumnTag.tag_id == tag_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
