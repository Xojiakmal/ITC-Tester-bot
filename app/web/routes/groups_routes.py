from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.database import get_db
from app.models.group import TelegramGroup
from app.services.admin_service import AdminService
from app.services.group_service import GroupService
from app.web.auth import get_current_admin, verify_csrf_token

router = APIRouter(prefix="/admin/groups", tags=["admin_groups"])

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)


@router.get("", response_class=HTMLResponse)
async def list_groups(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    stmt = select(TelegramGroup).options(selectinload(TelegramGroup.owner)).order_by(TelegramGroup.created_at.desc())
    res = await db.execute(stmt)
    groups = list(res.scalars().all())

    return templates.TemplateResponse(
        request=request,
        name="groups.html",
        context={
            "admin": admin,
            "active_tab": "groups",
            "csrf_token": admin_session.csrf_token,
            "groups": groups,
            "message": request.query_params.get("message"),
        },
    )


@router.post("/{group_id}/unlink")
async def admin_unlink_group(
    group_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    if not await verify_csrf_token(request, admin_session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")

    stmt = select(TelegramGroup).where(TelegramGroup.id == group_id)
    res = await db.execute(stmt)
    group = res.scalars().first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    old_owner_id = group.owner_id
    group.owner_id = None
    group.linked_at = None
    await db.commit()

    client_ip = request.client.host if request.client else "unknown"
    await AdminService.record_audit_log(
        session=db,
        admin_id=admin.id,
        action="UNLINK_GROUP",
        target_type="group",
        target_id=group.id,
        details={"group_title": group.title, "previous_owner_id": old_owner_id},
        ip_address=client_ip,
    )

    return RedirectResponse(
        url="/admin/groups?message=Group+successfully+unlinked",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{group_id}/delete")
async def admin_delete_group(
    group_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    if not await verify_csrf_token(request, admin_session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")

    stmt = select(TelegramGroup).where(TelegramGroup.id == group_id)
    res = await db.execute(stmt)
    group = res.scalars().first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    title = group.title
    del_stmt = delete(TelegramGroup).where(TelegramGroup.id == group_id)
    await db.execute(del_stmt)
    await db.commit()

    client_ip = request.client.host if request.client else "unknown"
    await AdminService.record_audit_log(
        session=db,
        admin_id=admin.id,
        action="DELETE_GROUP",
        target_type="group",
        target_id=group_id,
        details={"group_title": title},
        ip_address=client_ip,
    )

    return RedirectResponse(
        url="/admin/groups?message=Group+deleted+successfully",
        status_code=status.HTTP_303_SEE_OTHER,
    )
