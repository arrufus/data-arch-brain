"""Repository for masking rules."""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select

from src.models import MaskingRule
from src.repositories.base import BaseRepository


class MaskingRuleRepository(BaseRepository[MaskingRule]):
    """Repository for masking rule operations."""

    model_class = MaskingRule

    async def get_by_column(
        self,
        column_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[MaskingRule]:
        """Get all masking rules for a column."""
        stmt = (
            select(MaskingRule)
            .where(MaskingRule.column_id == column_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_enabled_rules(
        self,
        column_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[MaskingRule]:
        """Get all enabled masking rules for a column."""
        stmt = (
            select(MaskingRule)
            .where(MaskingRule.column_id == column_id)
            .where(MaskingRule.is_enabled == True)  # noqa: E712
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_method(
        self,
        masking_method: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[MaskingRule]:
        """Get all masking rules using a specific method."""
        stmt = (
            select(MaskingRule)
            .where(MaskingRule.masking_method == masking_method)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_role(
        self,
        role: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[MaskingRule]:
        """Get all masking rules that apply to a specific role."""
        stmt = (
            select(MaskingRule)
            .where(MaskingRule.applies_to_roles.contains([role]))
            .where(MaskingRule.is_enabled == True)  # noqa: E712
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_reversible_rules(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[MaskingRule]:
        """Get all reversible masking rules."""
        stmt = (
            select(MaskingRule)
            .where(MaskingRule.is_reversible == True)  # noqa: E712
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_column(self, column_id: UUID) -> int:
        """Count masking rules for a column."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(MaskingRule).where(
            MaskingRule.column_id == column_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
