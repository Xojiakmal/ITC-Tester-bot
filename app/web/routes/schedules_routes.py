from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.database import get_db
from app.models.schedule import Schedule
from app.services.admin_service import AdminService
from app.web.auth import get_current_admin, verify_csrf_token

router = APIRouter(prefix="/admin/schedules", tags=["admin_schedules"])

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)


@router.get("", response_class=HTMLResponse)
async def list_schedules(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    stmt = (
        select(Schedule)
        .options(
            selectinload(Schedule.owner),
            selectinload(Schedule.group),
            selectinload(Schedule.test_set),
        )
        .order_by(Schedule.created_at.desc())
    )
    res = await db.execute(stmt)
    schedules = list(res.scalars().all())

    return templates.TemplateResponse(
        request=request,
        name="schedules.html",
        context={
            "admin": admin,
            "active_tab": "schedules",
            "csrf_token": admin_session.csrf_token,
            "schedules": schedules,
            "message": request.query_params.get("message"),
        },
    )


@router.post("/{schedule_id}/toggle")
async def toggle_schedule_route(
    schedule_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    if not await verify_csrf_token(request, admin_session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")

    stmt = select(Schedule).where(Schedule.id == schedule_id)
    res = await db.execute(stmt)
    sched = res.scalars().first()

    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    old_state = sched.is_paused
    sched.is_paused = not old_state
    await db.commit()

    client_ip = request.client.host if request.client else "unknown"
    await AdminService.record_audit_log(
        session=db,
        admin_id=admin.id,
        action="PAUSE_SCHEDULE" if sched.is_paused else "RESUME_SCHEDULE",
        target_type="schedule",
        target_id=schedule_id,
        details={"name": sched.name, "before": old_state, "after": sched.is_paused},
        ip_address=client_ip,
    )

    action_text = "paused" if sched.is_paused else "resumed"
    return RedirectResponse(
        url=f"/admin/schedules?message=Schedule+{action_text}+successfully",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{schedule_id}/delete")
async def delete_schedule_route(
    schedule_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    if not await verify_csrf_token(request, admin_session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")

    stmt = select(Schedule).where(Schedule.id == schedule_id)
    res = await db.execute(stmt)
    sched = res.scalars().first()

    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    name = sched.name
    del_stmt = delete(Schedule).where(Schedule.id == schedule_id)
    await db.execute(del_stmt)
    await db.commit()

    client_ip = request.client.host if request.client else "unknown"
    await AdminService.record_audit_log(
        session=db,
        admin_id=admin.id,
        action="DELETE_SCHEDULE",
        target_type="schedule",
        target_id=schedule_id,
        details={"name": name},
        ip_address=client_ip,
    )

    return RedirectResponse(
        url="/admin/schedules?message=Schedule+deleted+successfully",
        status_code=status.HTTP_303_SEE_OTHER,
    )
