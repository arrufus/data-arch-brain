"""Repository for Capsule data access."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, literal_column, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.middleware import sanitize_search_query
from src.models.capsule import Capsule
from src.models.lineage import CapsuleLineage
from src.repositories.base import BaseRepository


class CapsuleRepository(BaseRepository[Capsule]):
    """Repository for capsule operations."""

    model_class = Capsule

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Capsule]:
        """Get all capsules with columns and domain eagerly loaded."""
        stmt = (
            select(Capsule)
            .options(
                selectinload(Capsule.columns),
                selectinload(Capsule.domain),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_urn(self, urn: str) -> Optional[Capsule]:
        """Get capsule by URN."""
        stmt = select(Capsule).where(Capsule.urn == urn)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_urns(self, urns: list[str]) -> Sequence[Capsule]:
        """Get capsules by URNs."""
        if not urns:
            return []
        stmt = select(Capsule).where(Capsule.urn.in_(urns))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_with_columns(self, id: UUID) -> Optional[Capsule]:
        """Get capsule with columns eagerly loaded."""
        stmt = (
            select(Capsule)
            .options(selectinload(Capsule.columns))
            .where(Capsule.id == id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_urn_with_columns(self, urn: str) -> Optional[Capsule]:
        """Get capsule by URN with columns and related data eagerly loaded."""
        stmt = (
            select(Capsule)
            .options(
                selectinload(Capsule.columns),
                selectinload(Capsule.domain),
                selectinload(Capsule.owner),
                selectinload(Capsule.source_system),
                selectinload(Capsule.violations),
                selectinload(Capsule.upstream_edges),
                selectinload(Capsule.downstream_edges),
            )
            .where(Capsule.urn == urn)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_layer(
        self,
        layer: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Capsule]:
        """Get capsules by architecture layer."""
        stmt = (
            select(Capsule)
            .options(
                selectinload(Capsule.columns),
                selectinload(Capsule.domain),
            )
            .where(Capsule.layer == layer)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_domain(
        self,
        domain_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Capsule]:
        """Get capsules by domain."""
        stmt = (
            select(Capsule)
            .options(
                selectinload(Capsule.columns),
                selectinload(Capsule.domain),
            )
            .where(Capsule.domain_id == domain_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_type(
        self,
        capsule_type: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Capsule]:
        """Get capsules by type."""
        stmt = (
            select(Capsule)
            .options(
                selectinload(Capsule.columns),
                selectinload(Capsule.domain),
            )
            .where(Capsule.capsule_type == capsule_type)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_source_system(
        self,
        source_system_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Capsule]:
        """Get capsules by source system."""
        stmt = (
            select(Capsule)
            .where(Capsule.source_system_id == source_system_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_with_pii(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Capsule]:
        """Get capsules that have PII columns."""
        from src.models.column import Column

        # Subquery to find capsules with PII columns
        subq = (
            select(Column.capsule_id)
            .where(Column.pii_type.isnot(None))
            .distinct()
            .subquery()
        )

        stmt = (
            select(Capsule)
            .options(
                selectinload(Capsule.columns),
                selectinload(Capsule.domain),
            )
            .where(Capsule.id.in_(select(subq)))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search(
        self,
        query: str,
        capsule_type: Optional[str] = None,
        layer: Optional[str] = None,
        domain_id: Optional[UUID] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Capsule]:
        """Search capsules by name or description."""
        # Sanitize search query to prevent SQL injection
        safe_query = sanitize_search_query(query)
        if not safe_query:
            return []

        search_pattern = f"%{safe_query}%"
        stmt = (
            select(Capsule)
            .options(
                selectinload(Capsule.columns),
                selectinload(Capsule.domain),
            )
            .where(
                Capsule.name.ilike(search_pattern)
                | Capsule.description.ilike(search_pattern)
            )
        )

        if capsule_type:
            stmt = stmt.where(Capsule.capsule_type == capsule_type)
        if layer:
            stmt = stmt.where(Capsule.layer == layer)
        if domain_id:
            stmt = stmt.where(Capsule.domain_id == domain_id)

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_upstream(
        self,
        capsule_id: UUID,
        depth: int = 1,
    ) -> Sequence[Capsule]:
        """
        Get upstream capsules (dependencies) using recursive CTE.
        
        This uses a single database query with a Common Table Expression (CTE)
        instead of multiple recursive Python calls, resulting in O(1) queries
        instead of O(depth) queries.
        """
        if depth < 1:
            return []

        from sqlalchemy import literal
        from sqlalchemy.dialects import postgresql
        
        # Check if we're using PostgreSQL (supports recursive CTEs natively)
        dialect_name = self.session.bind.dialect.name if self.session.bind else "postgresql"
        
        if dialect_name == "postgresql":
            # Use recursive CTE for PostgreSQL
            # Base case: direct upstream of the target capsule
            base_query = (
                select(
                    CapsuleLineage.source_id.label("id"),
                    literal(1).label("level"),
                )
                .where(CapsuleLineage.target_id == capsule_id)
            )
            
            # Recursive CTE
            cte = base_query.cte(name="upstream_lineage", recursive=True)
            
            # Recursive case: upstream of upstream (join on source_id)
            recursive_query = (
                select(
                    CapsuleLineage.source_id.label("id"),
                    (cte.c.level + 1).label("level"),
                )
                .join(cte, CapsuleLineage.target_id == cte.c.id)
                .where(cte.c.level < depth)
            )
            
            # Union the base and recursive parts
            cte = cte.union_all(recursive_query)
            
            # Get distinct capsule IDs from CTE
            upstream_ids_query = select(cte.c.id).distinct()
            
            # Final query to get capsule objects
            stmt = (
                select(Capsule)
                .where(Capsule.id.in_(upstream_ids_query))
            )
            
            result = await self.session.execute(stmt)
            return result.scalars().all()
        else:
            # Fallback for SQLite (used in tests) - iterative approach
            return await self._get_upstream_iterative(capsule_id, depth)

    async def _get_upstream_iterative(
        self,
        capsule_id: UUID,
        depth: int,
    ) -> Sequence[Capsule]:
        """Iterative upstream query for non-PostgreSQL databases (e.g., SQLite in tests)."""
        all_upstream_ids: set[UUID] = set()
        current_level_ids = {capsule_id}
        
        for _ in range(depth):
            if not current_level_ids:
                break
            
            # Get direct upstream for all IDs in current level
            stmt = (
                select(CapsuleLineage.source_id)
                .where(CapsuleLineage.target_id.in_(current_level_ids))
            )
            result = await self.session.execute(stmt)
            next_level_ids = {row[0] for row in result.all()}
            
            # Add to results and prepare next iteration
            new_ids = next_level_ids - all_upstream_ids - {capsule_id}
            all_upstream_ids.update(new_ids)
            current_level_ids = new_ids
        
        if not all_upstream_ids:
            return []
        
        # Fetch all capsules in one query
        stmt = select(Capsule).where(Capsule.id.in_(all_upstream_ids))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_downstream(
        self,
        capsule_id: UUID,
        depth: int = 1,
    ) -> Sequence[Capsule]:
        """
        Get downstream capsules (dependents) using recursive CTE.
        
        This uses a single database query with a Common Table Expression (CTE)
        instead of multiple recursive Python calls, resulting in O(1) queries
        instead of O(depth) queries.
        """
        if depth < 1:
            return []

        from sqlalchemy import literal
        
        # Check if we're using PostgreSQL (supports recursive CTEs natively)
        dialect_name = self.session.bind.dialect.name if self.session.bind else "postgresql"
        
        if dialect_name == "postgresql":
            # Use recursive CTE for PostgreSQL
            # Base case: direct downstream of the target capsule
            base_query = (
                select(
                    CapsuleLineage.target_id.label("id"),
                    literal(1).label("level"),
                )
                .where(CapsuleLineage.source_id == capsule_id)
            )
            
            # Recursive CTE
            cte = base_query.cte(name="downstream_lineage", recursive=True)
            
            # Recursive case: downstream of downstream (join on target_id)
            recursive_query = (
                select(
                    CapsuleLineage.target_id.label("id"),
                    (cte.c.level + 1).label("level"),
                )
                .join(cte, CapsuleLineage.source_id == cte.c.id)
                .where(cte.c.level < depth)
            )
            
            # Union the base and recursive parts
            cte = cte.union_all(recursive_query)
            
            # Get distinct capsule IDs from CTE
            downstream_ids_query = select(cte.c.id).distinct()
            
            # Final query to get capsule objects
            stmt = (
                select(Capsule)
                .where(Capsule.id.in_(downstream_ids_query))
            )
            
            result = await self.session.execute(stmt)
            return result.scalars().all()
        else:
            # Fallback for SQLite (used in tests) - iterative approach
            return await self._get_downstream_iterative(capsule_id, depth)

    async def _get_downstream_iterative(
        self,
        capsule_id: UUID,
        depth: int,
    ) -> Sequence[Capsule]:
        """Iterative downstream query for non-PostgreSQL databases (e.g., SQLite in tests)."""
        all_downstream_ids: set[UUID] = set()
        current_level_ids = {capsule_id}
        
        for _ in range(depth):
            if not current_level_ids:
                break
            
            # Get direct downstream for all IDs in current level
            stmt = (
                select(CapsuleLineage.target_id)
                .where(CapsuleLineage.source_id.in_(current_level_ids))
            )
            result = await self.session.execute(stmt)
            next_level_ids = {row[0] for row in result.all()}
            
            # Add to results and prepare next iteration
            new_ids = next_level_ids - all_downstream_ids - {capsule_id}
            all_downstream_ids.update(new_ids)
            current_level_ids = new_ids
        
        if not all_downstream_ids:
            return []
        
        # Fetch all capsules in one query
        stmt = select(Capsule).where(Capsule.id.in_(all_downstream_ids))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_layer(self) -> dict[str, int]:
        """Count capsules by layer."""
        stmt = (
            select(Capsule.layer, func.count(Capsule.id))
            .group_by(Capsule.layer)
        )
        result = await self.session.execute(stmt)
        return {row[0] or "unknown": row[1] for row in result.all()}

    async def count_by_type(self) -> dict[str, int]:
        """Count capsules by type."""
        stmt = (
            select(Capsule.capsule_type, func.count(Capsule.id))
            .group_by(Capsule.capsule_type)
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def upsert_by_urn(self, capsule: Capsule) -> tuple[Capsule, bool]:
        """
        Insert or update a capsule by URN.
        Returns (capsule, created) where created is True if new.
        """
        existing = await self.get_by_urn(capsule.urn)
        if existing:
            # Update existing
            existing.name = capsule.name
            existing.capsule_type = capsule.capsule_type
            existing.database_name = capsule.database_name
            existing.schema_name = capsule.schema_name
            existing.layer = capsule.layer
            existing.materialization = capsule.materialization
            existing.description = capsule.description
            existing.has_tests = capsule.has_tests
            existing.test_count = capsule.test_count
            existing.meta = capsule.meta
            existing.tags = capsule.tags
            existing.domain_id = capsule.domain_id
            existing.source_system_id = capsule.source_system_id
            existing.ingestion_id = capsule.ingestion_id
            await self.session.flush()
            return existing, False
        else:
            # Create new
            self.session.add(capsule)
            await self.session.flush()
            await self.session.refresh(capsule)
            return capsule, True

    async def delete_by_ingestion(self, ingestion_id: UUID) -> int:
        """Delete all capsules from a specific ingestion. Returns count deleted."""
        stmt = select(Capsule).where(Capsule.ingestion_id == ingestion_id)
        result = await self.session.execute(stmt)
        capsules = result.scalars().all()
        count = len(capsules)
        for capsule in capsules:
            await self.session.delete(capsule)
        await self.session.flush()
        return count
