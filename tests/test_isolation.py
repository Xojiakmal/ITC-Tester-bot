import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.group import TelegramGroup
from app.services.question_service import QuestionService
from app.services.group_service import GroupService
from app.services.schedule_service import ScheduleService


@pytest.mark.asyncio
async def test_question_tenant_isolation(
    db_session: AsyncSession, user_a: User, user_b: User
):
    # User A creates a question
    q_a, err = await QuestionService.create_question(
        session=db_session,
        owner_id=user_a.id,
        text="What is Python?",
        options=["Language", "Snake", "Coffee", "Car"],
        correct_option_id=0,
        explanation="Python is a programming language.",
    )
    assert err is None
    assert q_a is not None

    # User B creates a question
    q_b, err = await QuestionService.create_question(
        session=db_session,
        owner_id=user_b.id,
        text="What is HTML?",
        options=["Markup", "Protocol", "Style", "OS"],
        correct_option_id=0,
    )
    assert err is None
    assert q_b is not None

    # User B cannot read User A's question
    fetched_by_b = await QuestionService.get_question_by_id(
        db_session, q_a.id, owner_id=user_b.id
    )
    assert fetched_by_b is None

    # User A can read their own question
    fetched_by_a = await QuestionService.get_question_by_id(
        db_session, q_a.id, owner_id=user_a.id
    )
    assert fetched_by_a is not None
    assert fetched_by_a.id == q_a.id

    # User B cannot delete User A's question
    deleted = await QuestionService.delete_question(
        db_session, q_a.id, owner_id=user_b.id
    )
    assert deleted is False

    # Verify User A's question still exists
    still_exists = await QuestionService.get_question_by_id(
        db_session, q_a.id, owner_id=user_a.id
    )
    assert still_exists is not None

    # User A list sees only their 1 question
    list_a, count_a = await QuestionService.get_user_questions(
        db_session, owner_id=user_a.id
    )
    assert count_a == 1
    assert list_a[0].id == q_a.id

    # User B list sees only their 1 question
    list_b, count_b = await QuestionService.get_user_questions(
        db_session, owner_id=user_b.id
    )
    assert count_b == 1
    assert list_b[0].id == q_b.id


@pytest.mark.asyncio
async def test_group_tenant_isolation(
    db_session: AsyncSession, user_a: User, user_b: User
):
    # Create group for User A
    group_a = TelegramGroup(
        owner_id=user_a.id,
        chat_id=-1001111111,
        title="Alice Study Group",
        chat_type="supergroup",
        is_active=True,
    )
    db_session.add(group_a)
    await db_session.commit()
    await db_session.refresh(group_a)

    # User B cannot access User A's group
    b_access = await GroupService.get_group_by_id(
        db_session, group_a.id, owner_id=user_b.id
    )
    assert b_access is None

    # User B cannot unlink User A's group
    unlinked = await GroupService.unlink_group(
        db_session, group_a.id, owner_id=user_b.id
    )
    assert unlinked is False

    # Group still belongs to User A
    a_access = await GroupService.get_group_by_id(
        db_session, group_a.id, owner_id=user_a.id
    )
    assert a_access is not None
    assert a_access.owner_id == user_a.id

    # User B groups list is empty
    b_groups = await GroupService.get_user_groups(db_session, owner_id=user_b.id)
    assert len(b_groups) == 0


@pytest.mark.asyncio
async def test_schedule_tenant_isolation(
    db_session: AsyncSession, user_a: User, user_b: User
):
    group_a = TelegramGroup(
        owner_id=user_a.id,
        chat_id=-1001111112,
        title="Alice Physics Group",
        chat_type="supergroup",
        is_active=True,
    )
    db_session.add(group_a)
    await db_session.commit()
    await db_session.refresh(group_a)

    sched_a, err = await ScheduleService.create_schedule(
        session=db_session,
        owner=user_a,
        group_id=group_a.id,
        name="Morning Quiz",
        schedule_type="recurring",
        time_of_day="09:00",
        weekdays=[0, 1, 2],
    )
    assert err is None
    assert sched_a is not None

    # User B cannot view User A's schedule
    b_view = await ScheduleService.get_schedule_by_id(
        db_session, sched_a.id, owner_id=user_b.id
    )
    assert b_view is None

    # User B cannot toggle User A's schedule
    toggled = await ScheduleService.toggle_schedule(
        db_session, sched_a.id, owner_id=user_b.id
    )
    assert toggled is None

    # User B cannot delete User A's schedule
    deleted = await ScheduleService.delete_schedule(
        db_session, sched_a.id, owner_id=user_b.id
    )
    assert deleted is False

    # Schedule still intact for User A
    a_view = await ScheduleService.get_schedule_by_id(
        db_session, sched_a.id, owner_id=user_a.id
    )
    assert a_view is not None


@pytest.mark.asyncio
async def test_join_code_ownership_enforcement(
    db_session: AsyncSession, user_a: User, user_b: User
):
    # User A generates a join code
    raw_code, code_id = await GroupService.generate_join_code(db_session, user_a.id)

    # User B attempts to use User A's join code in a group
    success, err_key, grp = await GroupService.link_group_with_code(
        session=db_session,
        raw_code=raw_code,
        sender_telegram_id=user_b.telegram_id,  # User B sending /join
        chat_id=-1002222222,
        chat_title="Bob Group",
        chat_type="supergroup",
    )
    # MUST FAIL with join_not_owner!
    assert success is False
    assert err_key == "join_not_owner"
    assert grp is None

    # User A using their own code succeeds
    success_a, err_a, grp_a = await GroupService.link_group_with_code(
        session=db_session,
        raw_code=raw_code,
        sender_telegram_id=user_a.telegram_id,
        chat_id=-1003333333,
        chat_title="Alice Proper Group",
        chat_type="supergroup",
    )
    assert success_a is True
    assert err_a is None
    assert grp_a.owner_id == user_a.id
