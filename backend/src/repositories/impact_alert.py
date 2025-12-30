"""Repository for Impact Alert data access (Phase 8)."""

from datetime import datetime
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.impact_alert import ImpactAlert
from src.repositories.base import BaseRepository


class ImpactAlertRepository(BaseRepository[ImpactAlert]):
    """Repository for impact alert operations."""

    model_class = ImpactAlert

    async def list_alerts(
        self,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        column_urn: Optional[str] = None,
        resolved: Optional[bool] = False,
        acknowledged: Optional[bool] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[ImpactAlert], int]:
        """List alerts with filtering and pagination.

        Args:
            alert_type: Filter by alert type
            severity: Filter by severity
            column_urn: Filter by column URN
            resolved: Filter by resolved status (default: False - show unresolved)
            acknowledged: Filter by acknowledged status
            offset: Pagination offset
            limit: Results limit

        Returns:
            Tuple of (alerts, total_count)
        """
        # Build base query
        stmt = select(ImpactAlert)

        # Apply filters
        filters = []
        if alert_type:
            filters.append(ImpactAlert.alert_type == alert_type)
        if severity:
            filters.append(ImpactAlert.severity == severity)
        if column_urn:
            filters.append(ImpactAlert.column_urn == column_urn)
        if resolved is not None:
            filters.append(ImpactAlert.resolved == resolved)
        if acknowledged is not None:
            filters.append(ImpactAlert.acknowledged == acknowledged)

        if filters:
            stmt = stmt.where(and_(*filters))

        # Get total count
        count_stmt = select(func.count()).select_from(ImpactAlert)
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Apply pagination and ordering
        stmt = stmt.offset(offset).limit(limit).order_by(
            desc(ImpactAlert.created_at)
        )

        # Execute query
        result = await self.session.execute(stmt)
        alerts = result.scalars().all()

        return alerts, total_count

    async def get_by_column(
        self,
        column_urn: str,
        resolved: Optional[bool] = None,
    ) -> Sequence[ImpactAlert]:
        """Get alerts for a specific column.

        Args:
            column_urn: The column URN
            resolved: Optional filter by resolved status

        Returns:
            List of alerts for the column
        """
        filters = [ImpactAlert.column_urn == column_urn]

        if resolved is not None:
            filters.append(ImpactAlert.resolved == resolved)

        stmt = (
            select(ImpactAlert)
            .where(and_(*filters))
            .order_by(desc(ImpactAlert.created_at))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_unresolved(
        self,
        severity: Optional[str] = None,
        limit: int = 50,
    ) -> Sequence[ImpactAlert]:
        """Get unresolved alerts.

        Args:
            severity: Optional filter by severity
            limit: Maximum number of results

        Returns:
            List of unresolved alerts
        """
        filters = [ImpactAlert.resolved == False]  # noqa: E712

        if severity:
            filters.append(ImpactAlert.severity == severity)

        stmt = (
            select(ImpactAlert)
            .where(and_(*filters))
            .order_by(
                # Sort by severity: critical > high > medium > low
                func.case(
                    (ImpactAlert.severity == "critical", 1),
                    (ImpactAlert.severity == "high", 2),
                    (ImpactAlert.severity == "medium", 3),
                    (ImpactAlert.severity == "low", 4),
                    else_=5,
                ),
                desc(ImpactAlert.created_at),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_critical_unresolved(self) -> Sequence[ImpactAlert]:
        """Get all critical unresolved alerts."""
        return await self.get_unresolved(severity="critical", limit=1000)

    async def acknowledge_alert(
        self,
        alert_id: UUID,
        acknowledged_by: str,
    ) -> Optional[ImpactAlert]:
        """Acknowledge an alert.

        Args:
            alert_id: The alert ID
            acknowledged_by: User who acknowledged

        Returns:
            The updated alert, or None if not found
        """
        stmt = select(ImpactAlert).where(ImpactAlert.id == alert_id)
        result = await self.session.execute(stmt)
        alert = result.scalar_one_or_none()

        if alert:
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.utcnow()
            await self.session.flush()

        return alert

    async def resolve_alert(
        self,
        alert_id: UUID,
    ) -> Optional[ImpactAlert]:
        """Mark an alert as resolved.

        Args:
            alert_id: The alert ID

        Returns:
            The updated alert, or None if not found
        """
        stmt = select(ImpactAlert).where(ImpactAlert.id == alert_id)
        result = await self.session.execute(stmt)
        alert = result.scalar_one_or_none()

        if alert:
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            await self.session.flush()

        return alert

    async def count_by_severity(
        self,
        resolved: Optional[bool] = False,
    ) -> dict[str, int]:
        """Count alerts by severity.

        Args:
            resolved: Optional filter by resolved status

        Returns:
            Dictionary mapping severity to count
        """
        stmt = select(
            ImpactAlert.severity,
            func.count(ImpactAlert.id),
        ).group_by(ImpactAlert.severity)

        if resolved is not None:
            stmt = stmt.where(ImpactAlert.resolved == resolved)

        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def count_by_alert_type(
        self,
        resolved: Optional[bool] = False,
    ) -> dict[str, int]:
        """Count alerts by type.

        Args:
            resolved: Optional filter by resolved status

        Returns:
            Dictionary mapping alert_type to count
        """
        stmt = select(
            ImpactAlert.alert_type,
            func.count(ImpactAlert.id),
        ).group_by(ImpactAlert.alert_type)

        if resolved is not None:
            stmt = stmt.where(ImpactAlert.resolved == resolved)

        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def get_alert_summary(self) -> dict:
        """Get summary statistics for alerts.

        Returns:
            Dictionary with alert statistics
        """
        # Total alerts
        total_stmt = select(func.count()).select_from(ImpactAlert)
        total_result = await self.session.execute(total_stmt)
        total = total_result.scalar() or 0

        # Unresolved alerts
        unresolved_stmt = (
            select(func.count())
            .select_from(ImpactAlert)
            .where(ImpactAlert.resolved == False)  # noqa: E712
        )
        unresolved_result = await self.session.execute(unresolved_stmt)
        unresolved = unresolved_result.scalar() or 0

        # Critical unresolved
        critical_stmt = (
            select(func.count())
            .select_from(ImpactAlert)
            .where(
                and_(
                    ImpactAlert.resolved == False,  # noqa: E712
                    ImpactAlert.severity == "critical",
                )
            )
        )
        critical_result = await self.session.execute(critical_stmt)
        critical = critical_result.scalar() or 0

        return {
            "total_alerts": total,
            "unresolved_alerts": unresolved,
            "critical_unresolved": critical,
            "resolved_alerts": total - unresolved,
        }
