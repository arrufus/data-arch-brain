"""Repository for DataProduct data access."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.middleware import sanitize_search_query
from src.models.capsule import Capsule
from src.models.data_product import CapsuleDataProduct, CapsuleRole, DataProduct
from src.repositories.base import BaseRepository


class DataProductRepository(BaseRepository[DataProduct]):
    """Repository for data product operations."""

    model_class = DataProduct

    async def get_by_id_with_capsules(
        self, id: UUID
    ) -> Optional[DataProduct]:
        """Get data product by ID with capsule associations eagerly loaded."""
        stmt = (
            select(DataProduct)
            .options(
                selectinload(DataProduct.capsule_associations).selectinload(
                    CapsuleDataProduct.capsule
                ),
                selectinload(DataProduct.domain),
                selectinload(DataProduct.owner),
            )
            .where(DataProduct.id == id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[DataProduct]:
        """Get data product by name (case-insensitive)."""
        stmt = select(DataProduct).where(
            func.lower(DataProduct.name) == name.lower()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_with_relations(
        self,
        offset: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        domain_id: Optional[UUID] = None,
    ) -> Sequence[DataProduct]:
        """Get all data products with relations eagerly loaded."""
        stmt = (
            select(DataProduct)
            .options(
                selectinload(DataProduct.capsule_associations),
                selectinload(DataProduct.domain),
                selectinload(DataProduct.owner),
            )
        )

        if status:
            stmt = stmt.where(DataProduct.status == status)
        if domain_id:
            stmt = stmt.where(DataProduct.domain_id == domain_id)

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search(
        self,
        query: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[DataProduct]:
        """Search data products by name or description."""
        safe_query = sanitize_search_query(query)
        if not safe_query:
            return []

        search_pattern = f"%{safe_query}%"
        stmt = (
            select(DataProduct)
            .options(
                selectinload(DataProduct.domain),
                selectinload(DataProduct.owner),
            )
            .where(
                DataProduct.name.ilike(search_pattern)
                | DataProduct.description.ilike(search_pattern)
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_domain(
        self, domain_id: UUID, offset: int = 0, limit: int = 100
    ) -> Sequence[DataProduct]:
        """Get all data products in a domain."""
        stmt = (
            select(DataProduct)
            .where(DataProduct.domain_id == domain_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_owner(
        self, owner_id: UUID, offset: int = 0, limit: int = 100
    ) -> Sequence[DataProduct]:
        """Get all data products owned by an owner."""
        stmt = (
            select(DataProduct)
            .where(DataProduct.owner_id == owner_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class CapsuleDataProductRepository:
    """Repository for capsule-data product associations (PART_OF edges).
    
    Note: This doesn't inherit from BaseRepository since CapsuleDataProduct
    uses a different base class (Base instead of DABBase).
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: UUID) -> Optional[CapsuleDataProduct]:
        """Get association by ID."""
        return await self.session.get(CapsuleDataProduct, id)

    async def get_association(
        self, capsule_id: UUID, data_product_id: UUID
    ) -> Optional[CapsuleDataProduct]:
        """Get specific capsule-data product association."""
        stmt = select(CapsuleDataProduct).where(
            CapsuleDataProduct.capsule_id == capsule_id,
            CapsuleDataProduct.data_product_id == data_product_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_capsule_to_product(
        self,
        capsule_id: UUID,
        data_product_id: UUID,
        role: str = CapsuleRole.MEMBER,
        meta: Optional[dict] = None,
    ) -> CapsuleDataProduct:
        """Add a capsule to a data product (create PART_OF edge)."""
        association = CapsuleDataProduct(
            capsule_id=capsule_id,
            data_product_id=data_product_id,
            role=role,
            meta=meta or {},
        )
        self.session.add(association)
        await self.session.flush()
        await self.session.refresh(association)
        return association

    async def remove_capsule_from_product(
        self, capsule_id: UUID, data_product_id: UUID
    ) -> bool:
        """Remove a capsule from a data product. Returns True if removed."""
        association = await self.get_association(capsule_id, data_product_id)
        if association:
            await self.session.delete(association)
            await self.session.flush()
            return True
        return False

    async def update_capsule_role(
        self,
        capsule_id: UUID,
        data_product_id: UUID,
        role: str,
    ) -> Optional[CapsuleDataProduct]:
        """Update the role of a capsule in a data product."""
        association = await self.get_association(capsule_id, data_product_id)
        if association:
            association.role = role
            await self.session.flush()
            await self.session.refresh(association)
        return association

    async def get_capsules_in_product(
        self,
        data_product_id: UUID,
        role: Optional[str] = None,
    ) -> Sequence[CapsuleDataProduct]:
        """Get all capsule associations for a data product."""
        stmt = (
            select(CapsuleDataProduct)
            .options(selectinload(CapsuleDataProduct.capsule))
            .where(CapsuleDataProduct.data_product_id == data_product_id)
        )
        if role:
            stmt = stmt.where(CapsuleDataProduct.role == role)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_products_for_capsule(
        self, capsule_id: UUID
    ) -> Sequence[CapsuleDataProduct]:
        """Get all data product associations for a capsule."""
        stmt = (
            select(CapsuleDataProduct)
            .options(selectinload(CapsuleDataProduct.data_product))
            .where(CapsuleDataProduct.capsule_id == capsule_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_capsules_in_product(self, data_product_id: UUID) -> int:
        """Count capsules in a data product."""
        stmt = (
            select(func.count())
            .select_from(CapsuleDataProduct)
            .where(CapsuleDataProduct.data_product_id == data_product_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
