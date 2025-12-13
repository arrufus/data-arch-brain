"""Repository for Domain and Owner data access."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middleware import sanitize_search_query
from src.models.domain import Domain, Owner
from src.repositories.base import BaseRepository


class DomainRepository(BaseRepository[Domain]):
    """Repository for domain operations."""

    model_class = Domain

    async def get_by_name(self, name: str) -> Optional[Domain]:
        """Get domain by name (case-insensitive)."""
        stmt = select(Domain).where(func.lower(Domain.name) == name.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        name: str,
        description: Optional[str] = None,
    ) -> tuple[Domain, bool]:
        """
        Get existing domain or create new one.
        Returns (domain, created) where created is True if new.
        """
        existing = await self.get_by_name(name)
        if existing:
            return existing, False

        domain = Domain(name=name, description=description)
        self.session.add(domain)
        await self.session.flush()
        await self.session.refresh(domain)
        return domain, True

    async def get_root_domains(self) -> Sequence[Domain]:
        """Get all root-level domains (no parent)."""
        stmt = select(Domain).where(Domain.parent_id.is_(None))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_children(self, parent_id: UUID) -> Sequence[Domain]:
        """Get child domains of a parent."""
        stmt = select(Domain).where(Domain.parent_id == parent_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search(
        self,
        query: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Domain]:
        """Search domains by name or description."""
        # Sanitize search query to prevent SQL injection
        safe_query = sanitize_search_query(query)
        if not safe_query:
            return []

        search_pattern = f"%{safe_query}%"
        stmt = (
            select(Domain)
            .where(
                Domain.name.ilike(search_pattern)
                | Domain.description.ilike(search_pattern)
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class OwnerRepository(BaseRepository[Owner]):
    """Repository for owner operations."""

    model_class = Owner

    async def get_by_name(self, name: str) -> Optional[Owner]:
        """Get owner by name."""
        stmt = select(Owner).where(Owner.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        name: str,
        owner_type: str = "team",
        email: Optional[str] = None,
    ) -> tuple[Owner, bool]:
        """
        Get existing owner or create new one.
        Returns (owner, created) where created is True if new.
        """
        existing = await self.get_by_name(name)
        if existing:
            return existing, False

        owner = Owner(name=name, owner_type=owner_type, email=email)
        self.session.add(owner)
        await self.session.flush()
        await self.session.refresh(owner)
        return owner, True

    async def get_by_type(
        self,
        owner_type: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Owner]:
        """Get owners by type."""
        stmt = (
            select(Owner)
            .where(Owner.owner_type == owner_type)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
