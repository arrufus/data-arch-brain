"""Pipeline orchestration endpoints (Phase 4)."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.api.exceptions import NotFoundError
from src.database import DbSession
from src.repositories.pipeline import PipelineRepository, TaskDataEdgeRepository

router = APIRouter(prefix="/pipelines")


# ============================================================================
# Response Models
# ============================================================================


class PipelineSummary(BaseModel):
    """Summary view of a pipeline."""

    id: str
    urn: str
    name: str
    pipeline_type: str
    source_system: Optional[str] = None
    schedule_interval: Optional[str] = None
    is_active: bool
    is_paused: bool
    description: Optional[str] = None


class PipelineDetail(PipelineSummary):
    """Detailed view of a pipeline."""

    owners: list[str] = []
    config: dict = {}
    task_count: int = 0
    first_seen: str
    last_seen: str


class TaskSummary(BaseModel):
    """Summary view of a pipeline task."""

    id: str
    urn: str
    name: str
    task_type: str
    operator: Optional[str] = None
    operation_type: Optional[str] = None
    description: Optional[str] = None


class TaskDetail(TaskSummary):
    """Detailed view of a pipeline task."""

    pipeline_urn: str
    retries: int = 0
    retry_delay: Optional[int] = None  # seconds
    timeout: Optional[int] = None  # seconds
    tool_reference: Optional[dict] = None
    doc_md: Optional[str] = None
    meta: dict = {}


class CapsuleReference(BaseModel):
    """Reference to a capsule in data footprint."""

    capsule_urn: str
    capsule_name: str
    capsule_type: str
    schema_name: Optional[str] = None
    operation: Optional[str] = None
    access_pattern: Optional[str] = None


class DataFootprint(BaseModel):
    """Data footprint for a pipeline."""

    produces: list[CapsuleReference] = []
    consumes: list[CapsuleReference] = []
    transforms: list[CapsuleReference] = []
    validates: list[CapsuleReference] = []


class TaskDependency(BaseModel):
    """Task dependency edge."""

    source_task_urn: str
    target_task_urn: str
    edge_type: str


class PipelineListResponse(BaseModel):
    """Response for pipeline list."""

    data: list[PipelineSummary]
    pagination: dict


class TaskListResponse(BaseModel):
    """Response for task list."""

    data: list[TaskSummary]
    pagination: dict


# ============================================================================
# Pipeline Endpoints
# ============================================================================


@router.get("", response_model=PipelineListResponse)
async def list_pipelines(
    db: DbSession,
    pipeline_type: Optional[str] = Query(None, description="Filter by pipeline type"),
    source_system_id: Optional[UUID] = Query(None, description="Filter by source system ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_paused: Optional[bool] = Query(None, description="Filter by paused status"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
) -> PipelineListResponse:
    """List pipelines with filtering and pagination.

    Returns a paginated list of pipelines with optional filtering by type,
    source system, active/paused status, or text search.
    """
    repo = PipelineRepository(db)

    pipelines, total = await repo.list_pipelines(
        pipeline_type=pipeline_type,
        source_system_id=source_system_id,
        is_active=is_active,
        is_paused=is_paused,
        search_query=search,
        offset=offset,
        limit=limit,
    )

    data = [
        PipelineSummary(
            id=str(p.id),
            urn=p.urn,
            name=p.name,
            pipeline_type=p.pipeline_type,
            source_system=p.source_system.name if p.source_system else None,
            schedule_interval=p.schedule_interval,
            is_active=p.is_active,
            is_paused=p.is_paused,
            description=p.description,
        )
        for p in pipelines
    ]

    return PipelineListResponse(
        data=data,
        pagination={
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + len(data) < total,
        },
    )


@router.get("/stats")
async def get_pipeline_stats(db: DbSession) -> dict:
    """Get aggregated statistics about pipelines.

    Returns counts by pipeline type and source system, plus overall totals.
    """
    repo = PipelineRepository(db)

    by_type = await repo.count_by_type()
    by_source_system = await repo.count_by_source_system()
    total = await repo.count()

    return {
        "total_pipelines": total,
        "by_type": by_type,
        "by_source_system": by_source_system,
    }


@router.get("/{urn:path}", response_model=PipelineDetail)
async def get_pipeline(
    urn: str,
    db: DbSession,
) -> PipelineDetail:
    """Get pipeline details by URN.

    Returns detailed information about a pipeline including its configuration,
    owners, and task count.
    """
    repo = PipelineRepository(db)
    pipeline = await repo.get_by_urn(urn)

    if not pipeline:
        raise NotFoundError("Pipeline", urn)

    # Get task count
    tasks = await repo.get_tasks(pipeline.id)

    return PipelineDetail(
        id=str(pipeline.id),
        urn=pipeline.urn,
        name=pipeline.name,
        pipeline_type=pipeline.pipeline_type,
        source_system=pipeline.source_system.name if pipeline.source_system else None,
        schedule_interval=pipeline.schedule_interval,
        is_active=pipeline.is_active,
        is_paused=pipeline.is_paused,
        description=pipeline.description,
        owners=pipeline.owners,
        config=pipeline.config,
        task_count=len(tasks),
        first_seen=pipeline.first_seen.isoformat(),
        last_seen=pipeline.last_seen.isoformat(),
    )


@router.get("/{urn:path}/tasks", response_model=TaskListResponse)
async def get_pipeline_tasks(
    urn: str,
    db: DbSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
) -> TaskListResponse:
    """Get tasks for a specific pipeline.

    Returns a paginated list of all tasks within the specified pipeline.
    """
    repo = PipelineRepository(db)
    pipeline = await repo.get_by_urn(urn)

    if not pipeline:
        raise NotFoundError("Pipeline", urn)

    tasks = await repo.get_tasks(pipeline.id, offset=offset, limit=limit)

    data = [
        TaskSummary(
            id=str(t.id),
            urn=t.urn,
            name=t.name,
            task_type=t.task_type,
            operator=t.operator,
            operation_type=t.operation_type,
            description=t.description,
        )
        for t in tasks
    ]

    # Get total count (without pagination)
    all_tasks = await repo.get_tasks(pipeline.id)
    total = len(all_tasks)

    return TaskListResponse(
        data=data,
        pagination={
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + len(data) < total,
        },
    )


@router.get("/{urn:path}/data-footprint", response_model=DataFootprint)
async def get_pipeline_data_footprint(
    urn: str,
    db: DbSession,
) -> DataFootprint:
    """Get data footprint for a pipeline.

    Returns all data capsules that this pipeline produces, consumes, transforms,
    or validates.
    """
    repo = PipelineRepository(db)
    pipeline = await repo.get_by_urn(urn)

    if not pipeline:
        raise NotFoundError("Pipeline", urn)

    footprint = await repo.get_data_footprint(pipeline.id)

    return DataFootprint(
        produces=[
            CapsuleReference(
                capsule_urn=c["capsule_urn"],
                capsule_name=c["capsule_name"],
                capsule_type=c["capsule_type"],
                schema_name=c["schema_name"],
                operation=c["operation"],
            )
            for c in footprint["produces"]
        ],
        consumes=[
            CapsuleReference(
                capsule_urn=c["capsule_urn"],
                capsule_name=c["capsule_name"],
                capsule_type=c["capsule_type"],
                schema_name=c["schema_name"],
                access_pattern=c["access_pattern"],
            )
            for c in footprint["consumes"]
        ],
        transforms=[
            CapsuleReference(
                capsule_urn=c["capsule_urn"],
                capsule_name=c["capsule_name"],
                capsule_type=c["capsule_type"],
                schema_name=c["schema_name"],
            )
            for c in footprint["transforms"]
        ],
        validates=[
            CapsuleReference(
                capsule_urn=c["capsule_urn"],
                capsule_name=c["capsule_name"],
                capsule_type=c["capsule_type"],
                schema_name=c["schema_name"],
            )
            for c in footprint["validates"]
        ],
    )


@router.get("/{urn:path}/dependencies")
async def get_pipeline_dependencies(
    urn: str,
    db: DbSession,
) -> dict:
    """Get task dependency graph for a pipeline.

    Returns all task-to-task dependencies within the pipeline as a graph structure.
    """
    repo = PipelineRepository(db)
    pipeline = await repo.get_by_urn(urn)

    if not pipeline:
        raise NotFoundError("Pipeline", urn)

    dependencies = await repo.get_task_dependencies(pipeline.id)

    edges = [
        TaskDependency(
            source_task_urn=d.source_task_urn,
            target_task_urn=d.target_task_urn,
            edge_type=d.edge_type,
        )
        for d in dependencies
    ]

    # Extract unique task URNs
    task_urns = set()
    for dep in dependencies:
        task_urns.add(dep.source_task_urn)
        task_urns.add(dep.target_task_urn)

    return {
        "pipeline_urn": urn,
        "task_count": len(task_urns),
        "dependency_count": len(edges),
        "dependencies": [
            {
                "source": e.source_task_urn,
                "target": e.target_task_urn,
                "type": e.edge_type,
            }
            for e in edges
        ],
    }
