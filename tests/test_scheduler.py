import asyncio
from datetime import timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.user import User
from app.models.group import TelegramGroup
from app.models.schedule import Schedule, ScheduleRun
from app.models.base import utc_now
from app.services.schedule_service import ScheduleService
from app.services.question_service import QuestionService


@pytest.mark.asyncio
async def test_scheduler_atomic_claim(db_session: AsyncSession, user_a: User):
    group = TelegramGroup(
        owner_id=user_a.id,
        chat_id=-1008888888,
        title="Atomic Test Group",
        chat_type="supergroup",
        is_active=True,
    )
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)

    sched, _ = await ScheduleService.create_schedule(
        session=db_session,
        owner=user_a,
        group_id=group.id,
        name="Atomic Run Schedule",
        schedule_type="recurring",
        time_of_day="10:00",
        weekdays=[0, 1, 2, 3, 4, 5, 6],
    )

    # Fetch the pending run
    stmt = select(ScheduleRun).where(
        ScheduleRun.schedule_id == sched.id, ScheduleRun.status == "PENDING"
    )
    res = await db_session.execute(stmt)
    run_obj = res.scalars().first()
    assert run_obj is not None

    # Simulate two workers concurrently attempting atomic claim
    # Worker 1
    claim1 = await db_session.execute(
        update(ScheduleRun)
        .where(ScheduleRun.id == run_obj.id, ScheduleRun.status == "PENDING")
        .values(status="PROCESSING", locked_at=utc_now())
    )
    await db_session.commit()

    # Worker 2 attempts same claim
    claim2 = await db_session.execute(
        update(ScheduleRun)
        .where(ScheduleRun.id == run_obj.id, ScheduleRun.status == "PENDING")
        .values(status="PROCESSING", locked_at=utc_now())
    )
    await db_session.commit()

    # Exactly ONE worker claimed successfully!
    assert claim1.rowcount == 1
    assert claim2.rowcount == 0


@pytest.mark.asyncio
async def test_scheduler_questions_without_repeats(
    db_session: AsyncSession, user_a: User
):
    group = TelegramGroup(
        owner_id=user_a.id,
        chat_id=-1009999999,
        title="Quiz Group",
        chat_type="supergroup",
        is_active=True,
    )
    db_session.add(group)
    await db_session.commit()

    # Create 3 questions for user_a
    q1, _ = await QuestionService.create_question(
        db_session, user_a.id, "Question 1?", ["A", "B"], 0
    )
    q2, _ = await QuestionService.create_question(
        db_session, user_a.id, "Question 2?", ["A", "B"], 0
    )
    q3, _ = await QuestionService.create_question(
        db_session, user_a.id, "Question 3?", ["A", "B"], 0
    )

    sched, _ = await ScheduleService.create_schedule(
        session=db_session,
        owner=user_a,
        group_id=group.id,
        name="No Repeat Sched",
        schedule_type="recurring",
        time_of_day="12:00",
        questions_per_run=1,
        order_mode="sequential",
        weekdays=[0, 1, 2, 3, 4],
    )

    # First run picks 1 question
    run_1_questions = await ScheduleService.select_questions_for_run(db_session, sched)
    assert len(run_1_questions) == 1
    first_id = run_1_questions[0].id

    # Second run picks another question (different from first!)
    run_2_questions = await ScheduleService.select_questions_for_run(db_session, sched)
    assert len(run_2_questions) == 1
    second_id = run_2_questions[0].id
    assert second_id != first_id

    # Third run picks the last remaining question
    run_3_questions = await ScheduleService.select_questions_for_run(db_session, sched)
    assert len(run_3_questions) == 1
    third_id = run_3_questions[0].id
    assert third_id != first_id and third_id != second_id

    # Fourth run: pool is now exhausted, so it cleanly resets history and selects fresh
    run_4_questions = await ScheduleService.select_questions_for_run(db_session, sched)
    assert len(run_4_questions) == 1


def test_shuffle_poll_options_preserves_correct_answer():
    from app.services.scheduler_engine import shuffle_poll_options

    options = ["A", "B", "C", "D"]
    for _ in range(100):
        shuffled, new_correct_id = shuffle_poll_options(options, 2)
        # Same set of options, only reordered
        assert sorted(shuffled) == options
        # The correct answer still points at the same text ("C")
        assert shuffled[new_correct_id] == "C"
        assert 0 <= new_correct_id < len(options)
        # The original list must not be mutated in place
        assert options == ["A", "B", "C", "D"]


def test_shuffle_poll_options_can_reorder():
    from app.services.scheduler_engine import shuffle_poll_options

    options = ["A", "B", "C", "D", "E"]
    seen = set()
    for _ in range(200):
        shuffled, new_correct_id = shuffle_poll_options(options, 0)
        assert shuffled[new_correct_id] == "A"
        seen.add(tuple(shuffled))
    # Over many shuffles we should observe at least one reordering
    assert len(seen) > 1
