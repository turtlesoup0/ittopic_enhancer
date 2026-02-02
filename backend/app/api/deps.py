"""API dependencies."""
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db as get_db_session


async def get_db() -> AsyncSession:
    """Get database session."""
    async for session in get_db_session():
        yield session
