from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, delete, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.database import get_db
from app.models.user import User, UserSession
from app.services.admin_service import AdminService
from app.services.auth_service import AuthService
from app.web.auth import get_current_admin, verify_csrf_token

router = APIRouter(prefix="/admin/users", tags=["admin_users"])

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)


@router.get("", response_class=HTMLResponse)
async def list_users(
    request: Request,
    q: str = "",
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    query = select(User)
    if q.strip():
        search_val = f"%{q.strip().lower()}%"
        # Match username or telegram_id
        if q.strip().isdigit():
            query = query.where(
                (func.lower(User.username).like(search_val))
                | (User.telegram_id == int(q.strip()))
            )
        else:
            query = query.where(func.lower(User.username).like(search_val))

    query = query.order_by(User.created_at.desc())
    res = await db.execute(query)
    users = list(res.scalars().all())

    return templates.TemplateResponse(
        request=request,
        name="users.html",
        context={
            "admin": admin,
            "active_tab": "users",
            "csrf_token": admin_session.csrf_token,
            "users": users,
            "query": q,
            "message": request.query_params.get("message"),
        },
    )


@router.get("/{user_id}", response_class=HTMLResponse)
async def user_details(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.groups))
    )
    res = await db.execute(stmt)
    user_obj = res.scalars().first()

    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    return templates.TemplateResponse(
        request=request,
        name="user_detail.html",
        context={
            "admin": admin,
            "active_tab": "users",
            "csrf_token": admin_session.csrf_token,
            "user_obj": user_obj,
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/{user_id}/toggle-block")
async def toggle_block_user(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    if not await verify_csrf_token(request, admin_session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")

    user_obj = await AuthService.get_user_by_id(db, user_id)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    prev_state = user_obj.is_blocked
    user_obj.is_blocked = not prev_state

    # If blocking, invalidate all sessions
    if user_obj.is_blocked:
        await AuthService.revoke_all_user_sessions(db, user_obj.id)

    await db.commit()

    client_ip = request.client.host if request.client else "unknown"
    await AdminService.record_audit_log(
        session=db,
        admin_id=admin.id,
        action="BLOCK_USER" if user_obj.is_blocked else "UNBLOCK_USER",
        target_type="user",
        target_id=user_obj.id,
        details={"username": user_obj.username, "before": prev_state, "after": user_obj.is_blocked},
        ip_address=client_ip,
    )

    return RedirectResponse(
        url=f"/admin/users?message=User+status+updated+successfully",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{user_id}/force-logout")
async def force_logout_user(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    if not await verify_csrf_token(request, admin_session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")

    user_obj = await AuthService.get_user_by_id(db, user_id)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    await AuthService.revoke_all_user_sessions(db, user_obj.id)

    client_ip = request.client.host if request.client else "unknown"
    await AdminService.record_audit_log(
        session=db,
        admin_id=admin.id,
        action="FORCE_LOGOUT_USER",
        target_type="user",
        target_id=user_obj.id,
        details={"username": user_obj.username},
        ip_address=client_ip,
    )

    return RedirectResponse(
        url=f"/admin/users?message=All+sessions+for+{user_obj.username}+revoked",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{user_id}/rebind")
async def rebind_telegram(
    user_id: str,
    request: Request,
    new_telegram_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    if not await verify_csrf_token(request, admin_session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")

    user_obj = await AuthService.get_user_by_id(db, user_id)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    if not new_telegram_id.strip().isdigit():
        return RedirectResponse(
            url=f"/admin/users/{user_id}?error=Invalid+Telegram+ID",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    new_tg = int(new_telegram_id.strip())
    existing = await AuthService.get_user_by_telegram_id(db, new_tg)
    if existing and existing.id != user_obj.id:
        return RedirectResponse(
            url=f"/admin/users/{user_id}?error=Telegram+ID+already+bound+to+another+user",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    old_tg = user_obj.telegram_id
    user_obj.telegram_id = new_tg
    await db.commit()

    client_ip = request.client.host if request.client else "unknown"
    await AdminService.record_audit_log(
        session=db,
        admin_id=admin.id,
        action="REBIND_TELEGRAM",
        target_type="user",
        target_id=user_obj.id,
        details={"before": old_tg, "after": new_tg},
        ip_address=client_ip,
    )

    return RedirectResponse(
        url=f"/admin/users/{user_id}?message=Telegram+ID+successfully+updated",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{user_id}/delete")
async def delete_user_route(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    if not await verify_csrf_token(request, admin_session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")

    user_obj = await AuthService.get_user_by_id(db, user_id)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    username = user_obj.username
    await AuthService.delete_user_account(db, user_id)

    client_ip = request.client.host if request.client else "unknown"
    await AdminService.record_audit_log(
        session=db,
        admin_id=admin.id,
        action="DELETE_USER",
        target_type="user",
        target_id=user_id,
        details={"deleted_username": username},
        ip_address=client_ip,
    )

    return RedirectResponse(
        url=f"/admin/users?message=User+{username}+permanently+deleted",
        status_code=status.HTTP_303_SEE_OTHER,
    )
