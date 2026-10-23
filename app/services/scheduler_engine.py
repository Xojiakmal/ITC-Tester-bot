import asyncio
import logging
import random
from datetime import timedelta
from typing import Optional
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.schedule import Schedule, ScheduleRun, PollSendLog
from app.models.group import TelegramGroup
from app.models.user import User
from app.models.base import utc_now, ensure_utc
from app.services.schedule_service import ScheduleService, compute_next_run_at
from app.locales.uz import t
from app.config import get_settings

logger = logging.getLogger("scheduler_engine")
settings = get_settings()


def shuffle_poll_options(options: list[str], correct_option_id: int) -> tuple[list[str], int]:
    """Return a shuffled copy of the poll options with a remapped correct index.

    Telegram quiz polls reference the correct answer by its position
    (``correct_option_id``), so when the option order is randomized the index of
    the correct answer must be moved to its new position as well.
    """
    order = list(range(len(options)))
    random.shuffle(order)
    shuffled_options = [options[i] for i in order]
    new_correct_option_id = (
        order.index(correct_option_id) if correct_option_id in order else correct_option_id
    )
    return shuffled_options, new_correct_option_id


class SchedulerEngine:
    def __init__(self, bot: Bot):
        self.bot = bot
        self._is_running = False
        self._worker_task: Optional[asyncio.Task] = None

    def start(self):
        if not self._is_running:
            self._is_running = True
            self._worker_task = asyncio.create_task(self._run_loop())
            logger.info("Scheduler engine started.")

    async def stop(self):
        self._is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            logger.info("Scheduler engine stopped.")

    async def _run_loop(self):
        while self._is_running:
            try:
                await self.tick()
            except Exception as e:
                logger.error(f"Error in scheduler tick: {e}", exc_info=True)
            await asyncio.sleep(settings.SCHEDULER_INTERVAL_SECONDS)

    async def tick(self):
        """Single tick: find due runs, claim atomically, and process."""
        now = utc_now()
        grace_threshold = now - timedelta(seconds=settings.SCHEDULER_GRACE_WINDOW_SECONDS)

        async with AsyncSessionLocal() as session:
            # First, check any uncreated pending runs for active schedules whose next_run_at is due
            active_schedules_stmt = select(Schedule).where(
                Schedule.is_paused.is_(False),
                Schedule.next_run_at.is_not(None),
                Schedule.next_run_at <= now,
            )
            sched_res = await session.execute(active_schedules_stmt)
            active_schedules = sched_res.scalars().all()

            for sched in active_schedules:
                # Check if there is already a PENDING or PROCESSING run
                existing_run_stmt = select(ScheduleRun).where(
                    ScheduleRun.schedule_id == sched.id,
                    ScheduleRun.status.in_(["PENDING", "PROCESSING"]),
                )
                run_res = await session.execute(existing_run_stmt)
                if not run_res.scalars().first():
                    new_run = ScheduleRun(
                        schedule_id=sched.id,
                        planned_run_at=sched.next_run_at,
                        status="PENDING",
                    )
                    session.add(new_run)
            await session.commit()

            # Find candidate pending runs
            pending_stmt = (
                select(ScheduleRun.id, ScheduleRun.planned_run_at)
                .where(
                    ScheduleRun.status == "PENDING",
                    ScheduleRun.planned_run_at <= now,
                )
                .order_by(ScheduleRun.planned_run_at.asc())
                .limit(10)
            )
            candidate_res = await session.execute(pending_stmt)
            candidates = candidate_res.all()

        for run_id, planned_at in candidates:
            # Check grace window: if planned_at < grace_threshold, mark SKIPPED
            if ensure_utc(planned_at) < grace_threshold:
                async with AsyncSessionLocal() as session:
                    skip_stmt = (
                        update(ScheduleRun)
                        .where(ScheduleRun.id == run_id, ScheduleRun.status == "PENDING")
                        .values(
                            status="SKIPPED",
                            completed_at=now,
                            error_message="Run missed grace window (>10 minutes late).",
                        )
                    )
                    await session.execute(skip_stmt)
                    await session.commit()
                continue

            # Attempt atomic claim
            claimed = False
            async with AsyncSessionLocal() as session:
                claim_stmt = (
                    update(ScheduleRun)
                    .where(ScheduleRun.id == run_id, ScheduleRun.status == "PENDING")
                    .values(status="PROCESSING", locked_at=now)
                )
                claim_res = await session.execute(claim_stmt)
                await session.commit()
                if claim_res.rowcount > 0:
                    claimed = True

            if claimed:
                await self._process_claimed_run(run_id)

    async def _process_claimed_run(self, run_id: str):
        now = utc_now()
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ScheduleRun)
                .where(ScheduleRun.id == run_id)
                .options(
                    selectinload(ScheduleRun.schedule).selectinload(Schedule.group),
                    selectinload(ScheduleRun.schedule).selectinload(Schedule.owner),
                )
            )
            res = await session.execute(stmt)
            schedule_run = res.scalars().first()

            if not schedule_run or not schedule_run.schedule:
                return

            schedule = schedule_run.schedule
            group = schedule.group
            owner = schedule.owner

            # If schedule or group is paused/inactive, mark skipped
            if schedule.is_paused or not group or not group.is_active:
                schedule_run.status = "SKIPPED"
                schedule_run.completed_at = now
                schedule_run.error_message = "Schedule paused or group inactive."
                await session.commit()
                return

            # Pick questions to send
            questions = await ScheduleService.select_questions_for_run(session, schedule)
            if not questions:
                schedule_run.status = "FAILED"
                schedule_run.completed_at = now
                schedule_run.error_message = "No questions available in pool."
                await session.commit()
                await self._advance_next_run(session, schedule)
                return

            # Post each question as native Telegram quiz poll
            all_succeeded = True
            error_details = []

            for question in questions:
                # Randomize the answer order so the correct option is not always
                # in the same position (toggle via SHUFFLE_POLL_OPTIONS).
                poll_options = list(question.options)
                poll_correct_option_id = question.correct_option_id
                if settings.SHUFFLE_POLL_OPTIONS:
                    poll_options, poll_correct_option_id = shuffle_poll_options(
                        poll_options, poll_correct_option_id
                    )

                try:
                    # Native Telegram quiz poll
                    msg = await self.bot.send_poll(
                        chat_id=group.chat_id,
                        question=question.text,
                        options=poll_options,
                        type="quiz",
                        correct_option_id=poll_correct_option_id,
                        explanation=question.explanation if question.explanation else None,
                        is_anonymous=True,
                    )
                    # Log success
                    log = PollSendLog(
                        schedule_run_id=schedule_run.id,
                        group_id=group.id,
                        question_id=question.id,
                        telegram_message_id=msg.message_id,
                        poll_id=msg.poll.id if msg.poll else None,
                        status="SUCCESS",
                        sent_at=utc_now(),
                    )
                    session.add(log)
                    await session.commit()

                    # Small delay between multiple questions in the same run
                    await asyncio.sleep(1.0)

                except TelegramRetryAfter as e:
                    logger.warning(f"Telegram 429 RetryAfter: waiting {e.retry_after}s")
                    await asyncio.sleep(e.retry_after)
                    # Retry once (reuse the same shuffled order/correct index)
                    try:
                        msg = await self.bot.send_poll(
                            chat_id=group.chat_id,
                            question=question.text,
                            options=poll_options,
                            type="quiz",
                            correct_option_id=poll_correct_option_id,
                            explanation=question.explanation if question.explanation else None,
                            is_anonymous=True,
                        )
                        log = PollSendLog(
                            schedule_run_id=schedule_run.id,
                            group_id=group.id,
                            question_id=question.id,
                            telegram_message_id=msg.message_id,
                            poll_id=msg.poll.id if msg.poll else None,
                            status="SUCCESS",
                            sent_at=utc_now(),
                        )
                        session.add(log)
                        await session.commit()
                    except Exception as retry_err:
                        all_succeeded = False
                        error_details.append(str(retry_err))

                except (TelegramForbiddenError, TelegramBadRequest) as bot_err:
                    err_msg = str(bot_err)
                    logger.error(f"Bot error in group {group.chat_id}: {err_msg}")
                    all_succeeded = False
                    error_details.append(err_msg)

                    # Log failed send
                    log = PollSendLog(
                        schedule_run_id=schedule_run.id,
                        group_id=group.id,
                        question_id=question.id,
                        status="FAILED",
                        error=err_msg,
                        sent_at=utc_now(),
                    )
                    session.add(log)

                    # If bot removed or kicked from group
                    if "kicked" in err_msg.lower() or "not found" in err_msg.lower() or "forbidden" in err_msg.lower():
                        group.is_active = False
                        schedule.is_paused = True
                        await session.commit()

                        # Notify owner privately
                        try:
                            await self.bot.send_message(
                                chat_id=owner.telegram_id,
                                text=t("notify_group_kicked", title=group.title),
                                parse_mode="HTML",
                            )
                        except Exception:
                            pass
                        break

                except Exception as unexpected:
                    err_msg = str(unexpected)
                    all_succeeded = False
                    error_details.append(err_msg)
                    log = PollSendLog(
                        schedule_run_id=schedule_run.id,
                        group_id=group.id,
                        question_id=question.id,
                        status="FAILED",
                        error=err_msg,
                        sent_at=utc_now(),
                    )
                    session.add(log)
                    await session.commit()

            schedule_run.status = "COMPLETED" if all_succeeded else "FAILED"
            schedule_run.completed_at = utc_now()
            if error_details:
                schedule_run.error_message = "; ".join(error_details)[:500]

            schedule.last_run_at = utc_now()
            await session.commit()

            # Advance next run time
            await self._advance_next_run(session, schedule)

    async def _advance_next_run(self, session: AsyncSession, schedule: Schedule):
        """Compute the next occurrence for recurring or pause one-time."""
        if schedule.schedule_type == "one_time":
            schedule.is_paused = True
            schedule.next_run_at = None
        else:
            # Recurring
            user_stmt = select(User.timezone).where(User.id == schedule.owner_id)
            user_tz = (await session.execute(user_stmt)).scalar_one_or_none() or "Asia/Tashkent"

            next_run = compute_next_run_at(
                schedule_type=schedule.schedule_type,
                time_of_day=schedule.time_of_day,
                tz_name=user_tz,
                weekdays=schedule.weekdays,
                after_utc=utc_now(),
            )
            schedule.next_run_at = next_run
            if next_run:
                # Add future pending run
                next_run_obj = ScheduleRun(
                    schedule_id=schedule.id,
                    planned_run_at=next_run,
                    status="PENDING",
                )
                session.add(next_run_obj)

        await session.commit()
