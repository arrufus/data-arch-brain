"""Integrated lineage service combining data and orchestration lineage."""

from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.capsule import Capsule
from src.models.lineage import CapsuleLineage
from src.models.orchestration_edge import TaskDataEdge
from src.models.pipeline import Pipeline, PipelineTask
from src.repositories.capsule import CapsuleRepository
from src.repositories.pipeline import PipelineRepository, TaskDataEdgeRepository


class LineageService:
    """Service for integrated lineage queries combining data and orchestration."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.capsule_repo = CapsuleRepository(session)
        self.pipeline_repo = PipelineRepository(session)
        self.edge_repo = TaskDataEdgeRepository(session)

    async def get_integrated_lineage(
        self,
        urn: str,
        direction: Literal["upstream", "downstream", "both"] = "both",
        depth: int = 3,
        include_orchestration: bool = True,
    ) -> dict:
        """Get integrated lineage combining data and orchestration edges.

        Args:
            urn: URN of capsule or task to start from
            direction: Direction to traverse (upstream, downstream, both)
            depth: How many hops to traverse
            include_orchestration: Include pipeline tasks in lineage graph

        Returns:
            Dictionary with nodes (capsules + tasks) and edges (data + orchestration)
        """
        # Determine if URN is a capsule or task
        is_task = ":task:" in urn
        is_capsule = not is_task

        nodes = []
        edges = []

        if is_capsule:
            # Start from capsule
            capsule = await self.capsule_repo.get_by_urn(urn)
            if not capsule:
                raise ValueError(f"Capsule not found: {urn}")

            # Add root capsule
            nodes.append(
                {
                    "id": str(capsule.id),
                    "urn": capsule.urn,
                    "name": capsule.name,
                    "type": "capsule",
                    "capsule_type": capsule.capsule_type,
                    "layer": capsule.layer,
                    "depth": 0,
                    "is_root": True,
                }
            )

            # Get data lineage (capsule-to-capsule)
            if direction in ["upstream", "both"]:
                upstream_capsules = await self.capsule_repo.get_upstream(
                    capsule.id, depth=depth
                )
                for uc in upstream_capsules:
                    nodes.append(
                        {
                            "id": str(uc.id),
                            "urn": uc.urn,
                            "name": uc.name,
                            "type": "capsule",
                            "capsule_type": uc.capsule_type,
                            "layer": uc.layer,
                            "depth": 1,  # Simplified depth
                            "direction": "upstream",
                        }
                    )

            if direction in ["downstream", "both"]:
                downstream_capsules = await self.capsule_repo.get_downstream(
                    capsule.id, depth=depth
                )
                for dc in downstream_capsules:
                    nodes.append(
                        {
                            "id": str(dc.id),
                            "urn": dc.urn,
                            "name": dc.name,
                            "type": "capsule",
                            "capsule_type": dc.capsule_type,
                            "layer": dc.layer,
                            "depth": 1,  # Simplified depth
                            "direction": "downstream",
                        }
                    )

            # Get data lineage edges
            result = await self.session.execute(
                select(CapsuleLineage).where(
                    (CapsuleLineage.source_id == capsule.id)
                    | (CapsuleLineage.target_id == capsule.id)
                )
            )
            lineage_edges = result.scalars().all()

            for edge in lineage_edges:
                edges.append(
                    {
                        "source_urn": edge.source_urn,
                        "target_urn": edge.target_urn,
                        "edge_type": edge.edge_type,
                        "edge_category": "data_lineage",
                        "transformation": edge.transformation,
                    }
                )

            # Get orchestration lineage (task-data edges)
            if include_orchestration:
                # Get tasks that produce this capsule
                producers = await self.edge_repo.get_producers(urn)
                for producer in producers:
                    # Add task node
                    nodes.append(
                        {
                            "id": producer["task_urn"],
                            "urn": producer["task_urn"],
                            "name": producer["task_name"],
                            "type": "task",
                            "task_type": producer["task_type"],
                            "pipeline_name": producer["pipeline_name"],
                            "depth": 1,
                            "direction": "upstream",
                        }
                    )

                    # Add produces edge (task -> capsule)
                    edges.append(
                        {
                            "source_urn": producer["task_urn"],
                            "target_urn": urn,
                            "edge_type": "produces",
                            "edge_category": "orchestration",
                            "operation": producer.get("operation"),
                        }
                    )

                # Get tasks that consume this capsule
                consumers = await self.edge_repo.get_consumers(urn)
                for consumer in consumers:
                    # Add task node
                    nodes.append(
                        {
                            "id": consumer["task_urn"],
                            "urn": consumer["task_urn"],
                            "name": consumer["task_name"],
                            "type": "task",
                            "task_type": consumer["task_type"],
                            "pipeline_name": consumer["pipeline_name"],
                            "depth": 1,
                            "direction": "downstream",
                        }
                    )

                    # Add consumes edge (capsule -> task, but rendered task -> capsule)
                    edges.append(
                        {
                            "source_urn": urn,
                            "target_urn": consumer["task_urn"],
                            "edge_type": "consumes",
                            "edge_category": "orchestration",
                            "access_pattern": consumer.get("access_pattern"),
                        }
                    )

        elif is_task:
            # Start from task (not implemented yet - would follow task dependencies)
            raise NotImplementedError("Task-centric lineage not yet implemented")

        # Deduplicate nodes by URN
        unique_nodes = {}
        for node in nodes:
            urn = node["urn"]
            if urn not in unique_nodes:
                unique_nodes[urn] = node

        return {
            "root_urn": urn,
            "nodes": list(unique_nodes.values()),
            "edges": edges,
            "summary": {
                "total_nodes": len(unique_nodes),
                "total_edges": len(edges),
                "capsule_count": sum(1 for n in unique_nodes.values() if n["type"] == "capsule"),
                "task_count": sum(1 for n in unique_nodes.values() if n["type"] == "task"),
                "data_edges": sum(1 for e in edges if e["edge_category"] == "data_lineage"),
                "orchestration_edges": sum(
                    1 for e in edges if e["edge_category"] == "orchestration"
                ),
            },
        }

    async def analyze_pipeline_impact(
        self,
        pipeline_urn: str,
        scenario: Literal["modify", "disable", "delete"] = "modify",
        task_urn: Optional[str] = None,
    ) -> dict:
        """Analyze the impact of changes to a pipeline.

        Args:
            pipeline_urn: URN of pipeline to analyze
            scenario: Type of change (modify, disable, delete)
            task_urn: Optional specific task URN for task-level analysis

        Returns:
            Impact analysis with affected capsules and downstream dependencies
        """
        pipeline = await self.pipeline_repo.get_by_urn(pipeline_urn)
        if not pipeline:
            raise ValueError(f"Pipeline not found: {pipeline_urn}")

        # Get all data touched by this pipeline
        footprint = await self.pipeline_repo.get_data_footprint(pipeline.id)

        # Analyze impact based on scenario
        if scenario == "modify":
            # Identify capsules that would be affected by pipeline modification
            affected_capsules = footprint["produces"] + footprint["transforms"]
            risk_level = "medium"
            message = "Modifying this pipeline may affect downstream data consumers"

        elif scenario == "disable":
            # If disabled, produced capsules won't be updated
            affected_capsules = footprint["produces"]
            risk_level = "high"
            message = "Disabling this pipeline will stop data updates"

        elif scenario == "delete":
            # Deletion means no data production
            affected_capsules = footprint["produces"] + footprint["transforms"]
            risk_level = "critical"
            message = "Deleting this pipeline will permanently stop data production"

        else:
            raise ValueError(f"Unknown scenario: {scenario}")

        # For each affected capsule, find downstream consumers
        downstream_impact = []
        for capsule_ref in affected_capsules:
            capsule_urn = capsule_ref["capsule_urn"]

            # Get consumers of this capsule
            consumers = await self.edge_repo.get_consumers(capsule_urn)

            # Get downstream capsules
            capsule = await self.capsule_repo.get_by_urn(capsule_urn)
            if capsule:
                downstream_capsules = await self.capsule_repo.get_downstream(
                    capsule.id, depth=2
                )

                downstream_impact.append(
                    {
                        "capsule_urn": capsule_urn,
                        "capsule_name": capsule_ref["capsule_name"],
                        "consuming_tasks": len(consumers),
                        "downstream_capsules": len(downstream_capsules),
                        "consumers": consumers,
                    }
                )

        return {
            "pipeline_urn": pipeline_urn,
            "pipeline_name": pipeline.name,
            "scenario": scenario,
            "risk_level": risk_level,
            "message": message,
            "directly_affected_capsules": len(affected_capsules),
            "total_downstream_impact": sum(
                d["downstream_capsules"] for d in downstream_impact
            ),
            "total_consuming_tasks": sum(d["consuming_tasks"] for d in downstream_impact),
            "impact_details": downstream_impact,
            "recommendations": self._generate_recommendations(
                scenario, len(affected_capsules), downstream_impact
            ),
        }

    def _generate_recommendations(
        self, scenario: str, affected_count: int, downstream_impact: list
    ) -> list[str]:
        """Generate recommendations based on impact analysis."""
        recommendations = []

        if scenario == "delete":
            recommendations.append(
                "Consider disabling instead of deleting to preserve historical metadata"
            )
            recommendations.append("Ensure backup pipelines exist for critical data")

        if affected_count > 5:
            recommendations.append(
                f"High impact: {affected_count} capsules directly affected"
            )
            recommendations.append("Plan maintenance window for changes")

        total_consumers = sum(d["consuming_tasks"] for d in downstream_impact)
        if total_consumers > 0:
            recommendations.append(
                f"Notify owners of {total_consumers} downstream pipeline tasks"
            )

        if scenario in ["disable", "delete"]:
            recommendations.append(
                "Review SLAs for affected data products before proceeding"
            )

        return recommendations
