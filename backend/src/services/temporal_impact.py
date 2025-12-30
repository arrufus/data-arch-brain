"""Temporal Impact Analysis Service (Phase 8)

Analyzes when schema changes will impact tasks based on execution schedules.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from croniter import croniter


@dataclass
class TimeWindow:
    """Time window for impact assessment."""

    start: datetime
    end: datetime
    impact_score: float  # 0.0 (no impact) to 1.0 (critical)
    reason: str
    affected_tasks: list[str]


@dataclass
class TemporalImpact:
    """Temporal impact analysis result."""

    schedule_pattern: str  # Description of schedule patterns
    next_execution: Optional[datetime]
    executions_per_day: float
    executions_per_week: float
    peak_execution_hours: list[int]  # Hours of day (0-23)
    low_impact_windows: list[TimeWindow]
    high_impact_windows: list[TimeWindow]
    estimated_downtime_minutes: float
    affected_time_periods: dict[str, int]  # Time period -> task count


class TemporalImpactService:
    """Service for temporal impact analysis."""

    def calculate_temporal_impact(
        self,
        affected_tasks: list[dict],
        change_timestamp: Optional[datetime] = None,
    ) -> TemporalImpact:
        """Calculate temporal impact for affected tasks.

        Args:
            affected_tasks: List of task dictionaries with schedule_interval
            change_timestamp: When the change will occur (default: now)

        Returns:
            TemporalImpact with schedule-based predictions
        """
        if change_timestamp is None:
            change_timestamp = datetime.now(timezone.utc)

        # Parse schedules
        schedules = self._parse_schedules(affected_tasks, change_timestamp)

        # Calculate execution frequency
        freq_per_day = sum(s["freq_per_day"] for s in schedules)
        freq_per_week = freq_per_day * 7

        # Find next execution times
        next_execs = [s["next_run"] for s in schedules if s["next_run"]]
        next_execution = min(next_execs) if next_execs else None

        # Identify peak hours
        peak_hours = self._identify_peak_hours(schedules)

        # Find low/high impact windows
        low_impact = self._find_low_impact_windows(schedules, change_timestamp)
        high_impact = self._find_high_impact_windows(schedules, change_timestamp)

        # Estimate downtime
        downtime_minutes = self._estimate_downtime(affected_tasks, schedules)

        # Group by time period
        affected_periods = self._group_by_time_period(schedules)

        # Describe schedule pattern
        pattern_desc = self._describe_pattern(schedules)

        return TemporalImpact(
            schedule_pattern=pattern_desc,
            next_execution=next_execution,
            executions_per_day=freq_per_day,
            executions_per_week=freq_per_week,
            peak_execution_hours=peak_hours,
            low_impact_windows=low_impact,
            high_impact_windows=high_impact,
            estimated_downtime_minutes=downtime_minutes,
            affected_time_periods=affected_periods,
        )

    def _parse_schedules(
        self, affected_tasks: list[dict], base_time: datetime
    ) -> list[dict]:
        """Parse cron schedules and calculate frequencies."""
        schedules = []

        for task in affected_tasks:
            schedule_interval = task.get("schedule_interval")
            if not schedule_interval:
                continue

            # Handle special Airflow presets
            cron_expr = self._normalize_schedule(schedule_interval)
            if not cron_expr:
                continue

            try:
                # Parse cron expression
                cron = croniter(cron_expr, base_time)

                # Calculate frequency (executions per day)
                freq_per_day = self._calculate_frequency(cron_expr)

                # Get next run time
                next_run = cron.get_next(datetime)

                # Get execution hours (for peak identification)
                exec_hours = self._get_execution_hours(cron_expr)

                schedules.append(
                    {
                        "task_id": f"{task.get('dag_id')}.{task.get('task_id')}",
                        "cron": cron_expr,
                        "freq_per_day": freq_per_day,
                        "next_run": next_run,
                        "exec_hours": exec_hours,
                        "risk_score": task.get("risk_score", 0),
                    }
                )
            except (ValueError, KeyError):
                # Invalid cron expression, skip
                continue

        return schedules

    def _normalize_schedule(self, schedule_interval: str) -> Optional[str]:
        """Convert Airflow presets to cron expressions."""
        presets = {
            "@once": None,  # One-time execution, no cron
            "@hourly": "0 * * * *",
            "@daily": "0 0 * * *",
            "@weekly": "0 0 * * 0",
            "@monthly": "0 0 1 * *",
            "@yearly": "0 0 1 1 *",
            "None": None,
        }

        # Check if it's a preset
        if schedule_interval in presets:
            return presets[schedule_interval]

        # Assume it's already a cron expression
        return schedule_interval

    def _calculate_frequency(self, cron_expr: str) -> float:
        """Calculate executions per day for a cron expression."""
        # Simple heuristic based on cron fields
        parts = cron_expr.split()
        if len(parts) != 5:
            return 1.0  # Default to daily

        minute, hour, day, month, dow = parts

        # Count possible executions
        if minute == "*" and hour == "*":
            # Every minute
            return 1440.0
        if hour == "*":
            # Every hour
            return 24.0
        if minute != "*" and hour != "*":
            # Specific times
            minute_count = len(minute.split(",")) if "," in minute else 1
            hour_count = len(hour.split(",")) if "," in hour else 1
            return float(minute_count * hour_count)

        # Default to daily
        return 1.0

    def _get_execution_hours(self, cron_expr: str) -> list[int]:
        """Extract hours when task executes."""
        parts = cron_expr.split()
        if len(parts) != 5:
            return []

        hour_field = parts[1]

        if hour_field == "*":
            # Every hour
            return list(range(24))

        if "," in hour_field:
            # Specific hours
            return [int(h) for h in hour_field.split(",") if h.isdigit()]

        if hour_field.isdigit():
            # Single hour
            return [int(hour_field)]

        if "/" in hour_field:
            # Step values (e.g., */6 = every 6 hours)
            step = int(hour_field.split("/")[1])
            return list(range(0, 24, step))

        return []

    def _identify_peak_hours(self, schedules: list[dict]) -> list[int]:
        """Identify hours with most task executions."""
        hour_counts = defaultdict(int)

        for sched in schedules:
            for hour in sched["exec_hours"]:
                hour_counts[hour] += 1

        # Find hours with above-average execution counts
        if not hour_counts:
            return []

        avg_count = sum(hour_counts.values()) / len(hour_counts)
        peak_hours = [h for h, count in hour_counts.items() if count >= avg_count]

        return sorted(peak_hours)

    def _find_low_impact_windows(
        self, schedules: list[dict], base_time: datetime, min_gap_hours: int = 4
    ) -> list[TimeWindow]:
        """Find time windows with minimal task execution."""
        # Build 24-hour execution timeline
        timeline = self._build_execution_timeline(schedules, base_time)

        # Find gaps in execution
        windows = []
        start = None

        for hour in range(24):
            task_count = timeline.get(hour, 0)

            if task_count == 0:
                if start is None:
                    start = hour
            else:
                if start is not None:
                    # Gap found
                    duration = hour - start
                    if duration >= min_gap_hours:
                        window_start = base_time.replace(
                            hour=start, minute=0, second=0, microsecond=0
                        )
                        window_end = window_start + timedelta(hours=duration)
                        windows.append(
                            TimeWindow(
                                start=window_start,
                                end=window_end,
                                impact_score=0.1,
                                reason=f"No scheduled executions for {duration} hours",
                                affected_tasks=[],
                            )
                        )
                    start = None

        # Check for gap at end of day
        if start is not None:
            duration = 24 - start
            if duration >= min_gap_hours:
                window_start = base_time.replace(
                    hour=start, minute=0, second=0, microsecond=0
                )
                window_end = window_start + timedelta(hours=duration)
                windows.append(
                    TimeWindow(
                        start=window_start,
                        end=window_end,
                        impact_score=0.1,
                        reason=f"No scheduled executions for {duration} hours",
                        affected_tasks=[],
                    )
                )

        return windows[:3]  # Return top 3 low-impact windows

    def _find_high_impact_windows(
        self, schedules: list[dict], base_time: datetime
    ) -> list[TimeWindow]:
        """Find time windows with maximum task execution."""
        # Build execution timeline
        timeline = self._build_execution_timeline(schedules, base_time)

        # Find peak periods
        if not timeline:
            return []

        max_count = max(timeline.values())
        peak_hours = [h for h, count in timeline.items() if count >= max_count * 0.8]

        # Group consecutive peak hours
        windows = []
        start = None

        for hour in sorted(peak_hours):
            if start is None:
                start = hour
            elif hour != peak_hours[peak_hours.index(hour) - 1] + 1:
                # Gap in peak hours, create window
                window_start = base_time.replace(
                    hour=start, minute=0, second=0, microsecond=0
                )
                window_end = base_time.replace(
                    hour=peak_hours[peak_hours.index(hour) - 1] + 1,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
                windows.append(
                    TimeWindow(
                        start=window_start,
                        end=window_end,
                        impact_score=0.9,
                        reason=f"Peak execution period ({max_count} tasks)",
                        affected_tasks=[],
                    )
                )
                start = hour

        # Add final window
        if start is not None:
            window_start = base_time.replace(
                hour=start, minute=0, second=0, microsecond=0
            )
            window_end = base_time.replace(
                hour=peak_hours[-1] + 1, minute=0, second=0, microsecond=0
            )
            windows.append(
                TimeWindow(
                    start=window_start,
                    end=window_end,
                    impact_score=0.9,
                    reason=f"Peak execution period ({max_count} tasks)",
                    affected_tasks=[],
                )
            )

        return windows[:3]  # Return top 3 high-impact windows

    def _build_execution_timeline(
        self, schedules: list[dict], base_time: datetime
    ) -> dict[int, int]:
        """Build 24-hour timeline of task executions."""
        timeline = defaultdict(int)

        for sched in schedules:
            for hour in sched["exec_hours"]:
                timeline[hour] += 1

        return dict(timeline)

    def _estimate_downtime(
        self, affected_tasks: list[dict], schedules: list[dict]
    ) -> float:
        """Estimate total downtime in minutes."""
        # Use average execution duration from task metadata
        total_downtime = 0.0

        for task in affected_tasks:
            avg_duration = task.get("avg_execution_duration_seconds") or 300  # 5 min default
            risk_score = task.get("risk_score") or 50

            # Higher risk = longer potential downtime
            downtime_multiplier = 1.0 + (risk_score / 100)
            estimated_downtime = (avg_duration / 60) * downtime_multiplier

            total_downtime += estimated_downtime

        return round(total_downtime, 2)

    def _group_by_time_period(self, schedules: list[dict]) -> dict[str, int]:
        """Group tasks by time period (morning, afternoon, evening, night)."""
        periods = defaultdict(int)

        for sched in schedules:
            for hour in sched["exec_hours"]:
                if 6 <= hour < 12:
                    periods["morning"] += 1
                elif 12 <= hour < 18:
                    periods["afternoon"] += 1
                elif 18 <= hour < 22:
                    periods["evening"] += 1
                else:
                    periods["night"] += 1

        return dict(periods)

    def _describe_pattern(self, schedules: list[dict]) -> str:
        """Generate human-readable description of schedule patterns."""
        if not schedules:
            return "No scheduled tasks"

        total_freq = sum(s["freq_per_day"] for s in schedules)

        if total_freq >= 24:
            return "High frequency (hourly or more)"
        if total_freq >= 7:
            return "Moderate frequency (multiple times daily)"
        if total_freq >= 1:
            return "Daily execution"
        if total_freq >= 0.5:
            return "Every 2-3 days"

        return "Weekly or less frequent"
