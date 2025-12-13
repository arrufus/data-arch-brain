"""Repository for Column data access."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.middleware import sanitize_search_query
from src.models.column import Column
from src.repositories.base import BaseRepository


class ColumnRepository(BaseRepository[Column]):
    """Repository for column operations."""

    model_class = Column

    async def get_by_urn(self, urn: str) -> Optional[Column]:
        """Get column by URN."""
        stmt = select(Column).where(Column.urn == urn)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_urns(self, urns: list[str]) -> Sequence[Column]:
        """Get columns by URNs."""
        if not urns:
            return []
        stmt = select(Column).where(Column.urn.in_(urns))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_capsule_id(
        self,
        capsule_id: UUID,
        offset: int = 0,
        limit: int = 1000,
    ) -> Sequence[Column]:
        """Get columns by capsule ID."""
        stmt = (
            select(Column)
            .where(Column.capsule_id == capsule_id)
            .order_by(Column.ordinal_position)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_pii_columns(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Column]:
        """Get all columns identified as PII."""
        stmt = (
            select(Column)
            .where(Column.pii_type.isnot(None))
            .options(selectinload(Column.capsule))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_pii_columns_by_type(
        self,
        pii_type: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Column]:
        """Get PII columns by specific type."""
        stmt = (
            select(Column)
            .where(Column.pii_type == pii_type)
            .options(selectinload(Column.capsule))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_semantic_type(
        self,
        semantic_type: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Column]:
        """Get columns by semantic type."""
        stmt = (
            select(Column)
            .where(Column.semantic_type == semantic_type)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search(
        self,
        query: str,
        capsule_id: Optional[UUID] = None,
        pii_only: bool = False,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Column]:
        """Search columns by name or description."""
        # Sanitize search query to prevent SQL injection
        safe_query = sanitize_search_query(query)
        if not safe_query:
            return []

        search_pattern = f"%{safe_query}%"
        stmt = select(Column).where(
            Column.name.ilike(search_pattern)
            | Column.description.ilike(search_pattern)
        )

        if capsule_id:
            stmt = stmt.where(Column.capsule_id == capsule_id)
        if pii_only:
            stmt = stmt.where(Column.pii_type.isnot(None))

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_pii(self) -> int:
        """Count PII columns."""
        stmt = select(func.count()).select_from(Column).where(
            Column.pii_type.isnot(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_pii_by_type(self) -> dict[str, int]:
        """Count PII columns by type."""
        stmt = (
            select(Column.pii_type, func.count(Column.id))
            .where(Column.pii_type.isnot(None))
            .group_by(Column.pii_type)
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def count_by_semantic_type(self) -> dict[str, int]:
        """Count columns by semantic type."""
        stmt = (
            select(Column.semantic_type, func.count(Column.id))
            .group_by(Column.semantic_type)
        )
        result = await self.session.execute(stmt)
        return {row[0] or "unknown": row[1] for row in result.all()}

    async def upsert_by_urn(self, column: Column) -> tuple[Column, bool]:
        """
        Insert or update a column by URN.
        Returns (column, created) where created is True if new.
        """
        existing = await self.get_by_urn(column.urn)
        if existing:
            # Update existing
            existing.name = column.name
            existing.capsule_id = column.capsule_id
            existing.data_type = column.data_type
            existing.ordinal_position = column.ordinal_position
            existing.is_nullable = column.is_nullable
            existing.semantic_type = column.semantic_type
            existing.pii_type = column.pii_type
            existing.pii_detected_by = column.pii_detected_by
            existing.description = column.description
            existing.meta = column.meta
            existing.tags = column.tags
            existing.stats = column.stats
            existing.has_tests = column.has_tests
            existing.test_count = column.test_count
            await self.session.flush()
            return existing, False
        else:
            # Create new
            self.session.add(column)
            await self.session.flush()
            await self.session.refresh(column)
            return column, True

    async def delete_by_capsule(self, capsule_id: UUID) -> int:
        """Delete all columns for a capsule. Returns count deleted."""
        stmt = select(Column).where(Column.capsule_id == capsule_id)
        result = await self.session.execute(stmt)
        columns = result.scalars().all()
        count = len(columns)
        for column in columns:
            await self.session.delete(column)
        await self.session.flush()
        return count

    async def get_by_urn_with_lineage(self, urn: str) -> Optional[Column]:
        """Get column by URN with lineage edges eagerly loaded."""
        stmt = (
            select(Column)
            .options(
                selectinload(Column.capsule),
                selectinload(Column.upstream_edges),
                selectinload(Column.downstream_edges),
            )
            .where(Column.urn == urn)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: list[UUID]) -> Sequence[Column]:
        """Get columns by IDs with capsule loaded."""
        if not ids:
            return []
        stmt = (
            select(Column)
            .options(selectinload(Column.capsule))
            .where(Column.id.in_(ids))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
