# app/database.py
from sqlalchemy.ext.asyncio import AsyncSession
from models import Session
import logging

logger = logging.getLogger(__name__)


async def get_db_session() -> AsyncSession:
    logger.info("Creating database session")
    async with Session() as session:
        try:
            logger.info("Yielding session")
            yield session
        finally:
            logger.info("Closing session")
            await session.close()
