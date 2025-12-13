"""Repository for lineage data access."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.lineage import CapsuleLineage, ColumnLineage


class CapsuleLineageRepository:
    """Repository for capsule lineage operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: UUID) -> Optional[CapsuleLineage]:
        """Get lineage edge by ID."""
        return await self.session.get(CapsuleLineage, id)

    async def get_by_source_and_target(
        self,
        source_urn: str,
        target_urn: str,
    ) -> Optional[CapsuleLineage]:
        """Get lineage edge by source and target URN."""
        stmt = select(CapsuleLineage).where(
            CapsuleLineage.source_urn == source_urn,
            CapsuleLineage.target_urn == target_urn,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_upstream_edges(
        self,
        target_id: UUID,
    ) -> Sequence[CapsuleLineage]:
        """Get all edges flowing into a capsule."""
        stmt = select(CapsuleLineage).where(
            CapsuleLineage.target_id == target_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_downstream_edges(
        self,
        source_id: UUID,
    ) -> Sequence[CapsuleLineage]:
        """Get all edges flowing from a capsule."""
        stmt = select(CapsuleLineage).where(
            CapsuleLineage.source_id == source_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_ingestion(
        self,
        ingestion_id: UUID,
    ) -> Sequence[CapsuleLineage]:
        """Get all edges from a specific ingestion."""
        stmt = select(CapsuleLineage).where(
            CapsuleLineage.ingestion_id == ingestion_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, edge: CapsuleLineage) -> CapsuleLineage:
        """Create a lineage edge."""
        self.session.add(edge)
        await self.session.flush()
        await self.session.refresh(edge)
        return edge

    async def create_many(self, edges: list[CapsuleLineage]) -> list[CapsuleLineage]:
        """Create multiple lineage edges."""
        self.session.add_all(edges)
        await self.session.flush()
        for edge in edges:
            await self.session.refresh(edge)
        return edges

    async def upsert(self, edge: CapsuleLineage) -> tuple[CapsuleLineage, bool]:
        """
        Insert or update a lineage edge.
        Returns (edge, created) where created is True if new.
        """
        existing = await self.get_by_source_and_target(
            edge.source_urn, edge.target_urn
        )
        if existing:
            existing.source_id = edge.source_id
            existing.target_id = edge.target_id
            existing.edge_type = edge.edge_type
            existing.transformation = edge.transformation
            existing.meta = edge.meta
            existing.ingestion_id = edge.ingestion_id
            await self.session.flush()
            return existing, False
        else:
            self.session.add(edge)
            await self.session.flush()
            await self.session.refresh(edge)
            return edge, True

    async def delete_by_ingestion(self, ingestion_id: UUID) -> int:
        """Delete all edges from a specific ingestion. Returns count deleted."""
        stmt = select(CapsuleLineage).where(
            CapsuleLineage.ingestion_id == ingestion_id
        )
        result = await self.session.execute(stmt)
        edges = result.scalars().all()
        count = len(edges)
        for edge in edges:
            await self.session.delete(edge)
        await self.session.flush()
        return count

    async def delete_edges_for_capsule(self, capsule_id: UUID) -> int:
        """Delete all edges for a capsule (both directions)."""
        stmt = select(CapsuleLineage).where(
            (CapsuleLineage.source_id == capsule_id)
            | (CapsuleLineage.target_id == capsule_id)
        )
        result = await self.session.execute(stmt)
        edges = result.scalars().all()
        count = len(edges)
        for edge in edges:
            await self.session.delete(edge)
        await self.session.flush()
        return count


class ColumnLineageRepository:
    """Repository for column lineage operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: UUID) -> Optional[ColumnLineage]:
        """Get lineage edge by ID."""
        return await self.session.get(ColumnLineage, id)

    async def get_by_source_and_target(
        self,
        source_urn: str,
        target_urn: str,
    ) -> Optional[ColumnLineage]:
        """Get lineage edge by source and target URN."""
        stmt = select(ColumnLineage).where(
            ColumnLineage.source_urn == source_urn,
            ColumnLineage.target_urn == target_urn,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_upstream_edges(
        self,
        target_column_id: UUID,
    ) -> Sequence[ColumnLineage]:
        """Get all edges flowing into a column."""
        stmt = select(ColumnLineage).where(
            ColumnLineage.target_column_id == target_column_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_downstream_edges(
        self,
        source_column_id: UUID,
    ) -> Sequence[ColumnLineage]:
        """Get all edges flowing from a column."""
        stmt = select(ColumnLineage).where(
            ColumnLineage.source_column_id == source_column_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, edge: ColumnLineage) -> ColumnLineage:
        """Create a lineage edge."""
        self.session.add(edge)
        await self.session.flush()
        await self.session.refresh(edge)
        return edge

    async def create_many(self, edges: list[ColumnLineage]) -> list[ColumnLineage]:
        """Create multiple lineage edges."""
        self.session.add_all(edges)
        await self.session.flush()
        for edge in edges:
            await self.session.refresh(edge)
        return edges

    async def upsert(self, edge: ColumnLineage) -> tuple[ColumnLineage, bool]:
        """Insert or update a column lineage edge."""
        existing = await self.get_by_source_and_target(
            edge.source_urn, edge.target_urn
        )
        if existing:
            existing.source_column_id = edge.source_column_id
            existing.target_column_id = edge.target_column_id
            existing.transformation_type = edge.transformation_type
            existing.transformation_expr = edge.transformation_expr
            existing.ingestion_id = edge.ingestion_id
            await self.session.flush()
            return existing, False
        else:
            self.session.add(edge)
            await self.session.flush()
            await self.session.refresh(edge)
            return edge, True
