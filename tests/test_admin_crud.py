import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.admin import AdminUser
from app.models.audit import AuditLog
from app.models.user import User
from app.models.group import TelegramGroup
from app.models.question import Question
from app.models.schedule import Schedule
from app.services.admin_service import AdminService
from app.services.question_service import QuestionService
from app.services.schedule_service import ScheduleService
from app.web.app import create_app
from app.config import get_settings

settings = get_settings()


@pytest.mark.asyncio
async def test_admin_crud_full_lifecycle(
    db_session: AsyncSession, admin_fixture: tuple[AdminUser, str], user_a: User
):
    admin, _ = admin_fixture
    raw_token, csrf_token = await AdminService.create_admin_session(db_session, admin.id)

    # Create Group for user_a
    group = TelegramGroup(
        owner_id=user_a.id,
        chat_id=-1001234567,
        title="CRUD Test Group",
        chat_type="supergroup",
        is_active=True,
    )
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)

    # Create Question for user_a
    q, _ = await QuestionService.create_question(
        session=db_session,
        owner_id=user_a.id,
        text="Sample Question?",
        options=["Opt1", "Opt2"],
        correct_option_id=0,
    )

    # Create Schedule for user_a
    sched, _ = await ScheduleService.create_schedule(
        session=db_session,
        owner=user_a,
        group_id=group.id,
        name="CRUD Sched",
        schedule_type="recurring",
        time_of_day="15:00",
        weekdays=[0, 1],
    )

    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set(settings.ADMIN_SESSION_COOKIE_NAME, raw_token)

        # 1. View Users list and search
        res_users = await client.get("/admin/users?q=alice")
        assert res_users.status_code == 200
        assert "user_alice" in res_users.text

        # 2. View User detail
        res_detail = await client.get(f"/admin/users/{user_a.id}")
        assert res_detail.status_code == 200
        assert "user_alice" in res_detail.text
        assert "CRUD Test Group" in res_detail.text

        # 3. Re-bind Telegram ID
        res_rebind = await client.post(
            f"/admin/users/{user_a.id}/rebind",
            data={"csrf_token": csrf_token, "new_telegram_id": "8888888"},
            follow_redirects=False,
        )
        assert res_rebind.status_code == 303
        await db_session.refresh(user_a)
        assert user_a.telegram_id == 8888888

        # 4. View Groups list
        res_groups = await client.get("/admin/groups")
        assert res_groups.status_code == 200
        assert "CRUD Test Group" in res_groups.text

        # 5. Unlink Group
        res_unl = await client.post(
            f"/admin/groups/{group.id}/unlink",
            data={"csrf_token": csrf_token},
            follow_redirects=False,
        )
        assert res_unl.status_code == 303
        await db_session.refresh(group)
        assert group.owner_id is None

        # 6. Edit Question
        res_edit_q = await client.post(
            f"/admin/questions/{q.id}/edit",
            data={"csrf_token": csrf_token, "text": "Updated Question Text?"},
            follow_redirects=False,
        )
        assert res_edit_q.status_code == 303
        await db_session.refresh(q)
        assert q.text == "Updated Question Text?"

        # 7. Toggle Schedule
        res_tog_sched = await client.post(
            f"/admin/schedules/{sched.id}/toggle",
            data={"csrf_token": csrf_token},
            follow_redirects=False,
        )
        assert res_tog_sched.status_code == 303
        await db_session.refresh(sched)
        assert sched.is_paused is True

        # 8. Delete Schedule
        res_del_sched = await client.post(
            f"/admin/schedules/{sched.id}/delete",
            data={"csrf_token": csrf_token},
            follow_redirects=False,
        )
        assert res_del_sched.status_code == 303

        # 9. View Audit logs
        res_audit = await client.get("/admin/audit")
        assert res_audit.status_code == 200
        assert "REBIND_TELEGRAM" in res_audit.text
        assert "UNLINK_GROUP" in res_audit.text
        assert "EDIT_QUESTION" in res_audit.text
        assert "PAUSE_SCHEDULE" in res_audit.text
        assert "DELETE_SCHEDULE" in res_audit.text
