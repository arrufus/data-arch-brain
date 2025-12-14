"""Tag management endpoints for TAGGED_WITH property graph edges."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.api.exceptions import ConflictError, NotFoundError, ValidationError_
from src.database import DbSession
from src.repositories import CapsuleRepository, ColumnRepository
from src.repositories.tag import CapsuleTagRepository, ColumnTagRepository, TagRepository

router = APIRouter(prefix="/tags")


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class TagBase(BaseModel):
    """Base tag schema."""

    name: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(None, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$")
    sensitivity_level: Optional[str] = Field(
        None, pattern=r"^(public|internal|confidential|restricted)$"
    )
    meta: dict = Field(default_factory=dict)


class TagCreate(TagBase):
    """Schema for creating a tag."""

    pass


class TagUpdate(BaseModel):
    """Schema for updating a tag."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(None, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$")
    sensitivity_level: Optional[str] = Field(
        None, pattern=r"^(public|internal|confidential|restricted)$"
    )
    meta: Optional[dict] = None


class TagResponse(BaseModel):
    """Tag response schema."""

    id: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    sensitivity_level: Optional[str] = None
    meta: dict = {}
    created_at: str
    updated_at: str


class TagListResponse(BaseModel):
    """Response for tag list."""

    data: list[TagResponse]
    total: int
    offset: int
    limit: int


class AssociationBase(BaseModel):
    """Base schema for tag associations."""

    added_by: Optional[str] = None
    meta: dict = Field(default_factory=dict)


class CapsuleTagCreate(AssociationBase):
    """Schema for adding a tag to a capsule."""

    tag_id: UUID


class ColumnTagCreate(AssociationBase):
    """Schema for adding a tag to a column."""

    tag_id: UUID


class TagAssociationResponse(BaseModel):
    """Response for tag association."""

    id: str
    tag_id: str
    tag_name: str
    tag_category: Optional[str] = None
    added_by: Optional[str] = None
    added_at: str
    meta: dict = {}


class CapsuleTagResponse(TagAssociationResponse):
    """Response for capsule-tag association."""

    capsule_id: str


class ColumnTagResponse(TagAssociationResponse):
    """Response for column-tag association."""

    column_id: str


class CapsuleWithTagResponse(BaseModel):
    """Capsule summary with tag info."""

    capsule_id: str
    capsule_name: str
    capsule_urn: str
    capsule_type: str
    added_by: Optional[str] = None
    added_at: str


class ColumnWithTagResponse(BaseModel):
    """Column summary with tag info."""

    column_id: str
    column_name: str
    column_urn: str
    capsule_id: str
    capsule_name: str
    added_by: Optional[str] = None
    added_at: str


class CategoryListResponse(BaseModel):
    """Response for category list."""

    categories: list[str]


# ---------------------------------------------------------------------------
# Tag CRUD Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=TagResponse, status_code=201)
async def create_tag(tag_in: TagCreate, db: DbSession) -> TagResponse:
    """Create a new tag."""
    repo = TagRepository(db)

    # Check for duplicate name
    existing = await repo.get_by_name(tag_in.name)
    if existing:
        raise ConflictError(f"Tag with name '{tag_in.name}' already exists")

    from src.models import Tag

    tag = Tag(
        name=tag_in.name,
        category=tag_in.category,
        description=tag_in.description,
        color=tag_in.color,
        sensitivity_level=tag_in.sensitivity_level,
        meta=tag_in.meta,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)

    return TagResponse(
        id=str(tag.id),
        name=tag.name,
        category=tag.category,
        description=tag.description,
        color=tag.color,
        sensitivity_level=tag.sensitivity_level,
        meta=tag.meta or {},
        created_at=tag.created_at.isoformat(),
        updated_at=tag.updated_at.isoformat(),
    )


@router.get("", response_model=TagListResponse)
async def list_tags(
    db: DbSession,
    category: Optional[str] = Query(None, description="Filter by category"),
    sensitivity_level: Optional[str] = Query(
        None, description="Filter by sensitivity level"
    ),
    search: Optional[str] = Query(None, description="Search in name and description"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> TagListResponse:
    """List all tags with optional filtering."""
    repo = TagRepository(db)

    if search:
        tags = await repo.search(search, category=category, offset=offset, limit=limit)
    elif sensitivity_level:
        tags = await repo.get_by_sensitivity_level(
            sensitivity_level, offset=offset, limit=limit
        )
    elif category:
        tags = await repo.get_by_category(category, offset=offset, limit=limit)
    else:
        tags = await repo.get_all(offset=offset, limit=limit)

    return TagListResponse(
        data=[
            TagResponse(
                id=str(tag.id),
                name=tag.name,
                category=tag.category,
                description=tag.description,
                color=tag.color,
                sensitivity_level=tag.sensitivity_level,
                meta=tag.meta or {},
                created_at=tag.created_at.isoformat(),
                updated_at=tag.updated_at.isoformat(),
            )
            for tag in tags
        ],
        total=len(tags),
        offset=offset,
        limit=limit,
    )


@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(db: DbSession) -> CategoryListResponse:
    """List all distinct tag categories."""
    repo = TagRepository(db)
    categories = await repo.get_categories()
    return CategoryListResponse(categories=categories)


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(tag_id: UUID, db: DbSession) -> TagResponse:
    """Get a tag by ID."""
    repo = TagRepository(db)
    tag = await repo.get_by_id(tag_id)
    if not tag:
        raise NotFoundError("Tag", str(tag_id))

    return TagResponse(
        id=str(tag.id),
        name=tag.name,
        category=tag.category,
        description=tag.description,
        color=tag.color,
        sensitivity_level=tag.sensitivity_level,
        meta=tag.meta or {},
        created_at=tag.created_at.isoformat(),
        updated_at=tag.updated_at.isoformat(),
    )


@router.patch("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: UUID, tag_in: TagUpdate, db: DbSession
) -> TagResponse:
    """Update a tag."""
    repo = TagRepository(db)
    tag = await repo.get_by_id(tag_id)
    if not tag:
        raise NotFoundError("Tag", str(tag_id))

    # Check for name conflict if updating name
    if tag_in.name and tag_in.name != tag.name:
        existing = await repo.get_by_name(tag_in.name)
        if existing:
            raise ConflictError(f"Tag with name '{tag_in.name}' already exists")

    # Update fields
    update_data = tag_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tag, field, value)

    await db.commit()
    await db.refresh(tag)

    return TagResponse(
        id=str(tag.id),
        name=tag.name,
        category=tag.category,
        description=tag.description,
        color=tag.color,
        sensitivity_level=tag.sensitivity_level,
        meta=tag.meta or {},
        created_at=tag.created_at.isoformat(),
        updated_at=tag.updated_at.isoformat(),
    )


@router.delete("/{tag_id}", status_code=204)
async def delete_tag(tag_id: UUID, db: DbSession) -> None:
    """Delete a tag (cascades to all associations)."""
    repo = TagRepository(db)
    tag = await repo.get_by_id(tag_id)
    if not tag:
        raise NotFoundError("Tag", str(tag_id))

    await db.delete(tag)
    await db.commit()


# ---------------------------------------------------------------------------
# Capsule Tag Association Endpoints
# ---------------------------------------------------------------------------


@router.get("/{tag_id}/capsules", response_model=list[CapsuleWithTagResponse])
async def get_capsules_with_tag(
    tag_id: UUID,
    db: DbSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[CapsuleWithTagResponse]:
    """Get all capsules that have a specific tag."""
    tag_repo = TagRepository(db)
    tag = await tag_repo.get_by_id(tag_id)
    if not tag:
        raise NotFoundError("Tag", str(tag_id))

    capsule_tag_repo = CapsuleTagRepository(db)
    associations = await capsule_tag_repo.get_capsules_for_tag(
        tag_id, offset=offset, limit=limit
    )

    return [
        CapsuleWithTagResponse(
            capsule_id=str(assoc.capsule.id),
            capsule_name=assoc.capsule.name,
            capsule_urn=assoc.capsule.urn,
            capsule_type=assoc.capsule.capsule_type,
            added_by=assoc.added_by,
            added_at=assoc.added_at.isoformat(),
        )
        for assoc in associations
    ]


@router.get("/{tag_id}/columns", response_model=list[ColumnWithTagResponse])
async def get_columns_with_tag(
    tag_id: UUID,
    db: DbSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[ColumnWithTagResponse]:
    """Get all columns that have a specific tag."""
    tag_repo = TagRepository(db)
    tag = await tag_repo.get_by_id(tag_id)
    if not tag:
        raise NotFoundError("Tag", str(tag_id))

    column_tag_repo = ColumnTagRepository(db)
    associations = await column_tag_repo.get_columns_for_tag(
        tag_id, offset=offset, limit=limit
    )

    return [
        ColumnWithTagResponse(
            column_id=str(assoc.column.id),
            column_name=assoc.column.name,
            column_urn=assoc.column.urn,
            capsule_id=str(assoc.column.capsule_id),
            capsule_name=assoc.column.capsule.name if assoc.column.capsule else "",
            added_by=assoc.added_by,
            added_at=assoc.added_at.isoformat(),
        )
        for assoc in associations
    ]


# ---------------------------------------------------------------------------
# Capsule-specific tag endpoints (mounted at /capsules/{capsule_id}/tags)
# ---------------------------------------------------------------------------

capsule_tags_router = APIRouter()


@capsule_tags_router.get(
    "/capsules/{capsule_id}/tags", response_model=list[TagAssociationResponse]
)
async def get_capsule_tags(capsule_id: UUID, db: DbSession) -> list[TagAssociationResponse]:
    """Get all tags for a capsule."""
    capsule_repo = CapsuleRepository(db)
    capsule = await capsule_repo.get_by_id(capsule_id)
    if not capsule:
        raise NotFoundError("Capsule", str(capsule_id))

    capsule_tag_repo = CapsuleTagRepository(db)
    associations = await capsule_tag_repo.get_tags_for_capsule(capsule_id)

    return [
        TagAssociationResponse(
            id=str(assoc.id),
            tag_id=str(assoc.tag_id),
            tag_name=assoc.tag.name,
            tag_category=assoc.tag.category,
            added_by=assoc.added_by,
            added_at=assoc.added_at.isoformat(),
            meta=assoc.meta or {},
        )
        for assoc in associations
    ]


@capsule_tags_router.post(
    "/capsules/{capsule_id}/tags",
    response_model=CapsuleTagResponse,
    status_code=201,
)
async def add_tag_to_capsule(
    capsule_id: UUID, tag_in: CapsuleTagCreate, db: DbSession
) -> CapsuleTagResponse:
    """Add a tag to a capsule (create TAGGED_WITH edge)."""
    capsule_repo = CapsuleRepository(db)
    capsule = await capsule_repo.get_by_id(capsule_id)
    if not capsule:
        raise NotFoundError("Capsule", str(capsule_id))

    tag_repo = TagRepository(db)
    tag = await tag_repo.get_by_id(tag_in.tag_id)
    if not tag:
        raise NotFoundError("Tag", str(tag_in.tag_id))

    capsule_tag_repo = CapsuleTagRepository(db)

    # Check if association already exists
    existing = await capsule_tag_repo.get_association(capsule_id, tag_in.tag_id)
    if existing:
        raise ConflictError(f"Capsule {capsule_id} already has tag {tag_in.tag_id}")

    association = await capsule_tag_repo.add_tag_to_capsule(
        capsule_id=capsule_id,
        tag_id=tag_in.tag_id,
        added_by=tag_in.added_by,
        meta=tag_in.meta,
    )
    await db.commit()
    await db.refresh(association)

    return CapsuleTagResponse(
        id=str(association.id),
        capsule_id=str(capsule_id),
        tag_id=str(tag.id),
        tag_name=tag.name,
        tag_category=tag.category,
        added_by=association.added_by,
        added_at=association.added_at.isoformat(),
        meta=association.meta or {},
    )


@capsule_tags_router.delete("/capsules/{capsule_id}/tags/{tag_id}", status_code=204)
async def remove_tag_from_capsule(
    capsule_id: UUID, tag_id: UUID, db: DbSession
) -> None:
    """Remove a tag from a capsule (delete TAGGED_WITH edge)."""
    capsule_tag_repo = CapsuleTagRepository(db)
    removed = await capsule_tag_repo.remove_tag_from_capsule(capsule_id, tag_id)
    if not removed:
        raise NotFoundError("CapsuleTag", f"{capsule_id}:{tag_id}")
    await db.commit()


# ---------------------------------------------------------------------------
# Column-specific tag endpoints (mounted at /columns/{column_id}/tags)
# ---------------------------------------------------------------------------

column_tags_router = APIRouter()


@column_tags_router.get(
    "/columns/{column_id}/tags", response_model=list[TagAssociationResponse]
)
async def get_column_tags(column_id: UUID, db: DbSession) -> list[TagAssociationResponse]:
    """Get all tags for a column."""
    column_repo = ColumnRepository(db)
    column = await column_repo.get_by_id(column_id)
    if not column:
        raise NotFoundError("Column", str(column_id))

    column_tag_repo = ColumnTagRepository(db)
    associations = await column_tag_repo.get_tags_for_column(column_id)

    return [
        TagAssociationResponse(
            id=str(assoc.id),
            tag_id=str(assoc.tag_id),
            tag_name=assoc.tag.name,
            tag_category=assoc.tag.category,
            added_by=assoc.added_by,
            added_at=assoc.added_at.isoformat(),
            meta=assoc.meta or {},
        )
        for assoc in associations
    ]


@column_tags_router.post(
    "/columns/{column_id}/tags",
    response_model=ColumnTagResponse,
    status_code=201,
)
async def add_tag_to_column(
    column_id: UUID, tag_in: ColumnTagCreate, db: DbSession
) -> ColumnTagResponse:
    """Add a tag to a column (create TAGGED_WITH edge)."""
    column_repo = ColumnRepository(db)
    column = await column_repo.get_by_id(column_id)
    if not column:
        raise NotFoundError("Column", str(column_id))

    tag_repo = TagRepository(db)
    tag = await tag_repo.get_by_id(tag_in.tag_id)
    if not tag:
        raise NotFoundError("Tag", str(tag_in.tag_id))

    column_tag_repo = ColumnTagRepository(db)

    # Check if association already exists
    existing = await column_tag_repo.get_association(column_id, tag_in.tag_id)
    if existing:
        raise ConflictError(f"Column {column_id} already has tag {tag_in.tag_id}")

    association = await column_tag_repo.add_tag_to_column(
        column_id=column_id,
        tag_id=tag_in.tag_id,
        added_by=tag_in.added_by,
        meta=tag_in.meta,
    )
    await db.commit()
    await db.refresh(association)

    return ColumnTagResponse(
        id=str(association.id),
        column_id=str(column_id),
        tag_id=str(tag.id),
        tag_name=tag.name,
        tag_category=tag.category,
        added_by=association.added_by,
        added_at=association.added_at.isoformat(),
        meta=association.meta or {},
    )


@column_tags_router.delete("/columns/{column_id}/tags/{tag_id}", status_code=204)
async def remove_tag_from_column(
    column_id: UUID, tag_id: UUID, db: DbSession
) -> None:
    """Remove a tag from a column (delete TAGGED_WITH edge)."""
    column_tag_repo = ColumnTagRepository(db)
    removed = await column_tag_repo.remove_tag_from_column(column_id, tag_id)
    if not removed:
        raise NotFoundError("ColumnTag", f"{column_id}:{tag_id}")
    await db.commit()
