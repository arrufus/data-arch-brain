"""Repository for capsule contracts."""

from datetime import date
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select

from src.models import CapsuleContract
from src.repositories.base import BaseRepository


class CapsuleContractRepository(BaseRepository[CapsuleContract]):
    """Repository for capsule contract operations."""

    model_class = CapsuleContract

    async def get_by_capsule(
        self,
        capsule_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[CapsuleContract]:
        """Get all contracts for a capsule."""
        stmt = (
            select(CapsuleContract)
            .where(CapsuleContract.capsule_id == capsule_id)
            .order_by(CapsuleContract.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_contracts(
        self,
        capsule_id: Optional[UUID] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[CapsuleContract]:
        """Get all active contracts, optionally filtered by capsule."""
        stmt = select(CapsuleContract).where(CapsuleContract.contract_status == "active")

        if capsule_id:
            stmt = stmt.where(CapsuleContract.capsule_id == capsule_id)

        stmt = stmt.order_by(CapsuleContract.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_status(
        self,
        status: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[CapsuleContract]:
        """Get all contracts by status."""
        stmt = (
            select(CapsuleContract)
            .where(CapsuleContract.contract_status == status)
            .order_by(CapsuleContract.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_deprecated_contracts(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[CapsuleContract]:
        """Get all deprecated contracts."""
        stmt = (
            select(CapsuleContract)
            .where(
                (CapsuleContract.contract_status == "deprecated") |
                (CapsuleContract.deprecation_date <= date.today())
            )
            .order_by(CapsuleContract.deprecation_date)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_support_level(
        self,
        support_level: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[CapsuleContract]:
        """Get all contracts by support level."""
        stmt = (
            select(CapsuleContract)
            .where(CapsuleContract.support_level == support_level)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_contracts_with_freshness_sla(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[CapsuleContract]:
        """Get all contracts with freshness SLA defined."""
        stmt = (
            select(CapsuleContract)
            .where(CapsuleContract.freshness_sla.isnot(None))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_contracts_with_quality_sla(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[CapsuleContract]:
        """Get all contracts with quality SLA defined."""
        stmt = (
            select(CapsuleContract)
            .where(
                (CapsuleContract.quality_score_sla.isnot(None)) |
                (CapsuleContract.critical_quality_rules != [])
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_owner(
        self,
        owner_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[CapsuleContract]:
        """Get all contracts by owner."""
        stmt = (
            select(CapsuleContract)
            .where(CapsuleContract.contract_owner_id == owner_id)
            .order_by(CapsuleContract.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_capsule(self, capsule_id: UUID) -> int:
        """Count contracts for a capsule."""
        stmt = select(func.count()).select_from(CapsuleContract).where(
            CapsuleContract.capsule_id == capsule_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_status(self, status: str) -> int:
        """Count contracts by status."""
        stmt = select(func.count()).select_from(CapsuleContract).where(
            CapsuleContract.contract_status == status
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
