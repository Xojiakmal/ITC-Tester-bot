from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.database import get_db
from app.services.admin_service import AdminService
from app.models.audit import AuditLog
from app.web.auth import get_current_admin

router = APIRouter(prefix="/admin", tags=["admin_dashboard"])

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)


@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    stats = await AdminService.get_dashboard_stats(db)

    # Get 5 recent audit logs
    stmt = (
        select(AuditLog)
        .options(selectinload(AuditLog.admin))
        .order_by(AuditLog.created_at.desc())
        .limit(5)
    )
    result = await db.execute(stmt)
    recent_logs = list(result.scalars().all())

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "admin": admin,
            "active_tab": "dashboard",
            "csrf_token": admin_session.csrf_token,
            "stats": stats,
            "recent_logs": recent_logs,
        },
    )
