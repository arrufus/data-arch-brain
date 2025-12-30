"""Repository for Impact History data access (Phase 8)."""

from datetime import datetime
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.impact_history import ImpactHistory
from src.repositories.base import BaseRepository


class ImpactHistoryRepository(BaseRepository[ImpactHistory]):
    """Repository for impact history operations."""

    model_class = ImpactHistory

    async def list_history(
        self,
        column_urn: Optional[str] = None,
        change_type: Optional[str] = None,
        success: Optional[bool] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[ImpactHistory], int]:
        """List impact history with filtering and pagination.

        Args:
            column_urn: Filter by column URN
            change_type: Filter by change type
            success: Filter by success status
            from_date: Start date for change_timestamp
            to_date: End date for change_timestamp
            offset: Pagination offset
            limit: Results limit

        Returns:
            Tuple of (history_entries, total_count)
        """
        # Build base query
        stmt = select(ImpactHistory)

        # Apply filters
        filters = []
        if column_urn:
            filters.append(ImpactHistory.column_urn == column_urn)
        if change_type:
            filters.append(ImpactHistory.change_type == change_type)
        if success is not None:
            filters.append(ImpactHistory.success == success)
        if from_date:
            filters.append(ImpactHistory.change_timestamp >= from_date)
        if to_date:
            filters.append(ImpactHistory.change_timestamp <= to_date)

        if filters:
            stmt = stmt.where(and_(*filters))

        # Get total count
        count_stmt = select(func.count()).select_from(ImpactHistory)
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Apply pagination and ordering
        stmt = stmt.offset(offset).limit(limit).order_by(
            desc(ImpactHistory.change_timestamp)
        )

        # Execute query
        result = await self.session.execute(stmt)
        history = result.scalars().all()

        return history, total_count

    async def get_by_change_id(
        self,
        change_id: UUID,
    ) -> Optional[ImpactHistory]:
        """Get impact history by change ID."""
        stmt = select(ImpactHistory).where(ImpactHistory.change_id == change_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_column(
        self,
        column_urn: str,
        limit: int = 50,
    ) -> Sequence[ImpactHistory]:
        """Get impact history for a specific column.

        Args:
            column_urn: The column URN
            limit: Maximum number of results

        Returns:
            List of impact history entries, ordered by most recent first
        """
        stmt = (
            select(ImpactHistory)
            .where(ImpactHistory.column_urn == column_urn)
            .order_by(desc(ImpactHistory.change_timestamp))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_similar_changes(
        self,
        column_urn: str,
        change_type: str,
        success_only: bool = True,
        limit: int = 10,
    ) -> Sequence[ImpactHistory]:
        """Find similar historical changes for learning.

        Args:
            column_urn: The column URN
            change_type: The change type to match
            success_only: Only include successful changes
            limit: Maximum number of results

        Returns:
            List of similar historical changes
        """
        filters = [ImpactHistory.change_type == change_type]

        if success_only:
            filters.append(ImpactHistory.success == True)  # noqa: E712

        stmt = (
            select(ImpactHistory)
            .where(and_(*filters))
            .order_by(desc(ImpactHistory.change_timestamp))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_success_rate(
        self,
        change_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
    ) -> float:
        """Calculate success rate for changes.

        Args:
            change_type: Optional filter by change type
            from_date: Optional filter by date

        Returns:
            Success rate as a float (0.0 to 1.0)
        """
        filters = [ImpactHistory.success.isnot(None)]

        if change_type:
            filters.append(ImpactHistory.change_type == change_type)
        if from_date:
            filters.append(ImpactHistory.change_timestamp >= from_date)

        # Count total
        total_stmt = (
            select(func.count())
            .select_from(ImpactHistory)
            .where(and_(*filters))
        )
        total_result = await self.session.execute(total_stmt)
        total = total_result.scalar() or 0

        if total == 0:
            return 0.0

        # Count successful
        success_stmt = (
            select(func.count())
            .select_from(ImpactHistory)
            .where(
                and_(
                    *filters,
                    ImpactHistory.success == True,  # noqa: E712
                )
            )
        )
        success_result = await self.session.execute(success_stmt)
        successful = success_result.scalar() or 0

        return successful / total if total > 0 else 0.0

    async def get_avg_downtime(
        self,
        change_type: Optional[str] = None,
        success_only: bool = True,
    ) -> float:
        """Calculate average downtime in seconds.

        Args:
            change_type: Optional filter by change type
            success_only: Only include successful changes

        Returns:
            Average downtime in seconds
        """
        filters = [ImpactHistory.actual_downtime_seconds.isnot(None)]

        if change_type:
            filters.append(ImpactHistory.change_type == change_type)
        if success_only:
            filters.append(ImpactHistory.success == True)  # noqa: E712

        stmt = (
            select(func.avg(ImpactHistory.actual_downtime_seconds))
            .where(and_(*filters))
        )
        result = await self.session.execute(stmt)
        avg = result.scalar()

        return float(avg) if avg is not None else 0.0

    async def count_by_change_type(
        self,
        success: Optional[bool] = None,
    ) -> dict[str, int]:
        """Count history entries by change type.

        Args:
            success: Optional filter by success status

        Returns:
            Dictionary mapping change_type to count
        """
        stmt = select(
            ImpactHistory.change_type,
            func.count(ImpactHistory.id),
        ).group_by(ImpactHistory.change_type)

        if success is not None:
            stmt = stmt.where(ImpactHistory.success == success)

        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def get_common_issues(
        self,
        change_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[tuple[str, int]]:
        """Get most common issues encountered.

        Args:
            change_type: Optional filter by change type
            limit: Maximum number of issues to return

        Returns:
            List of (issue, count) tuples, ordered by frequency
        """
        # This requires unnesting the issues_encountered array
        # Using PostgreSQL-specific unnest function
        from sqlalchemy import literal_column, text

        filters = [ImpactHistory.issues_encountered.isnot(None)]
        if change_type:
            filters.append(ImpactHistory.change_type == change_type)

        # Build query with unnest
        stmt = text("""
            SELECT issue, COUNT(*) as count
            FROM dcs.impact_history,
                 unnest(issues_encountered) as issue
            WHERE issues_encountered IS NOT NULL
            """ + (f"AND change_type = :change_type" if change_type else "") + """
            GROUP BY issue
            ORDER BY count DESC
            LIMIT :limit
        """)

        params = {"limit": limit}
        if change_type:
            params["change_type"] = change_type

        result = await self.session.execute(stmt, params)
        return [(row[0], row[1]) for row in result.all()]
