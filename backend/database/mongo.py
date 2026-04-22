"""
MongoDB async client via Motor.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from config import get_settings

_client: AsyncIOMotorClient | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncIOMotorClient(settings.MONGO_URL, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    return get_mongo_client()["slms"]


async def close_mongo():
    global _client
    if _client:
        _client.close()
        _client = None
