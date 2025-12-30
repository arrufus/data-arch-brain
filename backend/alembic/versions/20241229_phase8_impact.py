"""phase8_impact

Phase 8: Advanced Impact Analysis - Task-Level and Temporal Impact

Revision ID: 20241229_phase8_impact
Revises: 20241229_airflow_column_lineage
Create Date: 2024-12-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20241229_phase8_impact"
down_revision: Union[str, None] = "20241229_airflow_column_lineage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Phase 8 tables for advanced impact analysis."""

    # ===================================================================
    # 1. Task Dependencies Table (dcs schema)
    # ===================================================================
    op.create_table(
        "task_dependencies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # DAG and Task identification
        sa.Column("dag_id", sa.String(255), nullable=False, comment="Airflow DAG ID"),
        sa.Column("task_id", sa.String(255), nullable=False, comment="Airflow Task ID"),
        # Capsule reference
        sa.Column(
            "capsule_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Referenced capsule (table/model)",
        ),
        # Dependency metadata
        sa.Column(
            "dependency_type",
            sa.String(50),
            nullable=False,
            comment="read, write, transform",
        ),
        sa.Column(
            "schedule_interval",
            sa.String(100),
            nullable=True,
            comment="Cron expression or preset",
        ),
        # Task status
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
            comment="Is task currently active",
        ),
        # Execution metrics
        sa.Column(
            "last_execution_time",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last successful execution timestamp",
        ),
        sa.Column(
            "avg_execution_duration_seconds",
            sa.Integer,
            nullable=True,
            comment="Average execution duration in seconds",
        ),
        sa.Column(
            "success_rate",
            sa.Numeric(5, 2),
            nullable=True,
            comment="Success rate percentage (0.00-100.00)",
        ),
        # Impact scoring
        sa.Column(
            "criticality_score",
            sa.Numeric(3, 2),
            nullable=True,
            comment="Criticality score (0.00-1.00)",
        ),
        # Additional metadata
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Additional task metadata",
        ),
        # Audit
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        # Constraints
        sa.ForeignKeyConstraint(
            ["capsule_id"], ["dcs.capsules.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "dag_id", "task_id", "capsule_id", name="uq_task_deps_dag_task_capsule"
        ),
        schema="dcs",
    )

    # Indexes for task_dependencies
    op.create_index(
        "idx_task_deps_capsule",
        "task_dependencies",
        ["capsule_id"],
        schema="dcs",
    )
    op.create_index(
        "idx_task_deps_dag",
        "task_dependencies",
        ["dag_id"],
        schema="dcs",
    )
    op.create_index(
        "idx_task_deps_task",
        "task_dependencies",
        ["task_id"],
        schema="dcs",
    )
    op.create_index(
        "idx_task_deps_active",
        "task_dependencies",
        ["is_active"],
        schema="dcs",
        postgresql_where=sa.text("is_active = true"),
    )
    op.create_index(
        "idx_task_deps_dependency_type",
        "task_dependencies",
        ["dependency_type"],
        schema="dcs",
    )

    # ===================================================================
    # 2. Impact History Table (dcs schema)
    # ===================================================================
    op.create_table(
        "impact_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Change identification
        sa.Column(
            "change_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
            comment="Unique identifier for the schema change",
        ),
        sa.Column(
            "column_urn",
            sa.String(500),
            nullable=False,
            comment="URN of the changed column",
        ),
        sa.Column(
            "change_type",
            sa.String(50),
            nullable=False,
            comment="delete, rename, type_change, nullability, etc.",
        ),
        sa.Column(
            "change_params",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Parameters of the change",
        ),
        # Predicted impact (from simulation)
        sa.Column(
            "predicted_risk_level",
            sa.String(20),
            nullable=True,
            comment="low, medium, high, critical",
        ),
        sa.Column(
            "predicted_affected_columns",
            sa.Integer,
            nullable=True,
            comment="Predicted number of affected columns",
        ),
        sa.Column(
            "predicted_affected_tasks",
            sa.Integer,
            nullable=True,
            comment="Predicted number of affected tasks",
        ),
        sa.Column(
            "predicted_downtime_seconds",
            sa.Integer,
            nullable=True,
            comment="Predicted downtime in seconds",
        ),
        # Actual impact (observed)
        sa.Column(
            "actual_risk_level",
            sa.String(20),
            nullable=True,
            comment="low, medium, high, critical",
        ),
        sa.Column(
            "actual_affected_columns",
            sa.Integer,
            nullable=True,
            comment="Actual number of affected columns",
        ),
        sa.Column(
            "actual_affected_tasks",
            sa.Integer,
            nullable=True,
            comment="Actual number of affected tasks",
        ),
        sa.Column(
            "actual_downtime_seconds",
            sa.Integer,
            nullable=True,
            comment="Actual downtime in seconds",
        ),
        sa.Column(
            "actual_failures",
            sa.Integer,
            nullable=True,
            comment="Number of task failures caused",
        ),
        # Outcome
        sa.Column(
            "success",
            sa.Boolean,
            nullable=True,
            comment="Was the change successful",
        ),
        sa.Column(
            "rollback_performed",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
            comment="Was a rollback performed",
        ),
        sa.Column(
            "issues_encountered",
            postgresql.ARRAY(sa.Text),
            nullable=True,
            comment="List of issues encountered",
        ),
        sa.Column(
            "resolution_notes",
            sa.Text,
            nullable=True,
            comment="Notes on how issues were resolved",
        ),
        # Metadata
        sa.Column(
            "changed_by",
            sa.String(255),
            nullable=True,
            comment="User who made the change",
        ),
        sa.Column(
            "change_timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When the change was applied",
        ),
        sa.Column(
            "completed_timestamp",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the change was completed",
        ),
        # Audit
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Constraint
        sa.CheckConstraint(
            "change_timestamp <= completed_timestamp",
            name="ck_impact_history_timestamps",
        ),
        schema="dcs",
    )

    # Indexes for impact_history
    op.create_index(
        "idx_impact_history_column",
        "impact_history",
        ["column_urn"],
        schema="dcs",
    )
    op.create_index(
        "idx_impact_history_type",
        "impact_history",
        ["change_type"],
        schema="dcs",
    )
    op.create_index(
        "idx_impact_history_timestamp",
        "impact_history",
        ["change_timestamp"],
        schema="dcs",
        postgresql_using="btree",
        postgresql_ops={"change_timestamp": "DESC"},
    )
    op.create_index(
        "idx_impact_history_success",
        "impact_history",
        ["success"],
        schema="dcs",
    )
    op.create_index(
        "idx_impact_history_risk",
        "impact_history",
        ["predicted_risk_level", "actual_risk_level"],
        schema="dcs",
    )

    # ===================================================================
    # 3. Impact Alerts Table (dcs schema)
    # ===================================================================
    op.create_table(
        "impact_alerts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Alert classification
        sa.Column(
            "alert_type",
            sa.String(50),
            nullable=False,
            comment="high_risk_change, production_impact, pii_change, breaking_change, low_confidence",
        ),
        sa.Column(
            "severity",
            sa.String(20),
            nullable=False,
            comment="critical, high, medium, low",
        ),
        # Related change
        sa.Column(
            "column_urn",
            sa.String(500),
            nullable=False,
            comment="URN of the affected column",
        ),
        sa.Column(
            "change_type",
            sa.String(50),
            nullable=False,
            comment="Type of change triggering the alert",
        ),
        # Alert details
        sa.Column(
            "trigger_condition",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Conditions that triggered the alert",
        ),
        sa.Column(
            "alert_message",
            sa.Text,
            nullable=False,
            comment="Human-readable alert message",
        ),
        sa.Column(
            "recommendation",
            sa.Text,
            nullable=True,
            comment="Recommended action to take",
        ),
        # Recipients
        sa.Column(
            "notified_users",
            postgresql.ARRAY(sa.Text),
            nullable=True,
            comment="List of users notified",
        ),
        sa.Column(
            "notified_teams",
            postgresql.ARRAY(sa.Text),
            nullable=True,
            comment="List of teams notified",
        ),
        sa.Column(
            "notified_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When notifications were sent",
        ),
        # Status
        sa.Column(
            "acknowledged",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
            comment="Has alert been acknowledged",
        ),
        sa.Column(
            "acknowledged_by",
            sa.String(255),
            nullable=True,
            comment="User who acknowledged the alert",
        ),
        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When alert was acknowledged",
        ),
        sa.Column(
            "resolved",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
            comment="Has alert been resolved",
        ),
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When alert was resolved",
        ),
        # Audit
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="dcs",
    )

    # Indexes for impact_alerts
    op.create_index(
        "idx_alerts_column",
        "impact_alerts",
        ["column_urn"],
        schema="dcs",
    )
    op.create_index(
        "idx_alerts_severity",
        "impact_alerts",
        ["severity"],
        schema="dcs",
    )
    op.create_index(
        "idx_alerts_type",
        "impact_alerts",
        ["alert_type"],
        schema="dcs",
    )
    op.create_index(
        "idx_alerts_unresolved",
        "impact_alerts",
        ["resolved"],
        schema="dcs",
        postgresql_where=sa.text("resolved = false"),
    )
    op.create_index(
        "idx_alerts_created",
        "impact_alerts",
        ["created_at"],
        schema="dcs",
        postgresql_using="btree",
        postgresql_ops={"created_at": "DESC"},
    )


def downgrade() -> None:
    """Revert Phase 8 advanced impact analysis tables."""

    # Drop tables in reverse order
    op.drop_table("impact_alerts", schema="dcs")
    op.drop_table("impact_history", schema="dcs")
    op.drop_table("task_dependencies", schema="dcs")
