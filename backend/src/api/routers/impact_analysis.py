"""Impact Analysis API endpoints for Phase 8.

Provides endpoints for advanced impact analysis including:
- Task-level impact analysis
- Task dependency queries
- Impact history tracking
- Impact alert management
"""

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.api.exceptions import NotFoundError, ValidationError_
from src.database import DbSession
from src.services.impact_simulation import ImpactSimulator
from src.services.task_impact import TaskImpactService
from src.repositories.task_dependency import TaskDependencyRepository
from src.repositories.impact_history import ImpactHistoryRepository
from src.repositories.impact_alert import ImpactAlertRepository

router = APIRouter(prefix="/impact")


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class TaskImpactDetail(BaseModel):
    """Details of a single task impact."""

    dag_id: str
    task_id: str
    dependency_type: str
    schedule_interval: Optional[str]
    criticality_score: Optional[float]
    success_rate: Optional[float]
    last_execution_time: Optional[str]
    avg_execution_duration_seconds: Optional[int]
    risk_score: float
    risk_level: str
    is_active: bool


class DAGImpactDetail(BaseModel):
    """Aggregated impact at DAG level."""

    dag_id: str
    affected_task_count: int
    critical_task_count: int
    high_risk_task_count: int
    max_risk_score: float
    avg_risk_score: float
    tasks: list[TaskImpactDetail]


class ColumnReference(BaseModel):
    """Reference to an affected column."""

    column_urn: str
    capsule_urn: Optional[str]
    data_type: Optional[str]


class TimeWindowResponse(BaseModel):
    """Time window for impact assessment."""

    start: str  # ISO 8601 timestamp
    end: str  # ISO 8601 timestamp
    impact_score: float
    reason: str


class TemporalImpactResponse(BaseModel):
    """Temporal impact analysis response."""

    schedule_pattern: str
    next_execution: Optional[str]  # ISO 8601 timestamp
    executions_per_day: float
    executions_per_week: float
    peak_execution_hours: list[int]
    low_impact_windows: list[TimeWindowResponse]
    high_impact_windows: list[TimeWindowResponse]
    estimated_downtime_minutes: float
    affected_time_periods: dict[str, int]


class TaskImpactAnalysisResponse(BaseModel):
    """Response for task-level impact analysis."""

    total_tasks: int
    total_dags: int
    critical_tasks: int
    risk_level: str
    confidence_score: float
    tasks: list[TaskImpactDetail]
    dags: list[DAGImpactDetail]
    affected_columns: list[ColumnReference]
    temporal_impact: Optional[TemporalImpactResponse] = None


class SimulationRequest(BaseModel):
    """Request for impact simulation."""

    column_urn: str = Field(..., description="URN of the column to change")
    change_type: str = Field(
        ...,
        description="Type of change: delete, rename, type_change, nullability, default",
    )
    change_params: dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the change"
    )
    scheduled_for: Optional[str] = Field(
        None, description="When the change will occur (ISO 8601 timestamp, default: now)"
    )
    include_temporal: bool = Field(
        True, description="Include temporal impact analysis"
    )
    depth: int = Field(5, ge=1, le=10, description="Lineage depth to traverse (1-10)")


class SimulationResponse(BaseModel):
    """Response for impact simulation."""

    simulation_id: str
    column_urn: str
    change_type: str
    change_params: dict[str, Any]

    # Impact predictions
    task_impact: dict[str, Any]
    temporal_impact: Optional[dict[str, Any]]
    affected_columns_count: int
    affected_tasks_count: int
    affected_dags_count: int

    # Historical insights
    similar_changes_count: int
    historical_success_rate: float
    avg_historical_downtime: float

    # Recommendations
    recommendations: list[str]
    warnings: list[str]
    best_deployment_window: Optional[dict[str, Any]]

    # Metadata
    confidence_score: float
    simulated_at: str
    scheduled_for: Optional[str]


class TaskDependencyResponse(BaseModel):
    """Task dependency information."""

    id: str
    dag_id: str
    task_id: str
    capsule_id: Optional[str]
    dependency_type: str
    schedule_interval: Optional[str]
    is_active: bool
    criticality_score: Optional[float]
    success_rate: Optional[float]
    last_execution_time: Optional[str]
    created_at: str
    updated_at: str


class TaskDependencyListResponse(BaseModel):
    """Paginated list of task dependencies."""

    dependencies: list[TaskDependencyResponse]
    total: int
    offset: int
    limit: int


class TaskDependencySummaryResponse(BaseModel):
    """Summary statistics for task dependencies."""

    total_dependencies: int
    active_dependencies: int
    unique_dags: int
    critical_tasks: int
    dependencies_by_type: dict[str, int]


class ImpactHistoryResponse(BaseModel):
    """Impact history entry."""

    id: str
    change_id: str
    column_urn: str
    change_type: str
    predicted_risk_level: Optional[str]
    actual_risk_level: Optional[str]
    success: Optional[bool]
    downtime_minutes: Optional[float]
    changed_by: Optional[str]
    change_timestamp: str


class ImpactHistoryListResponse(BaseModel):
    """Paginated list of impact history."""

    history: list[ImpactHistoryResponse]
    total: int
    offset: int
    limit: int


class ImpactAlertResponse(BaseModel):
    """Impact alert information."""

    id: str
    alert_type: str
    severity: str
    column_urn: str
    change_type: str
    alert_message: str
    recommendation: Optional[str]
    acknowledged: bool
    resolved: bool
    created_at: str


class ImpactAlertListResponse(BaseModel):
    """Paginated list of impact alerts."""

    alerts: list[ImpactAlertResponse]
    total: int
    offset: int
    limit: int


class AlertSummaryResponse(BaseModel):
    """Alert summary statistics."""

    total_alerts: int
    unresolved_alerts: int
    critical_unresolved: int
    resolved_alerts: int


# ---------------------------------------------------------------------------
# Endpoints - Task Impact Analysis
# ---------------------------------------------------------------------------


@router.post("/analyze/column/{column_urn:path}", response_model=TaskImpactAnalysisResponse)
async def analyze_column_impact(
    column_urn: str,
    db: DbSession,
    change_type: str = Query(
        ...,
        description="Type of change: delete, rename, type_change, nullability, default",
    ),
    depth: int = Query(
        5,
        ge=1,
        le=10,
        description="Lineage depth to traverse (1-10)",
    ),
    include_temporal: bool = Query(
        False,
        description="Include temporal impact analysis (schedule-based predictions)",
    ),
    change_timestamp: Optional[str] = Query(
        None,
        description="When the change will occur (ISO 8601 timestamp, default: now)",
    ),
) -> TaskImpactAnalysisResponse:
    """
    Analyze task-level impact of a column change.

    Calculates which Airflow tasks will be affected by a schema change to the specified column.
    Uses column lineage to identify all downstream columns and then finds tasks that depend
    on those columns.

    **Risk Scoring Factors:**
    - Dependency type (read, write, transform)
    - Change severity (delete > type_change > rename > nullability > default)
    - Task criticality score
    - Task success rate
    - Execution frequency

    **Change Types:**
    - `delete`: Remove column entirely (highest risk)
    - `rename`: Change column name
    - `type_change`: Modify data type
    - `nullability`: Add/remove NOT NULL constraint
    - `default`: Add/change default value (lowest risk)

    **Temporal Impact (Optional):**
    When `include_temporal=true`, response includes:
    - Next execution times for affected tasks
    - Execution frequency (per day/week)
    - Peak execution hours
    - Low-impact deployment windows
    - Estimated downtime
    """
    service = TaskImpactService(db)

    # Parse change timestamp if provided
    parsed_timestamp = None
    if change_timestamp:
        try:
            parsed_timestamp = datetime.fromisoformat(change_timestamp.replace("Z", "+00:00"))
        except ValueError:
            raise ValidationError_(f"Invalid timestamp format: {change_timestamp}")

    try:
        result = await service.analyze_column_impact(
            column_urn=column_urn,
            change_type=change_type,
            depth=depth,
            include_temporal=include_temporal,
            change_timestamp=parsed_timestamp,
        )
    except ValueError as e:
        raise NotFoundError(str(e))

    # Build temporal impact response if available
    temporal_impact_response = None
    if result.temporal_impact:
        temporal_impact_response = TemporalImpactResponse(
            schedule_pattern=result.temporal_impact["schedule_pattern"],
            next_execution=result.temporal_impact.get("next_execution"),
            executions_per_day=result.temporal_impact["executions_per_day"],
            executions_per_week=result.temporal_impact["executions_per_week"],
            peak_execution_hours=result.temporal_impact["peak_execution_hours"],
            low_impact_windows=[
                TimeWindowResponse(**w) for w in result.temporal_impact["low_impact_windows"]
            ],
            high_impact_windows=[
                TimeWindowResponse(**w) for w in result.temporal_impact["high_impact_windows"]
            ],
            estimated_downtime_minutes=result.temporal_impact["estimated_downtime_minutes"],
            affected_time_periods=result.temporal_impact["affected_time_periods"],
        )

    return TaskImpactAnalysisResponse(
        total_tasks=result.total_tasks,
        total_dags=result.total_dags,
        critical_tasks=result.critical_tasks,
        risk_level=result.risk_level,
        confidence_score=result.confidence_score,
        tasks=[TaskImpactDetail(**task) for task in result.tasks],
        dags=[DAGImpactDetail(**dag) for dag in result.dags],
        affected_columns=[ColumnReference(**col) for col in result.affected_columns],
        temporal_impact=temporal_impact_response,
    )


# ---------------------------------------------------------------------------
# Endpoints - Task Dependencies
# ---------------------------------------------------------------------------


@router.get("/dependencies", response_model=TaskDependencyListResponse)
async def list_task_dependencies(
    db: DbSession,
    capsule_id: Optional[UUID] = Query(None, description="Filter by capsule ID"),
    dag_id: Optional[str] = Query(None, description="Filter by DAG ID"),
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    dependency_type: Optional[str] = Query(None, description="Filter by type (read, write, transform)"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Results limit"),
) -> TaskDependencyListResponse:
    """
    List task dependencies with filtering and pagination.

    Returns tasks that depend on data capsules, showing:
    - Which DAGs/tasks read from which capsules
    - Which DAGs/tasks write to which capsules
    - Which DAGs/tasks transform which capsules

    Use filters to narrow results to specific capsules, DAGs, or tasks.
    """
    repo = TaskDependencyRepository(db)

    dependencies, total = await repo.list_dependencies(
        capsule_id=capsule_id,
        dag_id=dag_id,
        task_id=task_id,
        dependency_type=dependency_type,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )

    return TaskDependencyListResponse(
        dependencies=[
            TaskDependencyResponse(
                id=str(dep.id),
                dag_id=dep.dag_id,
                task_id=dep.task_id,
                capsule_id=str(dep.capsule_id) if dep.capsule_id else None,
                dependency_type=dep.dependency_type,
                schedule_interval=dep.schedule_interval,
                is_active=dep.is_active,
                criticality_score=float(dep.criticality_score) if dep.criticality_score else None,
                success_rate=float(dep.success_rate) if dep.success_rate else None,
                last_execution_time=dep.last_execution_time.isoformat() if dep.last_execution_time else None,
                created_at=dep.created_at.isoformat(),
                updated_at=dep.updated_at.isoformat(),
            )
            for dep in dependencies
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/dependencies/summary", response_model=TaskDependencySummaryResponse)
async def get_task_dependencies_summary(
    db: DbSession,
    capsule_id: Optional[UUID] = Query(None, description="Filter by capsule ID"),
    dag_id: Optional[str] = Query(None, description="Filter by DAG ID"),
) -> TaskDependencySummaryResponse:
    """
    Get summary statistics for task dependencies.

    Provides aggregate counts:
    - Total dependencies
    - Active dependencies
    - Unique DAGs
    - Critical tasks (high criticality score)
    - Breakdown by dependency type
    """
    service = TaskImpactService(db)

    summary = await service.get_task_dependencies_summary(
        capsule_id=capsule_id,
        dag_id=dag_id,
    )

    return TaskDependencySummaryResponse(**summary)


@router.get("/dependencies/capsule/{capsule_id}", response_model=list[TaskDependencyResponse])
async def get_capsule_dependencies(
    capsule_id: UUID,
    db: DbSession,
    dependency_type: Optional[str] = Query(None, description="Filter by type (read, write, transform)"),
) -> list[TaskDependencyResponse]:
    """
    Get all tasks that depend on a specific capsule.

    Shows which Airflow tasks interact with the capsule and how:
    - **read**: Task reads data from this capsule
    - **write**: Task writes data to this capsule
    - **transform**: Task transforms this capsule
    """
    repo = TaskDependencyRepository(db)

    dependencies = await repo.get_by_capsule(
        capsule_id=capsule_id,
        dependency_type=dependency_type,
    )

    return [
        TaskDependencyResponse(
            id=str(dep.id),
            dag_id=dep.dag_id,
            task_id=dep.task_id,
            capsule_id=str(dep.capsule_id) if dep.capsule_id else None,
            dependency_type=dep.dependency_type,
            schedule_interval=dep.schedule_interval,
            is_active=dep.is_active,
            criticality_score=float(dep.criticality_score) if dep.criticality_score else None,
            success_rate=float(dep.success_rate) if dep.success_rate else None,
            last_execution_time=dep.last_execution_time.isoformat() if dep.last_execution_time else None,
            created_at=dep.created_at.isoformat(),
            updated_at=dep.updated_at.isoformat(),
        )
        for dep in dependencies
    ]


# ---------------------------------------------------------------------------
# Endpoints - Impact History
# ---------------------------------------------------------------------------


@router.get("/history", response_model=ImpactHistoryListResponse)
async def list_impact_history(
    db: DbSession,
    column_urn: Optional[str] = Query(None, description="Filter by column URN"),
    change_type: Optional[str] = Query(None, description="Filter by change type"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Results limit"),
) -> ImpactHistoryListResponse:
    """
    List historical schema changes and their impact.

    Tracks past changes to learn from:
    - Predicted vs actual risk
    - Downtime experienced
    - Issues encountered
    - Resolutions applied

    Use this to improve future impact predictions.
    """
    repo = ImpactHistoryRepository(db)

    history, total = await repo.list_history(
        column_urn=column_urn,
        change_type=change_type,
        success=success,
        offset=offset,
        limit=limit,
    )

    return ImpactHistoryListResponse(
        history=[
            ImpactHistoryResponse(
                id=str(h.id),
                change_id=str(h.change_id),
                column_urn=h.column_urn,
                change_type=h.change_type,
                predicted_risk_level=h.predicted_risk_level,
                actual_risk_level=h.actual_risk_level,
                success=h.success,
                downtime_minutes=(
                    h.actual_downtime_seconds / 60 if h.actual_downtime_seconds else None
                ),
                changed_by=h.changed_by,
                change_timestamp=h.change_timestamp.isoformat(),
            )
            for h in history
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Endpoints - Impact Alerts
# ---------------------------------------------------------------------------


@router.get("/alerts", response_model=ImpactAlertListResponse)
async def list_impact_alerts(
    db: DbSession,
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    severity: Optional[str] = Query(None, description="Filter by severity (critical, high, medium, low)"),
    column_urn: Optional[str] = Query(None, description="Filter by column URN"),
    resolved: Optional[bool] = Query(False, description="Filter by resolved status"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Results limit"),
) -> ImpactAlertListResponse:
    """
    List impact alerts for high-risk changes.

    Alerts are triggered for:
    - **high_risk_change**: Risk level is high or critical
    - **production_impact**: Affects production DAGs
    - **pii_change**: Affects PII columns
    - **breaking_change**: Causes breaking changes
    - **low_confidence**: Prediction confidence is low
    """
    repo = ImpactAlertRepository(db)

    alerts, total = await repo.list_alerts(
        alert_type=alert_type,
        severity=severity,
        column_urn=column_urn,
        resolved=resolved,
        offset=offset,
        limit=limit,
    )

    return ImpactAlertListResponse(
        alerts=[
            ImpactAlertResponse(
                id=str(a.id),
                alert_type=a.alert_type,
                severity=a.severity,
                column_urn=a.column_urn,
                change_type=a.change_type,
                alert_message=a.alert_message,
                recommendation=a.recommendation,
                acknowledged=a.acknowledged,
                resolved=a.resolved,
                created_at=a.created_at.isoformat(),
            )
            for a in alerts
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/alerts/summary", response_model=AlertSummaryResponse)
async def get_alerts_summary(db: DbSession) -> AlertSummaryResponse:
    """
    Get summary statistics for impact alerts.

    Returns counts of:
    - Total alerts
    - Unresolved alerts
    - Critical unresolved alerts
    - Resolved alerts
    """
    repo = ImpactAlertRepository(db)
    summary = await repo.get_alert_summary()
    return AlertSummaryResponse(**summary)


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: UUID,
    db: DbSession,
    acknowledged_by: str = Query(..., description="User acknowledging the alert"),
) -> ImpactAlertResponse:
    """
    Acknowledge an impact alert.

    Marks the alert as seen and acknowledged by a user.
    Does not resolve the alert - use the resolve endpoint for that.
    """
    repo = ImpactAlertRepository(db)

    alert = await repo.acknowledge_alert(alert_id=alert_id, acknowledged_by=acknowledged_by)
    if not alert:
        raise NotFoundError(f"Alert not found: {alert_id}")

    await db.commit()

    return ImpactAlertResponse(
        id=str(alert.id),
        alert_type=alert.alert_type,
        severity=alert.severity,
        column_urn=alert.column_urn,
        change_type=alert.change_type,
        alert_message=alert.alert_message,
        recommendation=alert.recommendation,
        acknowledged=alert.acknowledged,
        resolved=alert.resolved,
        created_at=alert.created_at.isoformat(),
    )


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: UUID, db: DbSession) -> ImpactAlertResponse:
    """
    Mark an impact alert as resolved.

    Use this when the issue triggering the alert has been addressed.
    """
    repo = ImpactAlertRepository(db)

    alert = await repo.resolve_alert(alert_id=alert_id)
    if not alert:
        raise NotFoundError(f"Alert not found: {alert_id}")

    await db.commit()

    return ImpactAlertResponse(
        id=str(alert.id),
        alert_type=alert.alert_type,
        severity=alert.severity,
        column_urn=alert.column_urn,
        change_type=alert.change_type,
        alert_message=alert.alert_message,
        recommendation=alert.recommendation,
        acknowledged=alert.acknowledged,
        resolved=alert.resolved,
        created_at=alert.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints - Impact Simulation
# ---------------------------------------------------------------------------


@router.post("/simulate", response_model=SimulationResponse)
async def simulate_impact(
    request: SimulationRequest,
    db: DbSession,
) -> SimulationResponse:
    """
    Simulate impact of a schema change before applying it.

    This endpoint runs a "what-if" analysis that predicts the impact of a schema change
    without actually modifying any data. It provides:

    - **Task Impact**: Which Airflow tasks will be affected
    - **Temporal Impact**: When impacts will occur based on schedules
    - **Historical Insights**: Similar past changes and their outcomes
    - **Recommendations**: Actionable suggestions for minimizing risk
    - **Warnings**: Potential issues to watch for

    **Use Cases:**
    - Pre-deployment risk assessment
    - Comparing different change strategies
    - Finding optimal deployment windows
    - Learning from historical changes

    **Example Request:**
    ```json
    {
      "column_urn": "urn:dcs:column:users.email",
      "change_type": "rename",
      "change_params": {
        "new_name": "email_address",
        "create_alias": true
      },
      "scheduled_for": "2025-01-01T02:00:00Z",
      "include_temporal": true,
      "depth": 5
    }
    ```
    """
    simulator = ImpactSimulator(db)

    # Parse scheduled_for timestamp if provided
    parsed_timestamp = None
    if request.scheduled_for:
        try:
            parsed_timestamp = datetime.fromisoformat(
                request.scheduled_for.replace("Z", "+00:00")
            )
        except ValueError:
            raise ValidationError_(f"Invalid timestamp format: {request.scheduled_for}")

    # Run simulation
    result = await simulator.simulate_change(
        column_urn=request.column_urn,
        change_type=request.change_type,
        change_params=request.change_params,
        scheduled_for=parsed_timestamp,
        include_temporal=request.include_temporal,
        depth=request.depth,
    )

    return SimulationResponse(
        simulation_id=str(result.simulation_id),
        column_urn=result.column_urn,
        change_type=result.change_type,
        change_params=result.change_params,
        task_impact=result.task_impact,
        temporal_impact=result.temporal_impact,
        affected_columns_count=result.affected_columns_count,
        affected_tasks_count=result.affected_tasks_count,
        affected_dags_count=result.affected_dags_count,
        similar_changes_count=result.similar_changes_count,
        historical_success_rate=result.historical_success_rate,
        avg_historical_downtime=result.avg_historical_downtime,
        recommendations=result.recommendations,
        warnings=result.warnings,
        best_deployment_window=result.best_deployment_window,
        confidence_score=result.confidence_score,
        simulated_at=result.simulated_at.isoformat(),
        scheduled_for=result.scheduled_for.isoformat() if result.scheduled_for else None,
    )
