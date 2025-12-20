"""Repository for data policies."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select

from src.models import DataPolicy
from src.repositories.base import BaseRepository


class DataPolicyRepository(BaseRepository[DataPolicy]):
    """Repository for data policy operations."""

    model_class = DataPolicy

    async def get_by_capsule(
        self,
        capsule_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[DataPolicy]:
        """Get all data policies for a capsule."""
        stmt = (
            select(DataPolicy)
            .where(DataPolicy.capsule_id == capsule_id)
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
    ) -> Sequence[DataPolicy]:
        """Get all data policies for a column."""
        stmt = (
            select(DataPolicy)
            .where(DataPolicy.column_id == column_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_policies(
        self,
        capsule_id: Optional[UUID] = None,
        column_id: Optional[UUID] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[DataPolicy]:
        """Get all active policies, optionally filtered by subject."""
        stmt = select(DataPolicy).where(DataPolicy.policy_status == "active")

        if capsule_id:
            stmt = stmt.where(DataPolicy.capsule_id == capsule_id)
        if column_id:
            stmt = stmt.where(DataPolicy.column_id == column_id)

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_sensitivity(
        self,
        sensitivity_level: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[DataPolicy]:
        """Get all policies with a specific sensitivity level."""
        stmt = (
            select(DataPolicy)
            .where(DataPolicy.sensitivity_level == sensitivity_level)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_compliance_framework(
        self,
        framework: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[DataPolicy]:
        """Get all policies for a specific compliance framework."""
        from sqlalchemy.dialects.postgresql import JSONB
        stmt = (
            select(DataPolicy)
            .where(DataPolicy.compliance_frameworks.contains([framework]))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_policies_requiring_review(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[DataPolicy]:
        """Get all policies that require review."""
        from datetime import date
        from sqlalchemy import and_

        today = date.today()
        stmt = (
            select(DataPolicy)
            .where(
                and_(
                    DataPolicy.next_review_date.isnot(None),
                    DataPolicy.next_review_date <= today
                )
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_capsule(self, capsule_id: UUID) -> int:
        """Count data policies for a capsule."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(DataPolicy).where(
            DataPolicy.capsule_id == capsule_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_column(self, column_id: UUID) -> int:
        """Count data policies for a column."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(DataPolicy).where(
            DataPolicy.column_id == column_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
