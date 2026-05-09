"""
FastAPI application entry point.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import get_settings
from database.mongo import close_mongo, get_db
from database.postgres import create_tables
from middleware.rate_limiter import limiter
from routes import auth, logs, alerts, stats, ws, config, system
from services.pipeline_consumer import PipelineConsumer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("slms.main")
settings = get_settings()

_consumer: PipelineConsumer | None = None
_consumer_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _consumer, _consumer_task

    # Initialise PostgreSQL tables
    await create_tables()
    logger.info("PostgreSQL tables ready.")

    # Ensure admin user exists
    await _ensure_admin()

    # Ensure MongoDB indexes
    await _create_mongo_indexes()

    # Start pipeline consumer
    from routes.ws import broadcast_log
    _consumer = PipelineConsumer(broadcast_fn=broadcast_log)
    _consumer_task = asyncio.create_task(_consumer.run())
    logger.info("Pipeline consumer started.")

    yield

    # Shutdown
    if _consumer_task:
        _consumer_task.cancel()
    await close_mongo()
    logger.info("SLMS backend shutdown complete.")


async def _ensure_admin():
    """Create a default admin account on first run."""
    from sqlalchemy import select
    from database.postgres import AsyncSessionLocal
    from models.db_models import User
    from passlib.context import CryptContext

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == "admin"))
        if not result.scalar_one_or_none():
            admin = User(
                username="admin",
                email="admin@slms.local",
                hashed_password=pwd.hash("admin1234"),
                role="admin",
            )
            session.add(admin)
            await session.commit()
            logger.info("Default admin user created (username=admin, password=admin1234)")


async def _create_mongo_indexes():
    db = get_db()
    await db["logs"].create_index([("timestamp", -1)])
    await db["logs"].create_index([("source", 1)])
    await db["logs"].create_index([("severity", 1)])
    await db["logs"].create_index([("is_anomaly", 1)])
    await db["logs"].create_index([("ip", 1)])
    logger.info("MongoDB indexes ensured.")


# ── App Factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers under /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(ws.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}
