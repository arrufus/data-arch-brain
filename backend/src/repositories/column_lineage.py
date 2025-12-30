"""Repository for column-level lineage operations (Phase 6)."""

from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.lineage import ColumnLineage, ColumnVersion, TaskColumnEdge
from src.repositories.base import BaseRepository


class ColumnLineageRepository(BaseRepository[ColumnLineage]):
    """Repository for column-to-column lineage operations."""

    model_class = ColumnLineage

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_upstream_columns(
        self,
        column_urn: str,
        depth: int = 3,
        offset: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        """Get upstream columns (sources) for a given column.

        Args:
            column_urn: URN of the column to trace upstream
            depth: How many hops to traverse upstream
            offset: Pagination offset
            limit: Max results per page

        Returns:
            List of upstream column dictionaries with lineage metadata
        """
        from sqlalchemy import text

        # Recursive CTE to traverse upstream
        query = text("""
            WITH RECURSIVE upstream AS (
                -- Base case: direct upstream columns
                SELECT
                    cl.source_column_id,
                    cl.source_column_urn,
                    cl.edge_type,
                    cl.transformation_type,
                    cl.transformation_logic,
                    cl.confidence,
                    cl.detected_by,
                    c.name as column_name,
                    c.data_type,
                    caps.urn as capsule_urn,
                    caps.name as capsule_name,
                    1 as depth_level
                FROM dcs.column_lineage cl
                JOIN dcs.columns c ON cl.source_column_id = c.id
                JOIN dcs.capsules caps ON c.capsule_id = caps.id
                WHERE cl.target_column_urn = :column_urn

                UNION ALL

                -- Recursive case: traverse further upstream
                SELECT
                    cl.source_column_id,
                    cl.source_column_urn,
                    cl.edge_type,
                    cl.transformation_type,
                    cl.transformation_logic,
                    cl.confidence,
                    cl.detected_by,
                    c.name as column_name,
                    c.data_type,
                    caps.urn as capsule_urn,
                    caps.name as capsule_name,
                    u.depth_level + 1
                FROM dcs.column_lineage cl
                JOIN dcs.columns c ON cl.source_column_id = c.id
                JOIN dcs.capsules caps ON c.capsule_id = caps.id
                JOIN upstream u ON cl.target_column_urn = u.source_column_urn
                WHERE u.depth_level < :max_depth
            )
            SELECT DISTINCT
                source_column_urn,
                column_name,
                data_type,
                capsule_urn,
                capsule_name,
                edge_type,
                transformation_type,
                transformation_logic,
                confidence,
                detected_by,
                depth_level
            FROM upstream
            ORDER BY depth_level, source_column_urn
            OFFSET :offset
            LIMIT :limit
        """)

        result = await self.session.execute(
            query,
            {
                "column_urn": column_urn,
                "max_depth": depth,
                "offset": offset,
                "limit": limit,
            },
        )

        rows = result.fetchall()
        return [
            {
                "column_urn": row.source_column_urn,
                "column_name": row.column_name,
                "data_type": row.data_type,
                "capsule_urn": row.capsule_urn,
                "capsule_name": row.capsule_name,
                "edge_type": row.edge_type,
                "transformation_type": row.transformation_type,
                "transformation_logic": row.transformation_logic,
                "confidence": float(row.confidence),
                "detected_by": row.detected_by,
                "depth": row.depth_level,
            }
            for row in rows
        ]

    async def get_downstream_columns(
        self,
        column_urn: str,
        depth: int = 3,
        offset: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        """Get downstream columns (targets) for a given column.

        Args:
            column_urn: URN of the column to trace downstream
            depth: How many hops to traverse downstream
            offset: Pagination offset
            limit: Max results per page

        Returns:
            List of downstream column dictionaries with lineage metadata
        """
        from sqlalchemy import text

        # Recursive CTE to traverse downstream
        query = text("""
            WITH RECURSIVE downstream AS (
                -- Base case: direct downstream columns
                SELECT
                    cl.target_column_id,
                    cl.target_column_urn,
                    cl.edge_type,
                    cl.transformation_type,
                    cl.transformation_logic,
                    cl.confidence,
                    cl.detected_by,
                    c.name as column_name,
                    c.data_type,
                    caps.urn as capsule_urn,
                    caps.name as capsule_name,
                    1 as depth_level
                FROM dcs.column_lineage cl
                JOIN dcs.columns c ON cl.target_column_id = c.id
                JOIN dcs.capsules caps ON c.capsule_id = caps.id
                WHERE cl.source_column_urn = :column_urn

                UNION ALL

                -- Recursive case: traverse further downstream
                SELECT
                    cl.target_column_id,
                    cl.target_column_urn,
                    cl.edge_type,
                    cl.transformation_type,
                    cl.transformation_logic,
                    cl.confidence,
                    cl.detected_by,
                    c.name as column_name,
                    c.data_type,
                    caps.urn as capsule_urn,
                    caps.name as capsule_name,
                    d.depth_level + 1
                FROM dcs.column_lineage cl
                JOIN dcs.columns c ON cl.target_column_id = c.id
                JOIN dcs.capsules caps ON c.capsule_id = caps.id
                JOIN downstream d ON cl.source_column_urn = d.target_column_urn
                WHERE d.depth_level < :max_depth
            )
            SELECT DISTINCT
                target_column_urn as column_urn,
                column_name,
                data_type,
                capsule_urn,
                capsule_name,
                edge_type,
                transformation_type,
                transformation_logic,
                confidence,
                detected_by,
                depth_level
            FROM downstream
            ORDER BY depth_level, column_urn
            OFFSET :offset
            LIMIT :limit
        """)

        result = await self.session.execute(
            query,
            {
                "column_urn": column_urn,
                "max_depth": depth,
                "offset": offset,
                "limit": limit,
            },
        )

        rows = result.fetchall()
        return [
            {
                "column_urn": row.column_urn,
                "column_name": row.column_name,
                "data_type": row.data_type,
                "capsule_urn": row.capsule_urn,
                "capsule_name": row.capsule_name,
                "edge_type": row.edge_type,
                "transformation_type": row.transformation_type,
                "transformation_logic": row.transformation_logic,
                "confidence": float(row.confidence),
                "detected_by": row.detected_by,
                "depth": row.depth_level,
            }
            for row in rows
        ]

    async def get_column_transformations(
        self,
        column_urn: str,
    ) -> list[dict]:
        """Get all transformations applied to a column.

        Args:
            column_urn: URN of the column

        Returns:
            List of transformations with logic and metadata
        """
        # Get all edges where this column is the target
        stmt = (
            select(ColumnLineage)
            .where(ColumnLineage.target_column_urn == column_urn)
            .where(ColumnLineage.transformation_logic.isnot(None))
        )
        result = await self.session.execute(stmt)
        edges = result.scalars().all()

        return [
            {
                "source_column_urn": edge.source_column_urn,
                "transformation_type": edge.transformation_type,
                "transformation_logic": edge.transformation_logic,
                "edge_type": edge.edge_type,
                "confidence": float(edge.confidence),
                "detected_by": edge.detected_by,
            }
            for edge in edges
        ]

    async def trace_column_lineage(
        self,
        column_urn: str,
        direction: Literal["upstream", "downstream", "both"] = "both",
        depth: int = 5,
    ) -> dict:
        """Trace full column lineage graph.

        Args:
            column_urn: URN of the column to start tracing from
            direction: Direction to traverse (upstream, downstream, both)
            depth: How many hops to traverse

        Returns:
            Dictionary with nodes (columns) and edges (lineage relationships)

        Example:
            {
                "root_column_urn": "urn:dcs:column:...",
                "nodes": [
                    {
                        "column_urn": "urn:dcs:column:...",
                        "column_name": "customer_id",
                        "capsule_urn": "urn:dcs:postgres:table:...",
                        "data_type": "INTEGER",
                        "depth": 1,
                        "direction": "upstream"
                    }
                ],
                "edges": [
                    {
                        "source_column_urn": "...",
                        "target_column_urn": "...",
                        "edge_type": "derives_from",
                        "transformation_type": "identity",
                        "transformation_logic": null,
                        "confidence": 0.95,
                        "detected_by": "sql_parser"
                    }
                ],
                "summary": {
                    "total_nodes": 10,
                    "total_edges": 9,
                    "max_depth_reached": 3
                }
            }
        """
        from sqlalchemy import text

        nodes_dict = {}
        edges_list = []
        max_depth_reached = 0

        # Get root column info
        root_query = text("""
            SELECT
                c.urn as column_urn,
                c.name as column_name,
                c.data_type,
                caps.urn as capsule_urn,
                caps.name as capsule_name
            FROM dcs.columns c
            JOIN dcs.capsules caps ON c.capsule_id = caps.id
            WHERE c.urn = :column_urn
        """)

        root_result = await self.session.execute(root_query, {"column_urn": column_urn})
        root_row = root_result.first()

        if not root_row:
            raise ValueError(f"Column not found: {column_urn}")

        # Add root node
        nodes_dict[column_urn] = {
            "column_urn": column_urn,
            "column_name": root_row.column_name,
            "data_type": root_row.data_type,
            "capsule_urn": root_row.capsule_urn,
            "capsule_name": root_row.capsule_name,
            "depth": 0,
            "is_root": True,
        }

        # Get upstream if requested
        if direction in ["upstream", "both"]:
            upstream_query = text("""
                WITH RECURSIVE upstream AS (
                    SELECT
                        cl.source_column_urn,
                        cl.target_column_urn,
                        cl.edge_type,
                        cl.transformation_type,
                        cl.transformation_logic,
                        cl.confidence,
                        cl.detected_by,
                        c.name as column_name,
                        c.data_type,
                        caps.urn as capsule_urn,
                        caps.name as capsule_name,
                        1 as depth_level
                    FROM dcs.column_lineage cl
                    JOIN dcs.columns c ON cl.source_column_id = c.id
                    JOIN dcs.capsules caps ON c.capsule_id = caps.id
                    WHERE cl.target_column_urn = :column_urn

                    UNION ALL

                    SELECT
                        cl.source_column_urn,
                        cl.target_column_urn,
                        cl.edge_type,
                        cl.transformation_type,
                        cl.transformation_logic,
                        cl.confidence,
                        cl.detected_by,
                        c.name as column_name,
                        c.data_type,
                        caps.urn as capsule_urn,
                        caps.name as capsule_name,
                        u.depth_level + 1
                    FROM dcs.column_lineage cl
                    JOIN dcs.columns c ON cl.source_column_id = c.id
                    JOIN dcs.capsules caps ON c.capsule_id = caps.id
                    JOIN upstream u ON cl.target_column_urn = u.source_column_urn
                    WHERE u.depth_level < :max_depth
                )
                SELECT * FROM upstream
            """)

            upstream_result = await self.session.execute(
                upstream_query, {"column_urn": column_urn, "max_depth": depth}
            )

            for row in upstream_result:
                # Add node
                if row.source_column_urn not in nodes_dict:
                    nodes_dict[row.source_column_urn] = {
                        "column_urn": row.source_column_urn,
                        "column_name": row.column_name,
                        "data_type": row.data_type,
                        "capsule_urn": row.capsule_urn,
                        "capsule_name": row.capsule_name,
                        "depth": row.depth_level,
                        "direction": "upstream",
                    }

                # Add edge
                edges_list.append({
                    "source_column_urn": row.source_column_urn,
                    "target_column_urn": row.target_column_urn,
                    "edge_type": row.edge_type,
                    "transformation_type": row.transformation_type,
                    "transformation_logic": row.transformation_logic,
                    "confidence": float(row.confidence),
                    "detected_by": row.detected_by,
                })

                max_depth_reached = max(max_depth_reached, row.depth_level)

        # Get downstream if requested
        if direction in ["downstream", "both"]:
            downstream_query = text("""
                WITH RECURSIVE downstream AS (
                    SELECT
                        cl.source_column_urn,
                        cl.target_column_urn,
                        cl.edge_type,
                        cl.transformation_type,
                        cl.transformation_logic,
                        cl.confidence,
                        cl.detected_by,
                        c.name as column_name,
                        c.data_type,
                        caps.urn as capsule_urn,
                        caps.name as capsule_name,
                        1 as depth_level
                    FROM dcs.column_lineage cl
                    JOIN dcs.columns c ON cl.target_column_id = c.id
                    JOIN dcs.capsules caps ON c.capsule_id = caps.id
                    WHERE cl.source_column_urn = :column_urn

                    UNION ALL

                    SELECT
                        cl.source_column_urn,
                        cl.target_column_urn,
                        cl.edge_type,
                        cl.transformation_type,
                        cl.transformation_logic,
                        cl.confidence,
                        cl.detected_by,
                        c.name as column_name,
                        c.data_type,
                        caps.urn as capsule_urn,
                        caps.name as capsule_name,
                        d.depth_level + 1
                    FROM dcs.column_lineage cl
                    JOIN dcs.columns c ON cl.target_column_id = c.id
                    JOIN dcs.capsules caps ON c.capsule_id = caps.id
                    JOIN downstream d ON cl.source_column_urn = d.target_column_urn
                    WHERE d.depth_level < :max_depth
                )
                SELECT * FROM downstream
            """)

            downstream_result = await self.session.execute(
                downstream_query, {"column_urn": column_urn, "max_depth": depth}
            )

            for row in downstream_result:
                # Add node
                if row.target_column_urn not in nodes_dict:
                    nodes_dict[row.target_column_urn] = {
                        "column_urn": row.target_column_urn,
                        "column_name": row.column_name,
                        "data_type": row.data_type,
                        "capsule_urn": row.capsule_urn,
                        "capsule_name": row.capsule_name,
                        "depth": row.depth_level,
                        "direction": "downstream",
                    }

                # Add edge (avoid duplicates if direction=both)
                edge = {
                    "source_column_urn": row.source_column_urn,
                    "target_column_urn": row.target_column_urn,
                    "edge_type": row.edge_type,
                    "transformation_type": row.transformation_type,
                    "transformation_logic": row.transformation_logic,
                    "confidence": float(row.confidence),
                    "detected_by": row.detected_by,
                }
                if edge not in edges_list:
                    edges_list.append(edge)

                max_depth_reached = max(max_depth_reached, row.depth_level)

        return {
            "root_column_urn": column_urn,
            "nodes": list(nodes_dict.values()),
            "edges": edges_list,
            "summary": {
                "total_nodes": len(nodes_dict),
                "total_edges": len(edges_list),
                "max_depth_reached": max_depth_reached,
            },
        }

    async def get_column_impact(
        self,
        column_urn: str,
        change_type: Literal["delete", "rename", "type_change"] = "delete",
    ) -> dict:
        """Analyze impact of column schema change.

        Args:
            column_urn: URN of the column being changed
            change_type: Type of change (delete, rename, type_change)

        Returns:
            Impact analysis with affected columns and breaking changes

        Example:
            {
                "column_urn": "...",
                "change_type": "delete",
                "risk_level": "high",
                "affected_columns": 15,
                "affected_capsules": 8,
                "affected_tasks": 12,
                "breaking_changes": [
                    {
                        "target_column_urn": "...",
                        "reason": "Direct dependency - column will be missing",
                        "suggested_action": "Update transformation logic"
                    }
                ],
                "recommendations": [...]
            }
        """
        from sqlalchemy import text

        # Get all downstream columns (unlimited depth for impact analysis)
        downstream_columns = await self.get_downstream_columns(
            column_urn=column_urn,
            depth=10,  # Deep traversal for comprehensive impact
            offset=0,
            limit=1000,  # Large limit for impact analysis
        )

        # Count unique affected capsules
        affected_capsule_urns = set(col["capsule_urn"] for col in downstream_columns)
        affected_columns_count = len(downstream_columns)
        affected_capsules_count = len(affected_capsule_urns)

        # Count affected tasks
        task_count_query = text("""
            SELECT COUNT(DISTINCT task_urn) as task_count
            FROM dcs.task_column_edges
            WHERE column_urn = :column_urn
        """)
        task_result = await self.session.execute(
            task_count_query, {"column_urn": column_urn}
        )
        task_row = task_result.first()
        affected_tasks_count = task_row.task_count if task_row else 0

        # Identify breaking changes based on change_type
        breaking_changes = []

        if change_type == "delete":
            # Deletion breaks all direct dependencies
            for col in downstream_columns:
                if col["depth"] == 1:  # Direct dependency
                    breaking_changes.append({
                        "target_column_urn": col["column_urn"],
                        "target_column_name": col["column_name"],
                        "capsule_urn": col["capsule_urn"],
                        "capsule_name": col["capsule_name"],
                        "transformation_type": col["transformation_type"],
                        "reason": "Direct dependency - source column will be missing",
                        "suggested_action": "Update transformation logic or remove dependency",
                    })

        elif change_type == "rename":
            # Rename breaks references unless aliased
            for col in downstream_columns:
                if col["depth"] == 1:  # Direct dependency
                    breaking_changes.append({
                        "target_column_urn": col["column_urn"],
                        "target_column_name": col["column_name"],
                        "capsule_urn": col["capsule_urn"],
                        "capsule_name": col["capsule_name"],
                        "transformation_type": col["transformation_type"],
                        "reason": "Column renamed - references may break",
                        "suggested_action": "Update column references in SQL/transformations",
                    })

        elif change_type == "type_change":
            # Type changes break casts and transformations
            for col in downstream_columns:
                if col["transformation_type"] in ["cast", "arithmetic", "string_transform"]:
                    breaking_changes.append({
                        "target_column_urn": col["column_urn"],
                        "target_column_name": col["column_name"],
                        "capsule_urn": col["capsule_urn"],
                        "capsule_name": col["capsule_name"],
                        "transformation_type": col["transformation_type"],
                        "reason": f"Type change may break {col['transformation_type']} transformation",
                        "suggested_action": "Review and update transformation logic",
                    })

        # Calculate risk level
        if affected_columns_count == 0:
            risk_level = "none"
        elif affected_columns_count < 5 and len(breaking_changes) == 0:
            risk_level = "low"
        elif affected_columns_count < 10 and len(breaking_changes) < 3:
            risk_level = "medium"
        else:
            risk_level = "high"

        # Generate recommendations
        recommendations = []
        if change_type == "delete":
            recommendations.append(
                f"Review {len(breaking_changes)} downstream dependencies before deletion"
            )
            recommendations.append(
                "Consider deprecation period with warnings before removal"
            )
            if affected_tasks_count > 0:
                recommendations.append(
                    f"Update {affected_tasks_count} affected pipeline tasks"
                )
        elif change_type == "rename":
            recommendations.append(
                "Use column aliases in queries to maintain backward compatibility"
            )
            recommendations.append(
                f"Update {affected_capsules_count} affected capsules"
            )
        elif change_type == "type_change":
            recommendations.append(
                "Test all downstream transformations with new data type"
            )
            recommendations.append(
                "Add explicit CAST operations where needed"
            )
            if len(breaking_changes) > 0:
                recommendations.append(
                    f"Review {len(breaking_changes)} transformations that may be incompatible"
                )

        return {
            "column_urn": column_urn,
            "change_type": change_type,
            "risk_level": risk_level,
            "affected_columns": affected_columns_count,
            "affected_capsules": affected_capsules_count,
            "affected_tasks": affected_tasks_count,
            "breaking_changes": breaking_changes,
            "recommendations": recommendations,
        }


class TaskColumnEdgeRepository(BaseRepository[TaskColumnEdge]):
    """Repository for task-to-column edge operations."""

    model_class = TaskColumnEdge

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_column_producers(
        self,
        column_urn: str,
        offset: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        """Get tasks that produce (write to) a column.

        Args:
            column_urn: URN of the column
            offset: Pagination offset
            limit: Max results per page

        Returns:
            List of task dictionaries that write to this column
        """
        stmt = (
            select(TaskColumnEdge)
            .where(TaskColumnEdge.column_urn == column_urn)
            .where(TaskColumnEdge.edge_type == "writes")
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        edges = result.scalars().all()

        return [
            {
                "task_urn": edge.task_urn,
                "edge_type": edge.edge_type,
                "transformation_type": edge.transformation_type,
                "operation": edge.operation,
            }
            for edge in edges
        ]

    async def get_column_consumers(
        self,
        column_urn: str,
        offset: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        """Get tasks that consume (read from) a column.

        Args:
            column_urn: URN of the column
            offset: Pagination offset
            limit: Max results per page

        Returns:
            List of task dictionaries that read from this column
        """
        stmt = (
            select(TaskColumnEdge)
            .where(TaskColumnEdge.column_urn == column_urn)
            .where(TaskColumnEdge.edge_type == "reads")
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        edges = result.scalars().all()

        return [
            {
                "task_urn": edge.task_urn,
                "edge_type": edge.edge_type,
                "operation": edge.operation,
            }
            for edge in edges
        ]


class ColumnVersionRepository(BaseRepository[ColumnVersion]):
    """Repository for column version/schema evolution operations."""

    model_class = ColumnVersion

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_column_versions(
        self,
        column_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ColumnVersion]:
        """Get version history for a column.

        Args:
            column_id: ID of the column
            offset: Pagination offset
            limit: Max results per page

        Returns:
            List of ColumnVersion objects ordered by version descending
        """
        stmt = (
            select(ColumnVersion)
            .where(ColumnVersion.column_id == column_id)
            .order_by(ColumnVersion.version.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_breaking_changes(
        self,
        column_id: Optional[UUID] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ColumnVersion]:
        """Get all breaking changes, optionally filtered by column.

        Args:
            column_id: Optional column ID to filter by
            offset: Pagination offset
            limit: Max results per page

        Returns:
            List of ColumnVersion objects that represent breaking changes
        """
        stmt = (
            select(ColumnVersion)
            .where(ColumnVersion.breaking_change == True)
            .order_by(ColumnVersion.valid_from.desc())
        )

        if column_id:
            stmt = stmt.where(ColumnVersion.column_id == column_id)

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
