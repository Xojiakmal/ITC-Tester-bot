from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.database import get_db
from app.models.audit import AuditLog
from app.web.auth import get_current_admin

router = APIRouter(prefix="/admin/audit", tags=["admin_audit"])

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)


@router.get("", response_class=HTMLResponse)
async def list_audit_logs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    stmt = (
        select(AuditLog)
        .options(selectinload(AuditLog.admin))
        .order_by(AuditLog.created_at.desc())
        .limit(200)
    )
    res = await db.execute(stmt)
    logs = list(res.scalars().all())

    return templates.TemplateResponse(
        request=request,
        name="audit_logs.html",
        context={
            "admin": admin,
            "active_tab": "audit",
            "csrf_token": admin_session.csrf_token,
            "logs": logs,
        },
    )
