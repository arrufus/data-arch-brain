"""Base model definitions and common mixins."""

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text, TypeDecorator, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class JSONType(TypeDecorator):
    """A JSON type that works with both PostgreSQL (JSONB) and SQLite (TEXT).

    This type uses JSONB on PostgreSQL for efficient JSON operations,
    and falls back to TEXT with JSON serialization on other databases
    like SQLite (used in tests).
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        """Load the appropriate implementation for the database dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        """Process value before sending to database."""
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        """Process value from database."""
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        if isinstance(value, str):
            return json.loads(value)
        return value


class UUIDType(TypeDecorator):
    """A UUID type that works with both PostgreSQL and SQLite.

    Uses native UUID on PostgreSQL and stores as string on SQLite.
    """

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        """Load the appropriate implementation for the database dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        """Process value before sending to database."""
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        """Process value from database."""
        if value is None:
            return value
        if isinstance(value, UUID):
            return value
        return UUID(value)


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """Mixin for UUID primary key."""

    id: Mapped[UUID] = mapped_column(
        UUIDType(),
        primary_key=True,
        default=uuid4,
    )


class URNMixin:
    """Mixin for URN-based entities."""

    urn: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        nullable=False,
        index=True,
    )


class MetadataMixin:
    """Mixin for entities with JSONB metadata."""

    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONType(),
        default=dict,
        nullable=False,
    )
    tags: Mapped[list[str]] = mapped_column(
        JSONType(),
        default=list,
        nullable=False,
    )


import os

# Schema name for all DCS tables - disabled for SQLite (tests)
# Use None for SQLite (no schema support) or "dcs" for PostgreSQL
_db_url = os.environ.get("DATABASE_URL", "")
DCS_SCHEMA: str | None = None if "sqlite" in _db_url else "dcs"


def get_schema_table_args() -> dict:
    """Get table args with schema if not SQLite."""
    if DCS_SCHEMA:
        return {"schema": DCS_SCHEMA}
    return {}


def fk_ref(table_column: str) -> str:
    """Get a foreign key reference with schema prefix if applicable.

    Args:
        table_column: The table.column reference (e.g., "capsules.id")

    Returns:
        Schema-prefixed reference for PostgreSQL, or just table.column for SQLite.
    """
    if DCS_SCHEMA:
        return f"{DCS_SCHEMA}.{table_column}"
    return table_column


class DCSBase(Base, UUIDMixin, TimestampMixin):
    """Base class for all DCS models with common columns."""

    __abstract__ = True
    __table_args__ = get_schema_table_args()
