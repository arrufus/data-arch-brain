"""Task-level impact analysis service for Phase 8."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.models.capsule import Capsule
from src.models.column import Column
from src.models.lineage import ColumnLineage
from src.models.orchestration_edge import TaskDataEdge
from src.models.pipeline import Pipeline, PipelineTask
from src.repositories.capsule import CapsuleRepository
from src.repositories.column import ColumnRepository
from src.repositories.column_lineage import ColumnLineageRepository
from src.services.temporal_impact import TemporalImpact, TemporalImpactService


@dataclass
class TaskImpactResult:
    """Result of task-level impact analysis."""

    total_tasks: int
    total_dags: int
    critical_tasks: int
    risk_level: str
    confidence_score: float
    tasks: list[dict]
    dags: list[dict]
    affected_columns: list[dict]
    temporal_impact: Optional[dict] = None


class TaskImpactService:
    """Service for analyzing task-level impact of schema changes (Phase 8)."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.column_repo = ColumnRepository(session)
        self.capsule_repo = CapsuleRepository(session)
        self.lineage_repo = ColumnLineageRepository(session)
        self.temporal_service = TemporalImpactService()

    async def analyze_column_impact(
        self,
        column_urn: str,
        change_type: str,
        depth: int = 5,
        include_temporal: bool = False,
        change_timestamp: Optional[datetime] = None,
    ) -> TaskImpactResult:
        """Analyze task-level impact of a column change.

        Args:
            column_urn: URN of the column being changed
            change_type: Type of change (delete, rename, type_change, etc.)
            depth: Lineage depth to traverse

        Returns:
            TaskImpactResult with affected tasks and risk assessment
        """
        # 1. Get the source column
        column = await self._get_column_by_urn(column_urn)
        if not column:
            raise ValueError(f"Column not found: {column_urn}")

        # 2. Get affected columns via lineage
        affected_columns = await self._get_affected_columns(column, depth)

        # 3. Get capsules containing affected columns
        affected_capsule_ids = {col.capsule_id for col in affected_columns}

        # 4. Get tasks depending on affected capsules via TaskDataEdge
        affected_tasks = []
        for capsule_id in affected_capsule_ids:
            tasks = await self._get_tasks_by_capsule(capsule_id)
            affected_tasks.extend(tasks)

        # 5. Calculate task-level impact for each task
        task_impacts = []
        for task in affected_tasks:
            impact = await self._calculate_single_task_impact(
                task, change_type, column
            )
            task_impacts.append(impact)

        # 6. Group tasks by DAG
        dags = self._group_tasks_by_dag(task_impacts)

        # 7. Calculate overall risk
        risk_level, confidence = self._calculate_overall_risk(
            task_impacts, change_type, len(affected_columns)
        )

        # 8. Count critical tasks
        critical_count = sum(
            1 for t in task_impacts if t.get("risk_level") in ["high", "critical"]
        )

        # 9. Calculate temporal impact if requested
        temporal_impact_data = None
        if include_temporal:
            temporal_impact = self.temporal_service.calculate_temporal_impact(
                affected_tasks=task_impacts, change_timestamp=change_timestamp
            )
            temporal_impact_data = {
                "schedule_pattern": temporal_impact.schedule_pattern,
                "next_execution": (
                    temporal_impact.next_execution.isoformat()
                    if temporal_impact.next_execution
                    else None
                ),
                "executions_per_day": temporal_impact.executions_per_day,
                "executions_per_week": temporal_impact.executions_per_week,
                "peak_execution_hours": temporal_impact.peak_execution_hours,
                "low_impact_windows": [
                    {
                        "start": w.start.isoformat(),
                        "end": w.end.isoformat(),
                        "impact_score": w.impact_score,
                        "reason": w.reason,
                    }
                    for w in temporal_impact.low_impact_windows
                ],
                "high_impact_windows": [
                    {
                        "start": w.start.isoformat(),
                        "end": w.end.isoformat(),
                        "impact_score": w.impact_score,
                        "reason": w.reason,
                    }
                    for w in temporal_impact.high_impact_windows
                ],
                "estimated_downtime_minutes": temporal_impact.estimated_downtime_minutes,
                "affected_time_periods": temporal_impact.affected_time_periods,
            }

        return TaskImpactResult(
            total_tasks=len(task_impacts),
            total_dags=len(dags),
            critical_tasks=critical_count,
            risk_level=risk_level,
            confidence_score=confidence,
            tasks=task_impacts,
            dags=dags,
            affected_columns=[
                {
                    "column_urn": col.urn,
                    "capsule_urn": (
                        col.capsule.urn if col.capsule else None
                    ),
                    "data_type": col.data_type,
                }
                for col in affected_columns
            ],
            temporal_impact=temporal_impact_data,
        )

    async def _get_column_by_urn(self, urn: str) -> Optional[Column]:
        """Get column by URN with eager loading of capsule relationship."""
        stmt = (
            select(Column)
            .options(joinedload(Column.capsule))
            .where(Column.urn == urn)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_affected_columns(
        self, column: Column, depth: int
    ) -> list[Column]:
        """Get all columns affected by changes to the source column.

        This includes:
        1. The column itself
        2. All downstream columns via lineage
        """
        affected = [column]

        # Get downstream columns via lineage
        downstream_urns = await self.lineage_repo.get_downstream_columns(
            column.urn, depth=depth
        )

        # Fetch column objects
        for urn in downstream_urns:
            col = await self._get_column_by_urn(urn)
            if col:
                affected.append(col)

        return affected

    async def _get_tasks_by_capsule(self, capsule_id: UUID) -> list[dict]:
        """Get tasks that depend on a capsule via TaskDataEdge.

        Returns a list of task info dicts with attributes compatible with
        the TaskDependency interface.
        """
        # Query TaskDataEdge with joins to get full task and pipeline info
        stmt = (
            select(
                TaskDataEdge,
                PipelineTask,
                Pipeline
            )
            .join(PipelineTask, TaskDataEdge.task_id == PipelineTask.id)
            .join(Pipeline, PipelineTask.pipeline_id == Pipeline.id)
            .where(TaskDataEdge.capsule_id == capsule_id)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        # Convert to dict format compatible with TaskDependency
        tasks = []
        for edge, task, pipeline in rows:
            # Map edge_type to dependency_type
            dependency_type_map = {
                "consumes": "read",
                "produces": "write",
                "validates": "read",
                "transforms": "transform",
            }
            dependency_type = dependency_type_map.get(edge.edge_type, "read")

            # Extract metadata from task (if available)
            task_meta = task.meta or {}

            tasks.append({
                "dag_id": pipeline.name,
                "task_id": task.name,
                "dependency_type": dependency_type,
                "edge_type": edge.edge_type,
                "schedule_interval": pipeline.schedule_interval,
                "criticality_score": task_meta.get("criticality_score"),
                "success_rate": task_meta.get("success_rate"),
                "last_execution_time": None,  # Not tracked in current model
                "task_obj": task,  # Keep reference for temporal analysis
                "pipeline_obj": pipeline,  # Keep reference for temporal analysis
            })

        return tasks

    async def _calculate_single_task_impact(
        self, task: dict, change_type: str, source_column: Column
    ) -> dict:
        """Calculate impact for a single task.

        Impact factors:
        1. Dependency type (read, write, transform)
        2. Task criticality score
        3. Execution frequency
        4. Success rate
        5. Change severity
        """
        # Base risk score
        risk_score = 0.0

        # Factor 1: Dependency type (max +30)
        dependency_type = task.get("dependency_type", "read")
        if dependency_type == "read":
            risk_score += 30  # Reading deleted column = high risk
        elif dependency_type == "write":
            risk_score += 20  # Writing to changed column = medium risk
        elif dependency_type == "transform":
            risk_score += 25  # Transforming changed column = high risk

        # Factor 2: Change severity (max +30)
        change_severity = {
            "delete": 30,
            "rename": 20,
            "type_change": 25,
            "nullability": 15,
            "default": 10,
        }
        risk_score += change_severity.get(change_type, 15)

        # Factor 3: Task criticality (max +20)
        criticality_score = task.get("criticality_score")
        if criticality_score:
            risk_score += float(criticality_score) * 20

        # Factor 4: Success rate (inverse, max +10)
        success_rate = task.get("success_rate")
        if success_rate:
            # Low success rate = higher risk
            risk_score += (100 - float(success_rate)) / 10

        # Factor 5: Execution frequency (max +10)
        schedule_interval = task.get("schedule_interval")
        if schedule_interval:
            # More frequent = higher impact
            freq_score = self._calculate_frequency_score(schedule_interval)
            risk_score += freq_score

        # Normalize to 0-100
        risk_score = min(100, max(0, risk_score))

        # Determine risk level
        if risk_score >= 75:
            risk_level = "critical"
        elif risk_score >= 50:
            risk_level = "high"
        elif risk_score >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "dag_id": task.get("dag_id"),
            "task_id": task.get("task_id"),
            "dependency_type": dependency_type,
            "edge_type": task.get("edge_type"),
            "schedule_interval": schedule_interval,
            "criticality_score": (
                float(criticality_score) if criticality_score else None
            ),
            "success_rate": (
                float(success_rate) if success_rate else None
            ),
            "last_execution_time": task.get("last_execution_time"),
            "avg_execution_duration_seconds": task.get("avg_execution_duration_seconds"),
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "is_active": task.get("is_active", True),
        }

    def _calculate_frequency_score(self, schedule_interval: str) -> float:
        """Calculate frequency score from schedule interval.

        Higher frequency = higher score (more impact)
        """
        schedule_lower = schedule_interval.lower()

        # Presets
        if "@hourly" in schedule_lower or "0 * * * *" in schedule_lower:
            return 10.0
        elif "@daily" in schedule_lower or "0 0 * * *" in schedule_lower:
            return 8.0
        elif "@weekly" in schedule_lower or "0 0 * * 0" in schedule_lower:
            return 4.0
        elif "@monthly" in schedule_lower or "0 0 1 * *" in schedule_lower:
            return 2.0

        # Try to parse cron for frequency
        # Simplified: count asterisks (more = more frequent)
        asterisk_count = schedule_lower.count("*")
        return min(10.0, asterisk_count * 2)

    def _group_tasks_by_dag(self, task_impacts: list[dict]) -> list[dict]:
        """Group tasks by DAG and aggregate impact."""
        dag_dict = {}

        for task in task_impacts:
            dag_id = task["dag_id"]

            if dag_id not in dag_dict:
                dag_dict[dag_id] = {
                    "dag_id": dag_id,
                    "affected_task_count": 0,
                    "critical_task_count": 0,
                    "high_risk_task_count": 0,
                    "max_risk_score": 0.0,
                    "avg_risk_score": 0.0,
                    "tasks": [],
                }

            dag = dag_dict[dag_id]
            dag["affected_task_count"] += 1
            dag["tasks"].append(task)

            if task["risk_level"] == "critical":
                dag["critical_task_count"] += 1
            elif task["risk_level"] == "high":
                dag["high_risk_task_count"] += 1

            dag["max_risk_score"] = max(
                dag["max_risk_score"], task["risk_score"]
            )

        # Calculate averages
        for dag in dag_dict.values():
            if dag["affected_task_count"] > 0:
                dag["avg_risk_score"] = round(
                    sum(t["risk_score"] for t in dag["tasks"])
                    / dag["affected_task_count"],
                    2,
                )

        return list(dag_dict.values())

    def _calculate_overall_risk(
        self, task_impacts: list[dict], change_type: str, affected_columns_count: int
    ) -> tuple[str, float]:
        """Calculate overall risk level and confidence score.

        Returns:
            Tuple of (risk_level, confidence_score)
        """
        if not task_impacts:
            return "low", 0.9  # High confidence: no tasks affected

        # Calculate average and max risk scores
        avg_risk = sum(t["risk_score"] for t in task_impacts) / len(task_impacts)
        max_risk = max(t["risk_score"] for t in task_impacts)

        # Determine overall risk (weighted toward max risk)
        overall_risk_score = (avg_risk * 0.4) + (max_risk * 0.6)

        if overall_risk_score >= 70:
            risk_level = "critical"
        elif overall_risk_score >= 50:
            risk_level = "high"
        elif overall_risk_score >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Calculate confidence score
        confidence = self._calculate_confidence(
            task_impacts, affected_columns_count
        )

        return risk_level, confidence

    def _calculate_confidence(
        self, task_impacts: list[dict], affected_columns_count: int
    ) -> float:
        """Calculate confidence score based on data quality.

        Factors:
        1. Task metadata completeness
        2. Number of affected tasks
        3. Lineage completeness (affected columns count)
        """
        if not task_impacts:
            return 0.9  # High confidence when no tasks affected

        # Factor 1: Task metadata completeness (0-40 points)
        completeness_scores = []
        for task in task_impacts:
            score = 0
            if task["criticality_score"] is not None:
                score += 1
            if task["success_rate"] is not None:
                score += 1
            if task["last_execution_time"] is not None:
                score += 1
            if task["avg_execution_duration_seconds"] is not None:
                score += 1
            completeness_scores.append(score / 4)  # Normalize to 0-1

        avg_completeness = sum(completeness_scores) / len(completeness_scores)
        completeness_points = avg_completeness * 40

        # Factor 2: Sample size adequacy (0-30 points)
        if len(task_impacts) >= 10:
            sample_points = 30
        elif len(task_impacts) >= 5:
            sample_points = 20
        elif len(task_impacts) >= 1:
            sample_points = 10
        else:
            sample_points = 0

        # Factor 3: Lineage coverage (0-30 points)
        if affected_columns_count >= 10:
            lineage_points = 30
        elif affected_columns_count >= 5:
            lineage_points = 20
        elif affected_columns_count >= 1:
            lineage_points = 10
        else:
            lineage_points = 5

        # Total confidence (0-100, normalized to 0-1)
        total_points = completeness_points + sample_points + lineage_points
        confidence = total_points / 100

        return round(confidence, 2)

    async def get_task_dependencies_summary(
        self,
        capsule_id: Optional[UUID] = None,
        dag_id: Optional[str] = None,
    ) -> dict:
        """Get summary statistics for task dependencies.

        Args:
            capsule_id: Optional filter by capsule
            dag_id: Optional filter by DAG

        Returns:
            Dictionary with dependency statistics
        """
        # Get dependencies with filters
        deps, total = await self.task_dep_repo.list_dependencies(
            capsule_id=capsule_id,
            dag_id=dag_id,
            is_active=True,
            limit=1000,
        )

        # Count by type
        type_counts = await self.task_dep_repo.count_by_dependency_type(
            capsule_id=capsule_id
        )

        # Count critical tasks
        critical_tasks = 0
        if capsule_id:
            critical = await self.task_dep_repo.get_critical_tasks(
                capsule_id, min_criticality=0.7
            )
            critical_tasks = len(critical)

        # Get unique DAGs
        unique_dags = {dep.dag_id for dep in deps}

        return {
            "total_dependencies": total,
            "active_dependencies": len(deps),
            "unique_dags": len(unique_dags),
            "critical_tasks": critical_tasks,
            "dependencies_by_type": type_counts,
        }
