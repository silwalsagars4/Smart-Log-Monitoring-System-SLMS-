







"""
Alert routes — list, acknowledge, delete.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.postgres import get_db_session
from middleware.auth_middleware import get_current_user, require_admin, require_analyst_or_above, require_any_authenticated
from models.db_models import Alert, User, AlertInteraction
from models.schemas import AlertOut, AlertInteractionOut, CommentCreate

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    severity: str | None = Query(None),
    acknowledged: bool | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_any_authenticated),
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
    current_user: User = Depends(require_analyst_or_above),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = True
    interaction = AlertInteraction(
        alert_id=alert.id,
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role,
        action="acknowledge"
    )
    db.add(interaction)
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


@router.post("/{alert_id}/comment", response_model=AlertInteractionOut)
async def add_comment(
    alert_id: int,
    body: CommentCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_analyst_or_above),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.severity not in ("high", "disaster"):
        raise HTTPException(status_code=400, detail="Comments only allowed on High/Disaster alerts")
        
    interaction = AlertInteraction(
        alert_id=alert.id,
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role,
        action="comment",
        message=body.message
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)
    return interaction


@router.get("/{alert_id}/interactions", response_model=list[AlertInteractionOut])
async def list_interactions(
    alert_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_any_authenticated),
):
    result = await db.execute(
        select(AlertInteraction)
        .where(AlertInteraction.alert_id == alert_id)
        .order_by(AlertInteraction.timestamp)
    )
    return result.scalars().all()
