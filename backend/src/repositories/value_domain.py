"""Repository for value domains."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import or_, select

from src.models import ValueDomain
from src.repositories.base import BaseRepository


class ValueDomainRepository(BaseRepository[ValueDomain]):
    """Repository for value domain operations."""

    model_class = ValueDomain

    async def get_by_name(self, domain_name: str) -> Optional[ValueDomain]:
        """Get value domain by name."""
        stmt = select(ValueDomain).where(ValueDomain.domain_name == domain_name)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def search(
        self,
        query: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ValueDomain]:
        """Search value domains by name or description."""
        search_term = f"%{query}%"
        stmt = (
            select(ValueDomain)
            .where(
                or_(
                    ValueDomain.domain_name.ilike(search_term),
                    ValueDomain.description.ilike(search_term),
                )
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_type(
        self,
        domain_type: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ValueDomain]:
        """Get all domains of a specific type."""
        stmt = (
            select(ValueDomain)
            .where(ValueDomain.domain_type == domain_type)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_enum_domains(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ValueDomain]:
        """Get all enum type domains."""
        return await self.get_by_type("enum", offset, limit)

    async def get_pattern_domains(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ValueDomain]:
        """Get all pattern type domains."""
        return await self.get_by_type("pattern", offset, limit)

    async def get_by_owner(
        self,
        owner_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ValueDomain]:
        """Get all domains owned by a specific owner."""
        stmt = (
            select(ValueDomain)
            .where(ValueDomain.owner_id == owner_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_extensible_domains(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ValueDomain]:
        """Get all extensible domains."""
        stmt = (
            select(ValueDomain)
            .where(ValueDomain.is_extensible == True)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
