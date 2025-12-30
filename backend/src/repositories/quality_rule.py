"""Repository for quality rules."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select

from src.models import QualityRule
from src.repositories.base import BaseRepository


class QualityRuleRepository(BaseRepository[QualityRule]):
    """Repository for quality rule operations."""

    model_class = QualityRule

    async def get_by_capsule(
        self,
        capsule_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[QualityRule]:
        """Get all quality rules for a capsule."""
        stmt = (
            select(QualityRule)
            .where(QualityRule.capsule_id == capsule_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_column(
        self,
        column_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[QualityRule]:
        """Get all quality rules for a column."""
        stmt = (
            select(QualityRule)
            .where(QualityRule.column_id == column_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_type(
        self,
        rule_type: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[QualityRule]:
        """Get all quality rules of a specific type."""
        stmt = (
            select(QualityRule)
            .where(QualityRule.rule_type == rule_type)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_category(
        self,
        category: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[QualityRule]:
        """Get all quality rules of a specific category."""
        stmt = (
            select(QualityRule)
            .where(QualityRule.rule_category == category)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_enabled_rules(
        self,
        capsule_id: Optional[UUID] = None,
        column_id: Optional[UUID] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[QualityRule]:
        """Get all enabled quality rules, optionally filtered by subject."""
        stmt = select(QualityRule).where(QualityRule.is_enabled == True)  # noqa: E712

        if capsule_id:
            stmt = stmt.where(QualityRule.capsule_id == capsule_id)
        if column_id:
            stmt = stmt.where(QualityRule.column_id == column_id)

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_blocking_rules(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[QualityRule]:
        """Get all blocking quality rules."""
        stmt = (
            select(QualityRule)
            .where(QualityRule.blocking == True)  # noqa: E712
            .where(QualityRule.is_enabled == True)  # noqa: E712
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_capsule(self, capsule_id: UUID) -> int:
        """Count quality rules for a capsule."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(QualityRule).where(
            QualityRule.capsule_id == capsule_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_column(self, column_id: UUID) -> int:
        """Count quality rules for a column."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(QualityRule).where(
            QualityRule.column_id == column_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_type(self, rule_type: str) -> int:
        """Count quality rules by type."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(QualityRule).where(
            QualityRule.rule_type == rule_type
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_category(self, category: str) -> int:
        """Count quality rules by category."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(QualityRule).where(
            QualityRule.rule_category == category
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_enabled_rules(self) -> int:
        """Count enabled quality rules."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(QualityRule).where(
            QualityRule.is_enabled == True  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
