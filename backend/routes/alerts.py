







"""
Alert routes — list, acknowledge, delete.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.postgres import get_db_session
from middleware.auth_middleware import get_current_user, require_admin
from models.db_models import Alert, User
from models.schemas import AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    severity: str | None = Query(None),
    acknowledged: bool | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Alert)
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    if acknowledged is not None:
        stmt = stmt.where(Alert.acknowledged == acknowledged)
    stmt = stmt.order_by(desc(Alert.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/{alert_id}/acknowledge", response_model=AlertOut)
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = True
    await db.commit()
    await db.refresh(alert)
    return alert


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.delete(alert)
    await db.commit()
