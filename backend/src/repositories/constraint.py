"""Repository for column constraints."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.models import ColumnConstraint
from src.repositories.base import BaseRepository


class ColumnConstraintRepository(BaseRepository[ColumnConstraint]):
    """Repository for column constraint operations."""

    model_class = ColumnConstraint

    async def get_by_column(
        self,
        column_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ColumnConstraint]:
        """Get all constraints for a column."""
        stmt = (
            select(ColumnConstraint)
            .where(ColumnConstraint.column_id == column_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_type(
        self,
        constraint_type: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ColumnConstraint]:
        """Get all constraints of a specific type."""
        stmt = (
            select(ColumnConstraint)
            .where(ColumnConstraint.constraint_type == constraint_type)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_primary_keys(
        self,
        capsule_id: Optional[UUID] = None,
    ) -> Sequence[ColumnConstraint]:
        """Get all primary key constraints, optionally filtered by capsule."""
        stmt = select(ColumnConstraint).where(
            ColumnConstraint.constraint_type == "primary_key"
        )

        if capsule_id:
            stmt = stmt.join(ColumnConstraint.column).where(
                ColumnConstraint.column.has(capsule_id=capsule_id)
            )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_foreign_keys(
        self,
        capsule_id: Optional[UUID] = None,
    ) -> Sequence[ColumnConstraint]:
        """Get all foreign key constraints, optionally filtered by capsule."""
        stmt = select(ColumnConstraint).where(
            ColumnConstraint.constraint_type == "foreign_key"
        )

        if capsule_id:
            stmt = stmt.join(ColumnConstraint.column).where(
                ColumnConstraint.column.has(capsule_id=capsule_id)
            )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_referenced_table(
        self,
        table_urn: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ColumnConstraint]:
        """Get all foreign keys referencing a specific table."""
        stmt = (
            select(ColumnConstraint)
            .where(ColumnConstraint.referenced_table_urn == table_urn)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_column(self, column_id: UUID) -> int:
        """Count constraints for a column."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(ColumnConstraint).where(
            ColumnConstraint.column_id == column_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
