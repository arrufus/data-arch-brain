"""Repository for SLA incidents."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select

from src.models import SLAIncident
from src.repositories.base import BaseRepository


class SLAIncidentRepository(BaseRepository[SLAIncident]):
    """Repository for SLA incident operations."""

    model_class = SLAIncident

    async def get_by_contract(
        self,
        contract_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[SLAIncident]:
        """Get all incidents for a contract."""
        stmt = (
            select(SLAIncident)
            .where(SLAIncident.contract_id == contract_id)
            .order_by(SLAIncident.detected_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_capsule(
        self,
        capsule_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[SLAIncident]:
        """Get all incidents for a capsule."""
        stmt = (
            select(SLAIncident)
            .where(SLAIncident.capsule_id == capsule_id)
            .order_by(SLAIncident.detected_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_type(
        self,
        incident_type: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[SLAIncident]:
        """Get all incidents by type."""
        stmt = (
            select(SLAIncident)
            .where(SLAIncident.incident_type == incident_type)
            .order_by(SLAIncident.detected_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_status(
        self,
        status: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[SLAIncident]:
        """Get all incidents by status."""
        stmt = (
            select(SLAIncident)
            .where(SLAIncident.incident_status == status)
            .order_by(SLAIncident.detected_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_open_incidents(
        self,
        capsule_id: Optional[UUID] = None,
        contract_id: Optional[UUID] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[SLAIncident]:
        """Get all open incidents, optionally filtered by capsule or contract."""
        stmt = select(SLAIncident).where(
            SLAIncident.incident_status.in_(["open", "investigating"])
        )

        if capsule_id:
            stmt = stmt.where(SLAIncident.capsule_id == capsule_id)
        if contract_id:
            stmt = stmt.where(SLAIncident.contract_id == contract_id)

        stmt = stmt.order_by(SLAIncident.detected_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_severity(
        self,
        severity: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[SLAIncident]:
        """Get all incidents by severity."""
        stmt = (
            select(SLAIncident)
            .where(SLAIncident.incident_severity == severity)
            .order_by(SLAIncident.detected_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_critical_incidents(
        self,
        capsule_id: Optional[UUID] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[SLAIncident]:
        """Get all critical incidents."""
        stmt = select(SLAIncident).where(SLAIncident.incident_severity == "critical")

        if capsule_id:
            stmt = stmt.where(SLAIncident.capsule_id == capsule_id)

        stmt = stmt.order_by(SLAIncident.detected_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_root_cause_category(
        self,
        category: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[SLAIncident]:
        """Get all incidents by root cause category."""
        stmt = (
            select(SLAIncident)
            .where(SLAIncident.root_cause_category == category)
            .order_by(SLAIncident.detected_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_contract(self, contract_id: UUID) -> int:
        """Count incidents for a contract."""
        stmt = select(func.count()).select_from(SLAIncident).where(
            SLAIncident.contract_id == contract_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_capsule(self, capsule_id: UUID) -> int:
        """Count incidents for a capsule."""
        stmt = select(func.count()).select_from(SLAIncident).where(
            SLAIncident.capsule_id == capsule_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_status(self, status: str) -> int:
        """Count incidents by status."""
        stmt = select(func.count()).select_from(SLAIncident).where(
            SLAIncident.incident_status == status
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_open_incidents(
        self,
        capsule_id: Optional[UUID] = None,
        contract_id: Optional[UUID] = None,
    ) -> int:
        """Count open incidents."""
        stmt = select(func.count()).select_from(SLAIncident).where(
            SLAIncident.incident_status.in_(["open", "investigating"])
        )

        if capsule_id:
            stmt = stmt.where(SLAIncident.capsule_id == capsule_id)
        if contract_id:
            stmt = stmt.where(SLAIncident.contract_id == contract_id)

        result = await self.session.execute(stmt)
        return result.scalar() or 0
