"""Impact Simulation Service (Phase 8)

Allows users to simulate schema changes before applying them.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.impact_history import ImpactHistoryRepository
from src.services.task_impact import TaskImpactService
from src.services.temporal_impact import TemporalImpactService


@dataclass
class SimulationResult:
    """Result of impact simulation."""

    simulation_id: UUID
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
    simulated_at: datetime
    scheduled_for: Optional[datetime]


class ImpactSimulator:
    """Simulate schema changes and predict outcomes."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.task_impact_service = TaskImpactService(session)
        self.temporal_service = TemporalImpactService()
        self.history_repo = ImpactHistoryRepository(session)

    async def simulate_change(
        self,
        column_urn: str,
        change_type: str,
        change_params: dict[str, Any],
        scheduled_for: Optional[datetime] = None,
        include_temporal: bool = True,
        depth: int = 5,
    ) -> SimulationResult:
        """Run a what-if simulation for a schema change.

        Args:
            column_urn: URN of the column to change
            change_type: Type of change (delete, rename, type_change, etc.)
            change_params: Parameters for the change
            scheduled_for: When the change will occur (default: now)
            include_temporal: Include temporal impact analysis
            depth: Lineage depth to traverse

        Returns:
            SimulationResult with predicted impacts and recommendations
        """
        simulation_timestamp = scheduled_for or datetime.now(timezone.utc)

        # 1. Calculate task impact (virtual - no database changes)
        task_impact_result = await self.task_impact_service.analyze_column_impact(
            column_urn=column_urn,
            change_type=change_type,
            depth=depth,
            include_temporal=include_temporal,
            change_timestamp=simulation_timestamp,
        )

        # 2. Extract impact data
        task_impact = {
            "total_tasks": task_impact_result.total_tasks,
            "total_dags": task_impact_result.total_dags,
            "critical_tasks": task_impact_result.critical_tasks,
            "risk_level": task_impact_result.risk_level,
            "confidence_score": task_impact_result.confidence_score,
            "tasks": task_impact_result.tasks,
            "dags": task_impact_result.dags,
        }

        temporal_impact = task_impact_result.temporal_impact

        # 3. Find similar historical changes
        similar_changes = await self.history_repo.get_similar_changes(
            column_urn=column_urn, change_type=change_type, success_only=False, limit=10
        )

        # 4. Calculate historical metrics
        historical_success_rate = await self._calculate_success_rate(
            similar_changes, change_type
        )
        avg_downtime = await self._calculate_avg_downtime(similar_changes)

        # 5. Generate recommendations
        recommendations = self._generate_recommendations(
            task_impact=task_impact,
            temporal_impact=temporal_impact,
            change_type=change_type,
            change_params=change_params,
            historical_success_rate=historical_success_rate,
        )

        # 6. Generate warnings
        warnings = self._generate_warnings(
            task_impact=task_impact,
            change_type=change_type,
            historical_success_rate=historical_success_rate,
        )

        # 7. Find best deployment window
        best_window = self._find_best_deployment_window(temporal_impact)

        # 8. Calculate overall confidence
        confidence = self._calculate_confidence(
            task_confidence=task_impact_result.confidence_score,
            historical_matches=len(similar_changes),
            temporal_available=temporal_impact is not None,
        )

        return SimulationResult(
            simulation_id=uuid4(),
            column_urn=column_urn,
            change_type=change_type,
            change_params=change_params,
            task_impact=task_impact,
            temporal_impact=temporal_impact,
            affected_columns_count=len(task_impact_result.affected_columns),
            affected_tasks_count=task_impact_result.total_tasks,
            affected_dags_count=task_impact_result.total_dags,
            similar_changes_count=len(similar_changes),
            historical_success_rate=historical_success_rate,
            avg_historical_downtime=avg_downtime,
            recommendations=recommendations,
            warnings=warnings,
            best_deployment_window=best_window,
            confidence_score=confidence,
            simulated_at=datetime.now(timezone.utc),
            scheduled_for=scheduled_for,
        )

    async def _calculate_success_rate(
        self, similar_changes: list, change_type: str
    ) -> float:
        """Calculate success rate from historical changes."""
        if not similar_changes:
            # No history, return estimate based on change type severity
            severity_map = {
                "delete": 0.6,
                "type_change": 0.7,
                "rename": 0.75,
                "nullability": 0.85,
                "default": 0.95,
            }
            return severity_map.get(change_type, 0.8)

        successes = sum(1 for c in similar_changes if c.success)
        return successes / len(similar_changes)

    async def _calculate_avg_downtime(self, similar_changes: list) -> float:
        """Calculate average downtime from historical changes."""
        if not similar_changes:
            return 0.0

        downtimes = [
            c.downtime_minutes for c in similar_changes if c.downtime_minutes is not None
        ]
        if not downtimes:
            return 0.0

        return sum(downtimes) / len(downtimes)

    def _generate_recommendations(
        self,
        task_impact: dict,
        temporal_impact: Optional[dict],
        change_type: str,
        change_params: dict,
        historical_success_rate: float,
    ) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []

        risk_level = task_impact["risk_level"]
        critical_tasks = task_impact["critical_tasks"]

        # Risk-based recommendations
        if risk_level in ["critical", "high"]:
            recommendations.append(
                "⚠️ High-risk change detected. Test thoroughly in staging environment first."
            )

            if critical_tasks > 0:
                recommendations.append(
                    f"🚨 {critical_tasks} critical tasks will be affected. Plan rollback procedure."
                )

            if change_type == "delete":
                recommendations.append(
                    "💡 Consider deprecating the column first before deletion (add migration period)."
                )

            if change_type == "rename" and not change_params.get("create_alias", False):
                recommendations.append(
                    "💡 Create a column alias to maintain backward compatibility during transition."
                )

        # Temporal recommendations
        if temporal_impact:
            low_impact_windows = temporal_impact.get("low_impact_windows", [])
            if low_impact_windows:
                best_window = low_impact_windows[0]
                recommendations.append(
                    f"⏰ Best deployment window: {best_window['start']} - {best_window['end']} "
                    f"({best_window['reason']})"
                )

            exec_per_day = temporal_impact.get("executions_per_day", 0)
            if exec_per_day > 10:
                recommendations.append(
                    f"⚡ High execution frequency ({exec_per_day:.1f}/day). "
                    "Monitor closely during deployment."
                )

        # Historical recommendations
        if historical_success_rate < 0.8:
            recommendations.append(
                f"📊 Historical success rate is {historical_success_rate:.0%}. "
                "Review past failures before proceeding."
            )

        # General best practices
        if task_impact["total_tasks"] > 5:
            recommendations.append(
                "📝 Document the change and notify all affected teams before deployment."
            )

        if not recommendations:
            recommendations.append("✅ Low-risk change. Safe to proceed with standard deployment.")

        return recommendations

    def _generate_warnings(
        self, task_impact: dict, change_type: str, historical_success_rate: float
    ) -> list[str]:
        """Generate warnings for potential issues."""
        warnings = []

        if task_impact["confidence_score"] < 0.7:
            warnings.append(
                "⚠️ Low confidence score - predictions may be inaccurate due to incomplete metadata."
            )

        if change_type == "type_change":
            warnings.append(
                "⚠️ Type changes may cause data loss or conversion errors. Validate all data first."
            )

        if historical_success_rate < 0.5:
            warnings.append(
                "🚨 More than 50% of similar changes failed historically. Proceed with extreme caution."
            )

        if task_impact["total_dags"] > 10:
            warnings.append(
                "⚠️ Large blast radius - change affects more than 10 DAGs. "
                "Consider phased rollout."
            )

        return warnings

    def _find_best_deployment_window(
        self, temporal_impact: Optional[dict]
    ) -> Optional[dict[str, Any]]:
        """Find the best time window for deployment."""
        if not temporal_impact:
            return None

        low_impact_windows = temporal_impact.get("low_impact_windows", [])
        if not low_impact_windows:
            return None

        # Return the first (best) low-impact window
        best = low_impact_windows[0]
        return {
            "start": best["start"],
            "end": best["end"],
            "impact_score": best["impact_score"],
            "reason": best["reason"],
        }

    def _calculate_confidence(
        self,
        task_confidence: float,
        historical_matches: int,
        temporal_available: bool,
    ) -> float:
        """Calculate overall simulation confidence score.

        Factors:
        1. Task impact confidence (50%)
        2. Historical match count (30%)
        3. Temporal analysis availability (20%)
        """
        # Base confidence from task analysis
        confidence = task_confidence * 0.5

        # Historical matches boost (0-0.3)
        if historical_matches >= 10:
            confidence += 0.3
        elif historical_matches >= 5:
            confidence += 0.2
        elif historical_matches >= 2:
            confidence += 0.1

        # Temporal analysis boost (0-0.2)
        if temporal_available:
            confidence += 0.2

        return min(confidence, 1.0)
