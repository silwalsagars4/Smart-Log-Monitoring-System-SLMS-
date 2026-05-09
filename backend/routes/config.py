"""
Dynamic log config routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from database.postgres import get_db_session
from middleware.auth_middleware import require_admin
from models.db_models import LogConfig, User
from pydantic import BaseModel, Field

router = APIRouter(prefix="/config/log-paths", tags=["config"])


class LogConfigCreate(BaseModel):
    label: str = Field(..., max_length=128)
    log_path: str = Field(..., max_length=512)
    collector_type: str = Field(..., max_length=32)
    is_active: bool = True

class LogConfigUpdate(BaseModel):
    label: str | None = None
    log_path: str | None = None
    collector_type: str | None = None
    is_active: bool | None = None

class LogConfigOut(BaseModel):
    id: int
    label: str
    log_path: str
    collector_type: str
    is_active: bool
    created_by: int | None
    
    class Config:
        from_attributes = True


@router.get("", response_model=List[LogConfigOut])
async def list_log_configs(db: AsyncSession = Depends(get_db_session)):
    # Agents call this without auth
    result = await db.execute(select(LogConfig))
    return result.scalars().all()


@router.post("", response_model=LogConfigOut, status_code=status.HTTP_201_CREATED)
async def create_log_config(
    body: LogConfigCreate,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(require_admin),
):
    existing = await db.execute(select(LogConfig).where(LogConfig.log_path == body.log_path))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Log path already exists")

    config = LogConfig(
        label=body.label,
        log_path=body.log_path,
        collector_type=body.collector_type,
        is_active=body.is_active,
        created_by=admin.id,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.patch("/{config_id}", response_model=LogConfigOut)
async def update_log_config(
    config_id: int,
    body: LogConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(LogConfig).where(LogConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    if body.label is not None:
        config.label = body.label
    if body.log_path is not None:
        # Check uniqueness
        if body.log_path != config.log_path:
            existing = await db.execute(select(LogConfig).where(LogConfig.log_path == body.log_path))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Log path already exists")
        config.log_path = body.log_path
    if body.collector_type is not None:
        config.collector_type = body.collector_type
    if body.is_active is not None:
        config.is_active = body.is_active

    await db.commit()
    await db.refresh(config)
    return config


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_log_config(
    config_id: int,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(LogConfig).where(LogConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    # Soft delete
    config.is_active = False
    await db.commit()
