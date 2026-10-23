from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.database import get_db
from app.models.question import Question
from app.services.admin_service import AdminService
from app.web.auth import get_current_admin, verify_csrf_token

router = APIRouter(prefix="/admin/questions", tags=["admin_questions"])

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)


@router.get("", response_class=HTMLResponse)
async def list_questions(
    request: Request,
    q: str = "",
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    query = select(Question).options(
        selectinload(Question.owner), selectinload(Question.test_set)
    )

    if q.strip():
        query = query.where(Question.text.ilike(f"%{q.strip()}%"))

    query = query.order_by(Question.created_at.desc()).limit(100)
    res = await db.execute(query)
    questions = list(res.scalars().all())

    return templates.TemplateResponse(
        request=request,
        name="questions.html",
        context={
            "admin": admin,
            "active_tab": "questions",
            "csrf_token": admin_session.csrf_token,
            "questions": questions,
            "query": q,
            "message": request.query_params.get("message"),
        },
    )


@router.post("/{question_id}/edit")
async def edit_question(
    question_id: str,
    request: Request,
    text: str = Form(...),
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    if not await verify_csrf_token(request, admin_session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")

    stmt = select(Question).where(Question.id == question_id)
    res = await db.execute(stmt)
    question = res.scalars().first()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    old_text = question.text
    new_text = text.strip()[:300]
    question.text = new_text
    await db.commit()

    client_ip = request.client.host if request.client else "unknown"
    await AdminService.record_audit_log(
        session=db,
        admin_id=admin.id,
        action="EDIT_QUESTION",
        target_type="question",
        target_id=question_id,
        details={"before": old_text, "after": new_text},
        ip_address=client_ip,
    )

    return RedirectResponse(
        url="/admin/questions?message=Question+updated+successfully",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{question_id}/delete")
async def delete_question_route(
    question_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin),
):
    admin, admin_session = admin_data
    if not await verify_csrf_token(request, admin_session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF check failed")

    stmt = select(Question).where(Question.id == question_id)
    res = await db.execute(stmt)
    question = res.scalars().first()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    snippet = question.text[:40]
    del_stmt = delete(Question).where(Question.id == question_id)
    await db.execute(del_stmt)
    await db.commit()

    client_ip = request.client.host if request.client else "unknown"
    await AdminService.record_audit_log(
        session=db,
        admin_id=admin.id,
        action="DELETE_QUESTION",
        target_type="question",
        target_id=question_id,
        details={"deleted_snippet": snippet},
        ip_address=client_ip,
    )

    return RedirectResponse(
        url="/admin/questions?message=Question+deleted+successfully",
        status_code=status.HTTP_303_SEE_OTHER,
    )
