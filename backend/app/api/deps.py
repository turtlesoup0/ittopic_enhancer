"""API dependencies."""
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import get_request_id
from app.db.session import get_db as get_db_session


async def get_db() -> AsyncSession:
    """Get database session."""
    async for session in get_db_session():
        yield session


async def get_current_request_id(request: Request) -> str:
    """
    현재 요청의 Request ID를 가져옵니다.

    Args:
        request: FastAPI 요청 객체

    Returns:
        Request ID 문자열
    """
    return await get_request_id(request)
