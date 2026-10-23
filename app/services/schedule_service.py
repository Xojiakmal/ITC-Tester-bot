import random
from datetime import datetime, timedelta, time, date, timezone
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo
from sqlalchemy import select, update, func, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.schedule import Schedule, ScheduleSentQuestion, ScheduleRun, PollSendLog
from app.models.group import TelegramGroup
from app.models.question import Question, TestSet
from app.models.user import User
from app.models.base import utc_now
from app.config import get_settings

settings = get_settings()


def compute_next_run_at(
    schedule_type: str,
    time_of_day: str,
    tz_name: str,
    weekdays: Optional[List[int]] = None,
    one_time_date: Optional[str] = None,
    after_utc: Optional[datetime] = None,
) -> Optional[datetime]:
    """Compute the next run time in UTC based on owner's timezone."""
    try:
        user_tz = ZoneInfo(tz_name)
    except Exception:
        user_tz = ZoneInfo("Asia/Tashkent")

    now_utc = after_utc or utc_now()
    now_local = now_utc.astimezone(user_tz)

    try:
        hour, minute = map(int, time_of_day.split(":"))
        run_time = time(hour=hour, minute=minute)
    except Exception:
        return None

    if schedule_type == "one_time":
        if not one_time_date:
            return None
        try:
            target_date = datetime.strptime(one_time_date, "%Y-%m-%d").date()
            local_dt = datetime.combine(target_date, run_time, tzinfo=user_tz)
            utc_dt = local_dt.astimezone(timezone.utc)
            return utc_dt if utc_dt > now_utc else None
        except Exception:
            return None

    elif schedule_type == "recurring":
        if not weekdays:
            return None

        # Check next 14 days
        for day_offset in range(14):
            candidate_date = now_local.date() + timedelta(days=day_offset)
            if candidate_date.weekday() in weekdays:
                local_dt = datetime.combine(candidate_date, run_time, tzinfo=user_tz)
                utc_dt = local_dt.astimezone(timezone.utc)
                if utc_dt > now_utc:
                    return utc_dt
        return None

    return None


class ScheduleService:
    @staticmethod
    async def count_user_schedules(session: AsyncSession, owner_id: str) -> int:
        stmt = select(func.count(Schedule.id)).where(Schedule.owner_id == owner_id)
        result = await session.execute(stmt)
        return result.scalar_one() or 0

    @staticmethod
    async def get_user_schedules(session: AsyncSession, owner_id: str) -> List[Schedule]:
        stmt = (
            select(Schedule)
            .where(Schedule.owner_id == owner_id)
            .options(selectinload(Schedule.group), selectinload(Schedule.test_set))
            .order_by(Schedule.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_schedule_by_id(
        session: AsyncSession, schedule_id: str, owner_id: str
    ) -> Optional[Schedule]:
        """Tenant-isolated schedule fetch."""
        stmt = (
            select(Schedule)
            .where(Schedule.id == schedule_id, Schedule.owner_id == owner_id)
            .options(selectinload(Schedule.group), selectinload(Schedule.test_set))
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def create_schedule(
        session: AsyncSession,
        owner: User,
        group_id: str,
        name: str,
        schedule_type: str,
        time_of_day: str,
        questions_per_run: int = 1,
        order_mode: str = "random",
        test_set_id: Optional[str] = None,
        weekdays: Optional[List[int]] = None,
        one_time_date: Optional[str] = None,
    ) -> Tuple[Optional[Schedule], Optional[str]]:
        # Verify quotas
        count = await ScheduleService.count_user_schedules(session, owner.id)
        if count >= settings.MAX_SCHEDULES_PER_USER:
            return None, "schedule_quota_exceeded"

        # Verify group belongs to owner
        group_stmt = select(TelegramGroup).where(
            TelegramGroup.id == group_id, TelegramGroup.owner_id == owner.id
        )
        group_res = await session.execute(group_stmt)
        group = group_res.scalars().first()
        if not group:
            return None, "Guruh topilmadi."

        # Verify test set if given
        if test_set_id:
            set_stmt = select(TestSet).where(
                TestSet.id == test_set_id, TestSet.owner_id == owner.id
            )
            set_res = await session.execute(set_stmt)
            if not set_res.scalars().first():
                test_set_id = None

        # Compute next run time
        next_run = compute_next_run_at(
            schedule_type=schedule_type,
            time_of_day=time_of_day,
            tz_name=owner.timezone,
            weekdays=weekdays,
            one_time_date=one_time_date,
        )

        schedule = Schedule(
            owner_id=owner.id,
            group_id=group.id,
            test_set_id=test_set_id,
            name=name.strip()[:100],
            schedule_type=schedule_type,
            weekdays=weekdays,
            time_of_day=time_of_day,
            one_time_date=one_time_date,
            questions_per_run=max(1, min(10, questions_per_run)),
            order_mode=order_mode,
            is_paused=False,
            next_run_at=next_run,
        )
        session.add(schedule)
        await session.flush()

        # If next run was computed, create initial pending ScheduleRun
        if next_run:
            initial_run = ScheduleRun(
                schedule_id=schedule.id,
                planned_run_at=next_run,
                status="PENDING",
            )
            session.add(initial_run)

        await session.commit()
        await session.refresh(schedule)
        return schedule, None

    @staticmethod
    async def toggle_schedule(
        session: AsyncSession, schedule_id: str, owner_id: str
    ) -> Optional[Schedule]:
        schedule = await ScheduleService.get_schedule_by_id(session, schedule_id, owner_id)
        if not schedule:
            return None

        schedule.is_paused = not schedule.is_paused
        await session.commit()
        return schedule

    @staticmethod
    async def delete_schedule(
        session: AsyncSession, schedule_id: str, owner_id: str
    ) -> bool:
        stmt = delete(Schedule).where(
            Schedule.id == schedule_id, Schedule.owner_id == owner_id
        )
        res = await session.execute(stmt)
        await session.commit()
        return res.rowcount > 0

    @staticmethod
    async def select_questions_for_run(
        session: AsyncSession, schedule: Schedule
    ) -> List[Question]:
        """Pick N questions without repeats until the pool is exhausted (or sequential)."""
        # Base pool of available questions owned by user
        pool_query = select(Question).where(Question.owner_id == schedule.owner_id)
        if schedule.test_set_id:
            pool_query = pool_query.where(Question.test_set_id == schedule.test_set_id)

        all_questions_res = await session.execute(pool_query)
        all_questions = list(all_questions_res.scalars().all())

        if not all_questions:
            return []

        # Find sent question IDs for this schedule
        sent_stmt = select(ScheduleSentQuestion.question_id).where(
            ScheduleSentQuestion.schedule_id == schedule.id
        )
        sent_res = await session.execute(sent_stmt)
        sent_ids = set(sent_res.scalars().all())

        # Unsent candidates
        candidates = [q for q in all_questions if q.id not in sent_ids]

        # If pool exhausted, reset sent questions for this schedule and use full pool
        if len(candidates) < schedule.questions_per_run:
            reset_stmt = delete(ScheduleSentQuestion).where(
                ScheduleSentQuestion.schedule_id == schedule.id
            )
            await session.execute(reset_stmt)
            await session.commit()
            candidates = all_questions

        needed = min(schedule.questions_per_run, len(candidates))
        if schedule.order_mode == "sequential":
            # Sort by creation time
            candidates.sort(key=lambda x: x.created_at)
            selected = candidates[:needed]
        else:
            selected = random.sample(candidates, needed)

        # Record as sent
        for q in selected:
            sent_record = ScheduleSentQuestion(
                schedule_id=schedule.id,
                question_id=q.id,
                sent_at=utc_now(),
            )
            session.add(sent_record)
        await session.commit()

        return selected
