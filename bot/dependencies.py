from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from bot.core.database import get_async_session


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async database session as a dependency.

    Yields:
        AsyncSession: An active SQLAlchemy async session.

    Ensures:
        The session is properly closed after use.
    """
    async with get_async_session() as session:
        yield session
