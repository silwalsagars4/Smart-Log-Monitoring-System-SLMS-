"""
PostgreSQL async client via SQLAlchemy 2.0 + asyncpg.
Stores users and structured alerts.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.POSTGRES_URL,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
