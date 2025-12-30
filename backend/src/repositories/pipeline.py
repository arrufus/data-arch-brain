"""Repository for Pipeline data access."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.capsule import Capsule
from src.models.orchestration_edge import TaskDataEdge, TaskDependencyEdge
from src.models.pipeline import Pipeline, PipelineTask
from src.repositories.base import BaseRepository


class PipelineRepository(BaseRepository[Pipeline]):
    """Repository for pipeline operations."""

    model_class = Pipeline

    async def list_pipelines(
        self,
        pipeline_type: Optional[str] = None,
        source_system_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        is_paused: Optional[bool] = None,
        search_query: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[Pipeline], int]:
        """List pipelines with filtering and pagination.

        Returns:
            Tuple of (pipelines, total_count)
        """
        # Build base query
        stmt = select(Pipeline).options(
            selectinload(Pipeline.source_system),
        )

        # Apply filters
        filters = []
        if pipeline_type:
            filters.append(Pipeline.pipeline_type == pipeline_type)
        if source_system_id:
            filters.append(Pipeline.source_system_id == source_system_id)
        if is_active is not None:
            filters.append(Pipeline.is_active == is_active)
        if is_paused is not None:
            filters.append(Pipeline.is_paused == is_paused)
        if search_query:
            search_pattern = f"%{search_query}%"
            filters.append(
                or_(
                    Pipeline.name.ilike(search_pattern),
                    Pipeline.description.ilike(search_pattern),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        # Get total count
        count_stmt = select(func.count()).select_from(Pipeline)
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Apply pagination
        stmt = stmt.offset(offset).limit(limit).order_by(Pipeline.name)

        # Execute query
        result = await self.session.execute(stmt)
        pipelines = result.scalars().all()

        return pipelines, total_count

    async def get_by_urn(self, urn: str) -> Optional[Pipeline]:
        """Get pipeline by URN with related data eagerly loaded."""
        stmt = (
            select(Pipeline)
            .options(
                selectinload(Pipeline.source_system),
                selectinload(Pipeline.tasks),
            )
            .where(Pipeline.urn == urn)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tasks(
        self,
        pipeline_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[PipelineTask]:
        """Get tasks for a specific pipeline."""
        stmt = (
            select(PipelineTask)
            .where(PipelineTask.pipeline_id == pipeline_id)
            .offset(offset)
            .limit(limit)
            .order_by(PipelineTask.name)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_data_footprint(
        self,
        pipeline_id: UUID,
    ) -> dict[str, list[dict]]:
        """Get data footprint (all capsules touched) by a pipeline.

        Returns:
            Dictionary with 'produces', 'consumes', 'transforms', 'validates' keys,
            each containing a list of capsule dictionaries.
        """
        # Get all tasks for this pipeline
        tasks_result = await self.session.execute(
            select(PipelineTask.id).where(PipelineTask.pipeline_id == pipeline_id)
        )
        task_ids = [row[0] for row in tasks_result.all()]

        if not task_ids:
            return {
                "produces": [],
                "consumes": [],
                "transforms": [],
                "validates": [],
            }

        # Query task-data edges grouped by edge type
        footprint = {
            "produces": [],
            "consumes": [],
            "transforms": [],
            "validates": [],
        }

        for edge_type in ["produces", "consumes", "transforms", "validates"]:
            stmt = (
                select(TaskDataEdge, Capsule)
                .join(Capsule, TaskDataEdge.capsule_id == Capsule.id)
                .where(
                    and_(
                        TaskDataEdge.task_id.in_(task_ids),
                        TaskDataEdge.edge_type == edge_type,
                    )
                )
            )
            result = await self.session.execute(stmt)
            rows = result.all()

            capsule_data = []
            for edge, capsule in rows:
                capsule_data.append(
                    {
                        "capsule_urn": capsule.urn,
                        "capsule_name": capsule.name,
                        "capsule_type": capsule.capsule_type,
                        "schema_name": capsule.schema_name,
                        "operation": edge.operation,
                        "access_pattern": edge.access_pattern,
                    }
                )

            footprint[edge_type] = capsule_data

        return footprint

    async def get_task_dependencies(
        self,
        pipeline_id: UUID,
    ) -> Sequence[TaskDependencyEdge]:
        """Get task dependency edges for a specific pipeline."""
        # Get all tasks for this pipeline
        tasks_result = await self.session.execute(
            select(PipelineTask.id).where(PipelineTask.pipeline_id == pipeline_id)
        )
        task_ids = [row[0] for row in tasks_result.all()]

        if not task_ids:
            return []

        # Query task dependency edges where both source and target are in this pipeline
        stmt = (
            select(TaskDependencyEdge)
            .where(
                and_(
                    TaskDependencyEdge.source_task_id.in_(task_ids),
                    TaskDependencyEdge.target_task_id.in_(task_ids),
                )
            )
            .order_by(TaskDependencyEdge.source_task_urn)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_type(self) -> dict[str, int]:
        """Count pipelines by type."""
        stmt = (
            select(Pipeline.pipeline_type, func.count(Pipeline.id)).group_by(
                Pipeline.pipeline_type
            )
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def count_by_source_system(self) -> dict[str, int]:
        """Count pipelines by source system."""
        from src.models.source_system import SourceSystem

        stmt = (
            select(SourceSystem.name, func.count(Pipeline.id))
            .join(Pipeline, SourceSystem.id == Pipeline.source_system_id)
            .group_by(SourceSystem.name)
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}


class TaskDataEdgeRepository(BaseRepository[TaskDataEdge]):
    """Repository for TaskDataEdge operations."""

    model_class = TaskDataEdge

    async def get_producers(
        self,
        capsule_urn: str,
        offset: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        """Get tasks that produce a specific capsule.

        Returns:
            List of dictionaries containing task and pipeline information.
        """
        stmt = (
            select(TaskDataEdge, PipelineTask, Pipeline)
            .join(PipelineTask, TaskDataEdge.task_id == PipelineTask.id)
            .join(Pipeline, PipelineTask.pipeline_id == Pipeline.id)
            .where(
                and_(
                    TaskDataEdge.capsule_urn == capsule_urn,
                    TaskDataEdge.edge_type == "produces",
                )
            )
            .offset(offset)
            .limit(limit)
            .order_by(Pipeline.name, PipelineTask.name)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        producers = []
        for edge, task, pipeline in rows:
            producers.append(
                {
                    "task_urn": task.urn,
                    "task_name": task.name,
                    "task_type": task.task_type,
                    "pipeline_urn": pipeline.urn,
                    "pipeline_name": pipeline.name,
                    "pipeline_type": pipeline.pipeline_type,
                    "operation": edge.operation,
                }
            )

        return producers

    async def get_consumers(
        self,
        capsule_urn: str,
        offset: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        """Get tasks that consume a specific capsule.

        Returns:
            List of dictionaries containing task and pipeline information.
        """
        stmt = (
            select(TaskDataEdge, PipelineTask, Pipeline)
            .join(PipelineTask, TaskDataEdge.task_id == PipelineTask.id)
            .join(Pipeline, PipelineTask.pipeline_id == Pipeline.id)
            .where(
                and_(
                    TaskDataEdge.capsule_urn == capsule_urn,
                    TaskDataEdge.edge_type == "consumes",
                )
            )
            .offset(offset)
            .limit(limit)
            .order_by(Pipeline.name, PipelineTask.name)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        consumers = []
        for edge, task, pipeline in rows:
            consumers.append(
                {
                    "task_urn": task.urn,
                    "task_name": task.name,
                    "task_type": task.task_type,
                    "pipeline_urn": pipeline.urn,
                    "pipeline_name": pipeline.name,
                    "pipeline_type": pipeline.pipeline_type,
                    "access_pattern": edge.access_pattern,
                }
            )

        return consumers

    async def get_by_task(
        self,
        task_urn: str,
    ) -> Sequence[TaskDataEdge]:
        """Get all task-data edges for a specific task."""
        stmt = (
            select(TaskDataEdge)
            .where(TaskDataEdge.task_urn == task_urn)
            .order_by(TaskDataEdge.edge_type, TaskDataEdge.capsule_urn)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_pipeline(
        self,
        pipeline_urn: str,
    ) -> Sequence[TaskDataEdge]:
        """Get all task-data edges for tasks within a pipeline."""
        # Extract pipeline URN prefix to match task URNs
        # Task URN format: urn:dcs:task:airflow:{instance}:{pipeline_id}.{task_id}
        # Pipeline URN format: urn:dcs:pipeline:airflow:{instance}:{pipeline_id}

        # Get all tasks with URNs starting with the pipeline prefix
        stmt = (
            select(TaskDataEdge)
            .join(PipelineTask, TaskDataEdge.task_id == PipelineTask.id)
            .where(PipelineTask.pipeline_urn == pipeline_urn)
            .order_by(TaskDataEdge.task_urn, TaskDataEdge.edge_type)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_edge_type(self) -> dict[str, int]:
        """Count task-data edges by edge type."""
        stmt = (
            select(TaskDataEdge.edge_type, func.count(TaskDataEdge.id)).group_by(
                TaskDataEdge.edge_type
            )
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
