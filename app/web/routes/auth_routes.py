from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.database import get_db
from app.services.admin_service import AdminService
from app.services.auth_service import AuthService
from app.config import get_settings
from app.web.auth import get_current_admin_optional, verify_csrf_token

router = APIRouter(prefix="/admin", tags=["admin_auth"])
settings = get_settings()

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin_optional),
):
    admin, _ = admin_data
    if admin:
        return RedirectResponse(url="/admin/", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"admin": None, "error": None},
    )


@router.post("/login", response_class=HTMLResponse)
async def handle_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    totp_code: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    ip_key = f"admin:ip:{client_ip}"
    user_key = f"admin:user:{username.strip().lower()}"

    # Rate limiting on admin login
    is_ip_locked, rem_ip = await AuthService.check_login_throttled(db, ip_key)
    is_user_locked, rem_user = await AuthService.check_login_throttled(db, user_key)

    if is_ip_locked or is_user_locked:
        wait_sec = max(rem_ip, rem_user)
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "admin": None,
                "error": f"Haddan tashqari ko'p urinish. Iltimos {wait_sec} soniya kuting.",
            },
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    admin, err = await AdminService.authenticate_admin(db, username, password, totp_code)
    if err or not admin:
        await AuthService.record_login_failure(db, ip_key)
        await AuthService.record_login_failure(db, user_key)
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "admin": None,
                "error": err or "Noto'g'ri login yoki parol.",
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Clear throttles
    await AuthService.record_login_success(db, ip_key)
    await AuthService.record_login_success(db, user_key)

    user_agent = request.headers.get("User-Agent")
    raw_token, _ = await AdminService.create_admin_session(
        db, admin.id, ip_address=client_ip, user_agent=user_agent
    )

    await AdminService.record_audit_log(
        session=db,
        admin_id=admin.id,
        action="ADMIN_LOGIN",
        target_type="admin",
        target_id=admin.id,
        details={"ip": client_ip, "user_agent": user_agent},
        ip_address=client_ip,
    )

    response = RedirectResponse(url="/admin/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=settings.ADMIN_SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=12 * 3600,
    )
    return response


@router.post("/logout")
async def handle_logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin_optional),
):
    admin, admin_session = admin_data
    if admin_session:
        # Verify CSRF
        if not await verify_csrf_token(request, admin_session):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed.")

        raw_token = request.cookies.get(settings.ADMIN_SESSION_COOKIE_NAME, "")
        await AdminService.revoke_admin_session(db, raw_token)

        client_ip = request.client.host if request.client else "unknown"
        await AdminService.record_audit_log(
            session=db,
            admin_id=admin.id,
            action="ADMIN_LOGOUT",
            target_type="admin",
            target_id=admin.id,
            ip_address=client_ip,
        )

    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(settings.ADMIN_SESSION_COOKIE_NAME)
    return response
