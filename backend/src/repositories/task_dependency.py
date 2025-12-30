"""Repository for Task Dependency data access (Phase 8)."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.capsule import Capsule
from src.models.task_dependency import TaskDependency
from src.repositories.base import BaseRepository


class TaskDependencyRepository(BaseRepository[TaskDependency]):
    """Repository for task dependency operations."""

    model_class = TaskDependency

    async def list_dependencies(
        self,
        capsule_id: Optional[UUID] = None,
        dag_id: Optional[str] = None,
        task_id: Optional[str] = None,
        dependency_type: Optional[str] = None,
        is_active: Optional[bool] = True,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[TaskDependency], int]:
        """List task dependencies with filtering and pagination.

        Args:
            capsule_id: Filter by capsule ID
            dag_id: Filter by DAG ID
            task_id: Filter by task ID
            dependency_type: Filter by dependency type (read, write, transform)
            is_active: Filter by active status (default: True)
            offset: Pagination offset
            limit: Results limit

        Returns:
            Tuple of (dependencies, total_count)
        """
        # Build base query
        stmt = select(TaskDependency).options(
            selectinload(TaskDependency.capsule),
        )

        # Apply filters
        filters = []
        if capsule_id:
            filters.append(TaskDependency.capsule_id == capsule_id)
        if dag_id:
            filters.append(TaskDependency.dag_id == dag_id)
        if task_id:
            filters.append(TaskDependency.task_id == task_id)
        if dependency_type:
            filters.append(TaskDependency.dependency_type == dependency_type)
        if is_active is not None:
            filters.append(TaskDependency.is_active == is_active)

        if filters:
            stmt = stmt.where(and_(*filters))

        # Get total count
        count_stmt = select(func.count()).select_from(TaskDependency)
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Apply pagination
        stmt = stmt.offset(offset).limit(limit).order_by(
            TaskDependency.dag_id, TaskDependency.task_id
        )

        # Execute query
        result = await self.session.execute(stmt)
        dependencies = result.scalars().all()

        return dependencies, total_count

    async def get_by_dag_and_task(
        self,
        dag_id: str,
        task_id: str,
    ) -> Sequence[TaskDependency]:
        """Get all dependencies for a specific DAG task."""
        stmt = (
            select(TaskDependency)
            .options(selectinload(TaskDependency.capsule))
            .where(
                and_(
                    TaskDependency.dag_id == dag_id,
                    TaskDependency.task_id == task_id,
                )
            )
            .order_by(TaskDependency.dependency_type)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_capsule(
        self,
        capsule_id: UUID,
        dependency_type: Optional[str] = None,
    ) -> Sequence[TaskDependency]:
        """Get all tasks that depend on a specific capsule.

        Args:
            capsule_id: The capsule ID
            dependency_type: Optional filter by dependency type

        Returns:
            List of task dependencies
        """
        filters = [TaskDependency.capsule_id == capsule_id]
        if dependency_type:
            filters.append(TaskDependency.dependency_type == dependency_type)

        stmt = (
            select(TaskDependency)
            .where(and_(*filters))
            .order_by(TaskDependency.dag_id, TaskDependency.task_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_readers(
        self,
        capsule_id: UUID,
    ) -> Sequence[TaskDependency]:
        """Get all tasks that read from a specific capsule."""
        return await self.get_by_capsule(capsule_id, dependency_type="read")

    async def get_writers(
        self,
        capsule_id: UUID,
    ) -> Sequence[TaskDependency]:
        """Get all tasks that write to a specific capsule."""
        return await self.get_by_capsule(capsule_id, dependency_type="write")

    async def get_transformers(
        self,
        capsule_id: UUID,
    ) -> Sequence[TaskDependency]:
        """Get all tasks that transform a specific capsule."""
        return await self.get_by_capsule(capsule_id, dependency_type="transform")

    async def get_critical_tasks(
        self,
        capsule_id: UUID,
        min_criticality: float = 0.7,
    ) -> Sequence[TaskDependency]:
        """Get high-criticality tasks that depend on a capsule.

        Args:
            capsule_id: The capsule ID
            min_criticality: Minimum criticality score (0.0-1.0)

        Returns:
            List of high-criticality task dependencies
        """
        stmt = (
            select(TaskDependency)
            .where(
                and_(
                    TaskDependency.capsule_id == capsule_id,
                    TaskDependency.criticality_score >= min_criticality,
                    TaskDependency.is_active == True,  # noqa: E712
                )
            )
            .order_by(TaskDependency.criticality_score.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_dependency_type(
        self,
        capsule_id: Optional[UUID] = None,
    ) -> dict[str, int]:
        """Count dependencies by type.

        Args:
            capsule_id: Optional capsule ID to filter by

        Returns:
            Dictionary mapping dependency_type to count
        """
        stmt = select(
            TaskDependency.dependency_type,
            func.count(TaskDependency.id),
        ).group_by(TaskDependency.dependency_type)

        if capsule_id:
            stmt = stmt.where(TaskDependency.capsule_id == capsule_id)

        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def count_by_dag(self) -> dict[str, int]:
        """Count dependencies by DAG ID."""
        stmt = (
            select(TaskDependency.dag_id, func.count(TaskDependency.id))
            .group_by(TaskDependency.dag_id)
            .order_by(func.count(TaskDependency.id).desc())
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def upsert_dependency(
        self,
        dag_id: str,
        task_id: str,
        capsule_id: UUID,
        dependency_type: str,
        **kwargs,
    ) -> TaskDependency:
        """Create or update a task dependency.

        Args:
            dag_id: DAG ID
            task_id: Task ID
            capsule_id: Capsule ID
            dependency_type: Dependency type (read/write/transform)
            **kwargs: Additional fields to update

        Returns:
            The created or updated TaskDependency
        """
        # Check if dependency exists
        stmt = select(TaskDependency).where(
            and_(
                TaskDependency.dag_id == dag_id,
                TaskDependency.task_id == task_id,
                TaskDependency.capsule_id == capsule_id,
            )
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            for key, value in kwargs.items():
                setattr(existing, key, value)
            existing.dependency_type = dependency_type
            await self.session.flush()
            return existing
        else:
            # Create new
            new_dep = TaskDependency(
                dag_id=dag_id,
                task_id=task_id,
                capsule_id=capsule_id,
                dependency_type=dependency_type,
                **kwargs,
            )
            self.session.add(new_dep)
            await self.session.flush()
            return new_dep
