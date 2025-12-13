"""FastAPI dependencies for dependency injection."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for the request."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
