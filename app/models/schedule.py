from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, generate_uuid, utc_now


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    group_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("telegram_groups.id", ondelete="CASCADE"), index=True, nullable=False
    )
    test_set_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("test_sets.id", ondelete="SET NULL"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    schedule_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'recurring' or 'one_time'
    weekdays: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)  # [0, 1, 2, 3, 4, 5, 6] (0=Monday)
    time_of_day: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # 'HH:MM'
    one_time_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 'YYYY-MM-DD'
    questions_per_run: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    order_mode: Mapped[str] = mapped_column(String(20), default="random", nullable=False)  # 'random' or 'sequential'
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    owner: Mapped["User"] = relationship("User", back_populates="schedules")
    group: Mapped["TelegramGroup"] = relationship("TelegramGroup", back_populates="schedules")
    test_set: Mapped[Optional["TestSet"]] = relationship("TestSet", back_populates="schedules")
    runs: Mapped[list["ScheduleRun"]] = relationship("ScheduleRun", back_populates="schedule", cascade="all, delete-orphan")
    sent_questions: Mapped[list["ScheduleSentQuestion"]] = relationship(
        "ScheduleSentQuestion", back_populates="schedule", cascade="all, delete-orphan"
    )


class ScheduleSentQuestion(Base):
    __tablename__ = "schedule_sent_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    schedule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schedules.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("questions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    schedule: Mapped["Schedule"] = relationship("Schedule", back_populates="sent_questions")


class ScheduleRun(Base):
    __tablename__ = "schedule_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    schedule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schedules.id", ondelete="CASCADE"), index=True, nullable=False
    )
    planned_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="PENDING", index=True, nullable=False
    )  # PENDING, PROCESSING, COMPLETED, SKIPPED, FAILED
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    schedule: Mapped["Schedule"] = relationship("Schedule", back_populates="runs")
    logs: Mapped[list["PollSendLog"]] = relationship("PollSendLog", back_populates="schedule_run")


class PollSendLog(Base):
    __tablename__ = "poll_send_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    schedule_run_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("schedule_runs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    group_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("telegram_groups.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("questions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    telegram_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    poll_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # SUCCESS, FAILED
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    schedule_run: Mapped[Optional["ScheduleRun"]] = relationship("ScheduleRun", back_populates="logs")
    group: Mapped["TelegramGroup"] = relationship("TelegramGroup", back_populates="poll_send_logs")
    question: Mapped["Question"] = relationship("Question", back_populates="sent_logs")
