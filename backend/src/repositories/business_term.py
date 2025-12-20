"""Repository for business terms."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload

from src.models import BusinessTerm, CapsuleBusinessTerm, ColumnBusinessTerm
from src.repositories.base import BaseRepository


class BusinessTermRepository(BaseRepository[BusinessTerm]):
    """Repository for business term operations."""

    model_class = BusinessTerm

    async def get_by_name(self, term_name: str) -> Optional[BusinessTerm]:
        """Get business term by name."""
        stmt = select(BusinessTerm).where(BusinessTerm.term_name == term_name)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def search(
        self,
        query: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[BusinessTerm]:
        """Search business terms by name or definition."""
        search_term = f"%{query}%"
        stmt = (
            select(BusinessTerm)
            .where(
                or_(
                    BusinessTerm.term_name.ilike(search_term),
                    BusinessTerm.display_name.ilike(search_term),
                    BusinessTerm.definition.ilike(search_term),
                )
            )
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
    ) -> Sequence[BusinessTerm]:
        """Get all terms in a domain."""
        stmt = (
            select(BusinessTerm)
            .where(BusinessTerm.domain_id == domain_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_category(
        self,
        category: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[BusinessTerm]:
        """Get all terms in a category."""
        stmt = (
            select(BusinessTerm)
            .where(BusinessTerm.category == category)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_status(
        self,
        approval_status: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[BusinessTerm]:
        """Get all terms with a specific approval status."""
        stmt = (
            select(BusinessTerm)
            .where(BusinessTerm.approval_status == approval_status)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_approved_terms(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[BusinessTerm]:
        """Get all approved terms."""
        return await self.get_by_status("approved", offset, limit)

    async def get_categories(self) -> Sequence[str]:
        """Get all unique categories."""
        stmt = select(BusinessTerm.category).distinct().where(
            BusinessTerm.category.isnot(None)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class CapsuleBusinessTermRepository(BaseRepository[CapsuleBusinessTerm]):
    """Repository for capsule-business term associations."""

    model_class = CapsuleBusinessTerm

    async def get_by_capsule(
        self,
        capsule_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[CapsuleBusinessTerm]:
        """Get all business term associations for a capsule."""
        stmt = (
            select(CapsuleBusinessTerm)
            .where(CapsuleBusinessTerm.capsule_id == capsule_id)
            .options(joinedload(CapsuleBusinessTerm.business_term))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_term(
        self,
        business_term_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[CapsuleBusinessTerm]:
        """Get all capsules associated with a business term."""
        stmt = (
            select(CapsuleBusinessTerm)
            .where(CapsuleBusinessTerm.business_term_id == business_term_id)
            .options(joinedload(CapsuleBusinessTerm.capsule))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def exists_association(
        self,
        capsule_id: UUID,
        business_term_id: UUID,
    ) -> bool:
        """Check if association exists."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(CapsuleBusinessTerm).where(
            CapsuleBusinessTerm.capsule_id == capsule_id,
            CapsuleBusinessTerm.business_term_id == business_term_id,
        )
        result = await self.session.execute(stmt)
        return (result.scalar() or 0) > 0


class ColumnBusinessTermRepository(BaseRepository[ColumnBusinessTerm]):
    """Repository for column-business term associations."""

    model_class = ColumnBusinessTerm

    async def get_by_column(
        self,
        column_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ColumnBusinessTerm]:
        """Get all business term associations for a column."""
        stmt = (
            select(ColumnBusinessTerm)
            .where(ColumnBusinessTerm.column_id == column_id)
            .options(joinedload(ColumnBusinessTerm.business_term))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_term(
        self,
        business_term_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ColumnBusinessTerm]:
        """Get all columns associated with a business term."""
        stmt = (
            select(ColumnBusinessTerm)
            .where(ColumnBusinessTerm.business_term_id == business_term_id)
            .options(joinedload(ColumnBusinessTerm.column))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def exists_association(
        self,
        column_id: UUID,
        business_term_id: UUID,
    ) -> bool:
        """Check if association exists."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(ColumnBusinessTerm).where(
            ColumnBusinessTerm.column_id == column_id,
            ColumnBusinessTerm.business_term_id == business_term_id,
        )
        result = await self.session.execute(stmt)
        return (result.scalar() or 0) > 0
