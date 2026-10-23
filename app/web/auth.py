from typing import Tuple, Optional
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.admin_service import AdminService
from app.models.admin import AdminUser, AdminSession
from app.config import get_settings

settings = get_settings()


async def get_current_admin_optional(
    request: Request, db: AsyncSession = Depends(get_db)
) -> Tuple[Optional[AdminUser], Optional[AdminSession]]:
    token = request.cookies.get(settings.ADMIN_SESSION_COOKIE_NAME)
    if not token:
        return None, None
    admin, admin_session = await AdminService.validate_admin_session(db, token)
    return admin, admin_session


async def get_current_admin(
    request: Request, db: AsyncSession = Depends(get_db)
) -> Tuple[AdminUser, AdminSession]:
    admin, admin_session = await get_current_admin_optional(request, db)
    if not admin or not admin_session:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )
    return admin, admin_session


async def verify_csrf_token(request: Request, admin_session: AdminSession) -> bool:
    """Validate CSRF token sent via form body or header against active admin session."""
    # Check header
    header_token = request.headers.get("X-CSRF-Token")
    if header_token and header_token == admin_session.csrf_token:
        return True

    # Check form body
    form = await request.form()
    form_token = form.get("csrf_token")
    if form_token and form_token == admin_session.csrf_token:
        return True

    return False
