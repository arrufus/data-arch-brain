"""Repository for violation data access."""

from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.violation import Violation, ViolationStatus


class ViolationRepository:
    """Repository for violation operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: UUID) -> Optional[Violation]:
        """Get violation by ID."""
        stmt = select(Violation).options(
            selectinload(Violation.rule),
            selectinload(Violation.capsule),
            selectinload(Violation.column),
        ).where(Violation.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_rule_and_subject(
        self,
        rule_id: UUID,
        capsule_id: Optional[UUID] = None,
        column_id: Optional[UUID] = None,
    ) -> Optional[Violation]:
        """Get existing open violation for a rule and subject."""
        conditions = [
            Violation.rule_id == rule_id,
            Violation.status == ViolationStatus.OPEN.value,
        ]
        
        if column_id:
            conditions.append(Violation.column_id == column_id)
        elif capsule_id:
            conditions.append(Violation.capsule_id == capsule_id)
            conditions.append(Violation.column_id.is_(None))
        
        stmt = select(Violation).where(and_(*conditions))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, violation: Violation) -> Violation:
        """Create a new violation."""
        self.session.add(violation)
        await self.session.flush()
        await self.session.refresh(violation)
        return violation

    async def create_many(self, violations: list[Violation]) -> list[Violation]:
        """Create multiple violations."""
        self.session.add_all(violations)
        await self.session.flush()
        for v in violations:
            await self.session.refresh(v)
        return violations

    async def upsert(
        self,
        violation: Violation,
    ) -> tuple[Violation, bool]:
        """
        Insert or update a violation.
        If an open violation exists for the same rule/subject, update it.
        Returns (violation, created) where created is True if new.
        """
        existing = await self.get_by_rule_and_subject(
            rule_id=violation.rule_id,
            capsule_id=violation.capsule_id,
            column_id=violation.column_id,
        )
        
        if existing:
            # Update existing open violation
            existing.message = violation.message
            existing.details = violation.details
            existing.severity = violation.severity
            existing.ingestion_id = violation.ingestion_id
            existing.detected_at = datetime.now(timezone.utc)
            await self.session.flush()
            return existing, False
        else:
            self.session.add(violation)
            await self.session.flush()
            await self.session.refresh(violation)
            return violation, True

    async def list_violations(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        rule_set: Optional[str] = None,
        capsule_id: Optional[UUID] = None,
        ingestion_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Violation]:
        """List violations with filters."""
        stmt = select(Violation).options(
            selectinload(Violation.rule),
            selectinload(Violation.capsule),
            selectinload(Violation.column),
        )
        
        if status:
            stmt = stmt.where(Violation.status == status)
        if severity:
            stmt = stmt.where(Violation.severity == severity)
        if capsule_id:
            stmt = stmt.where(Violation.capsule_id == capsule_id)
        if ingestion_id:
            stmt = stmt.where(Violation.ingestion_id == ingestion_id)
        
        # Filter by rule category or rule_set requires join
        if category or rule_set:
            from src.models.rule import Rule
            stmt = stmt.join(Violation.rule)
            if category:
                stmt = stmt.where(Rule.category == category)
            if rule_set:
                stmt = stmt.where(Rule.rule_set == rule_set)
        
        stmt = stmt.order_by(Violation.detected_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_violations(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        capsule_id: Optional[UUID] = None,
    ) -> int:
        """Count violations with optional filters."""
        stmt = select(func.count(Violation.id))
        if status:
            stmt = stmt.where(Violation.status == status)
        if severity:
            stmt = stmt.where(Violation.severity == severity)
        if capsule_id:
            stmt = stmt.where(Violation.capsule_id == capsule_id)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_severity(
        self,
        status: Optional[str] = None,
    ) -> dict[str, int]:
        """Get violation counts grouped by severity."""
        stmt = select(
            Violation.severity,
            func.count(Violation.id),
        ).group_by(Violation.severity)
        
        if status:
            stmt = stmt.where(Violation.status == status)
        
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def count_by_category(
        self,
        status: Optional[str] = None,
    ) -> dict[str, int]:
        """Get violation counts grouped by rule category."""
        from src.models.rule import Rule
        
        stmt = select(
            Rule.category,
            func.count(Violation.id),
        ).join(Violation.rule).group_by(Rule.category)
        
        if status:
            stmt = stmt.where(Violation.status == status)
        
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def update_status(
        self,
        violation_id: UUID,
        status: ViolationStatus,
        resolved_by: Optional[str] = None,
    ) -> Optional[Violation]:
        """Update violation status."""
        violation = await self.get_by_id(violation_id)
        if not violation:
            return None
        
        violation.status = status.value
        
        if status in (ViolationStatus.RESOLVED, ViolationStatus.FALSE_POSITIVE):
            violation.resolved_at = datetime.now(timezone.utc)
            violation.resolved_by = resolved_by
        
        await self.session.flush()
        return violation

    async def bulk_update_status(
        self,
        violation_ids: list[UUID],
        status: ViolationStatus,
        resolved_by: Optional[str] = None,
    ) -> int:
        """Update status for multiple violations. Returns count updated."""
        values = {"status": status.value}
        
        if status in (ViolationStatus.RESOLVED, ViolationStatus.FALSE_POSITIVE):
            values["resolved_at"] = datetime.now(timezone.utc)
            values["resolved_by"] = resolved_by
        
        stmt = (
            update(Violation)
            .where(Violation.id.in_(violation_ids))
            .values(**values)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def auto_resolve_for_ingestion(
        self,
        ingestion_id: UUID,
        active_violation_ids: set[UUID],
    ) -> int:
        """
        Auto-resolve violations from a previous ingestion that are no longer detected.
        Returns count of auto-resolved violations.
        """
        # Find open violations from previous ingestions for the same subjects
        # that are not in the current active set
        stmt = (
            update(Violation)
            .where(
                and_(
                    Violation.status == ViolationStatus.OPEN.value,
                    Violation.ingestion_id != ingestion_id,
                    ~Violation.id.in_(active_violation_ids) if active_violation_ids else True,
                )
            )
            .values(
                status=ViolationStatus.RESOLVED.value,
                resolved_at=datetime.now(timezone.utc),
                resolved_by="auto_resolved",
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def delete_by_ingestion(self, ingestion_id: UUID) -> int:
        """Delete all violations from a specific ingestion."""
        stmt = select(Violation).where(Violation.ingestion_id == ingestion_id)
        result = await self.session.execute(stmt)
        violations = result.scalars().all()
        count = len(violations)
        for v in violations:
            await self.session.delete(v)
        await self.session.flush()
        return count
