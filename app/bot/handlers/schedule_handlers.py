from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.locales.uz import t
from app.models.user import User
from app.services.schedule_service import ScheduleService
from app.services.group_service import GroupService
from app.services.question_service import QuestionService
from app.bot.keyboards import (
    get_schedules_menu_keyboard,
    get_schedule_detail_keyboard,
    get_cancel_keyboard,
    get_start_keyboard,
)

router = Router(name="schedule_router")

WEEKDAYS_MAP = ["Dush", "Sesh", "Chor", "Pay", "Juma", "Shan", "Yak"]


class AddScheduleStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_group = State()
    waiting_for_set = State()
    waiting_for_type = State()
    waiting_for_weekdays = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_count = State()
    waiting_for_order = State()


@router.callback_query(F.data == "cab:schedules")
async def show_schedules_menu(
    callback: CallbackQuery, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    await state.clear()
    schedules = await ScheduleService.get_user_schedules(db_session, user.id)
    text = t("schedules_menu_title", count=len(schedules))
    if not schedules:
        text += "\n\n" + t("schedules_empty")

    await callback.message.edit_text(
        text,
        reply_markup=get_schedules_menu_keyboard(schedules),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sched:v:"))
async def view_schedule_detail(
    callback: CallbackQuery, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    sched_id = callback.data[8:]
    schedule = await ScheduleService.get_schedule_by_id(db_session, sched_id, user.id)
    if not schedule:
        await callback.answer("Jadval topilmadi.", show_alert=True)
        return

    group_title = schedule.group.title if schedule.group else "Noma'lum"
    set_name = schedule.test_set.name if schedule.test_set else "Barcha savollar"
    sched_type = "Takroriy" if schedule.schedule_type == "recurring" else "Bir martalik"

    if schedule.schedule_type == "recurring":
        days_str = ", ".join(WEEKDAYS_MAP[d] for d in (schedule.weekdays or []))
        time_info = f"{days_str} soat {schedule.time_of_day}"
    else:
        time_info = f"{schedule.one_time_date} {schedule.time_of_day}"

    order_str = "Tasodifiy" if schedule.order_mode == "random" else "Ketma-ket"
    status_str = "To'xtatilgan (Pauza)" if schedule.is_paused else "Faol"

    next_run_str = (
        schedule.next_run_at.strftime("%Y-%m-%d %H:%M UTC")
        if schedule.next_run_at
        else "Yo'q"
    )

    text = t(
        "schedule_detail",
        name=schedule.name,
        group_title=group_title,
        set_name=set_name,
        schedule_type=sched_type,
        time_info=time_info,
        count=schedule.questions_per_run,
        order_mode=order_str,
        status=status_str,
        next_run=next_run_str,
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_schedule_detail_keyboard(schedule),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sched:toggle:"))
async def toggle_schedule_status(
    callback: CallbackQuery, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    sched_id = callback.data[13:]
    schedule = await ScheduleService.toggle_schedule(db_session, sched_id, user.id)
    if not schedule:
        await callback.answer("Jadval topilmadi.", show_alert=True)
        return

    msg = "Jadval to'xtatildi." if schedule.is_paused else "Jadval faollashtirildi."
    await callback.answer(msg, show_alert=True)
    await view_schedule_detail(callback, user, db_session)


@router.callback_query(F.data.startswith("sched:del:"))
async def delete_schedule_handler(
    callback: CallbackQuery, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    sched_id = callback.data[10:]
    await ScheduleService.delete_schedule(db_session, sched_id, user.id)
    await callback.answer(t("schedule_deleted"), show_alert=True)

    schedules = await ScheduleService.get_user_schedules(db_session, user.id)
    await callback.message.edit_text(
        t("schedules_menu_title", count=len(schedules)),
        reply_markup=get_schedules_menu_keyboard(schedules),
        parse_mode="HTML",
    )


# --- Add Schedule Flow ---
@router.callback_query(F.data == "sched:add")
async def start_add_schedule(
    callback: CallbackQuery, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    groups = await GroupService.get_user_groups(db_session, user.id)
    if not groups:
        await callback.answer(t("add_sched_no_groups"), show_alert=True)
        return

    await state.set_state(AddScheduleStates.waiting_for_name)
    await callback.message.edit_text(
        t("add_sched_enter_name"),
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AddScheduleStates.waiting_for_name, F.text, F.chat.type == "private")
async def process_sched_name(
    message: Message, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if not user:
        await message.answer(t("login_invalid_credentials"), reply_markup=get_start_keyboard())
        return

    name = message.text.strip()
    if not (1 <= len(name) <= 100):
        await message.answer("Nom 1-100 belgi bo'lishi kerak.", reply_markup=get_cancel_keyboard())
        return

    await state.update_data(sched_name=name)
    await state.set_state(AddScheduleStates.waiting_for_group)

    groups = await GroupService.get_user_groups(db_session, user.id)
    buttons = [
        [InlineKeyboardButton(text=f"👥 {g.title[:25]}", callback_data=f"sc_grp:{g.id}")]
        for g in groups
    ]
    buttons.append([InlineKeyboardButton(text=t("btn_cancel"), callback_data="action:cancel")])

    await message.answer(
        t("add_sched_select_group"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(AddScheduleStates.waiting_for_group, F.data.startswith("sc_grp:"))
async def process_sched_group(
    callback: CallbackQuery, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    group_id = callback.data[7:]
    await state.update_data(sched_group_id=group_id)
    await state.set_state(AddScheduleStates.waiting_for_set)

    sets = await QuestionService.get_user_sets(db_session, user.id)
    buttons = [
        [InlineKeyboardButton(text=f"📁 {s.name[:25]}", callback_data=f"sc_set:{s.id}")]
        for s in sets
    ]
    buttons.append([InlineKeyboardButton(text=t("btn_all_questions"), callback_data="sc_set:all")])
    buttons.append([InlineKeyboardButton(text=t("btn_cancel"), callback_data="action:cancel")])

    await callback.message.edit_text(
        t("add_sched_select_set"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(AddScheduleStates.waiting_for_set, F.data.startswith("sc_set:"))
async def process_sched_set(callback: CallbackQuery, state: FSMContext, user: User | None):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    set_id_raw = callback.data[7:]
    test_set_id = None if set_id_raw == "all" else set_id_raw
    await state.update_data(sched_set_id=test_set_id)
    await state.set_state(AddScheduleStates.waiting_for_type)

    buttons = [
        [
            InlineKeyboardButton(text=t("btn_type_recurring"), callback_data="sc_type:recurring"),
            InlineKeyboardButton(text=t("btn_type_one_time"), callback_data="sc_type:one_time"),
        ],
        [InlineKeyboardButton(text=t("btn_cancel"), callback_data="action:cancel")],
    ]
    await callback.message.edit_text(
        t("add_sched_select_type"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


def build_weekdays_keyboard(selected_days: list[int]) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for idx, day_name in enumerate(WEEKDAYS_MAP):
        mark = "✅ " if idx in selected_days else ""
        row.append(
            InlineKeyboardButton(text=f"{mark}{day_name}", callback_data=f"sc_day:{idx}")
        )
        if len(row) == 4 or idx == len(WEEKDAYS_MAP) - 1:
            buttons.append(row)
            row = []

    buttons.append([InlineKeyboardButton(text=t("btn_day_done"), callback_data="sc_day:done")])
    buttons.append([InlineKeyboardButton(text=t("btn_cancel"), callback_data="action:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(AddScheduleStates.waiting_for_type, F.data.startswith("sc_type:"))
async def process_sched_type(callback: CallbackQuery, state: FSMContext, user: User | None):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    sched_type = callback.data[8:]
    await state.update_data(sched_type=sched_type)

    if sched_type == "recurring":
        await state.update_data(sched_weekdays=[0, 1, 2, 3, 4])  # Default Mon-Fri
        await state.set_state(AddScheduleStates.waiting_for_weekdays)
        await callback.message.edit_text(
            t("add_sched_select_days"),
            reply_markup=build_weekdays_keyboard([0, 1, 2, 3, 4]),
        )
    else:
        await state.set_state(AddScheduleStates.waiting_for_date)
        await callback.message.edit_text(
            t("add_sched_enter_date"),
            reply_markup=get_cancel_keyboard(),
        )
    await callback.answer()


@router.callback_query(AddScheduleStates.waiting_for_weekdays, F.data.startswith("sc_day:"))
async def toggle_sched_day(callback: CallbackQuery, state: FSMContext, user: User | None):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    action = callback.data[7:]
    data = await state.get_data()
    selected: list[int] = data.get("sched_weekdays", [])

    if action == "done":
        if not selected:
            await callback.answer("Kamida bitta kunni tanlang!", show_alert=True)
            return
        await state.set_state(AddScheduleStates.waiting_for_time)
        await callback.message.edit_text(
            t("add_sched_enter_time", timezone=user.timezone),
            reply_markup=get_cancel_keyboard(),
        )
        await callback.answer()
        return

    day_idx = int(action)
    if day_idx in selected:
        selected.remove(day_idx)
    else:
        selected.append(day_idx)
        selected.sort()

    await state.update_data(sched_weekdays=selected)
    await callback.message.edit_reply_markup(reply_markup=build_weekdays_keyboard(selected))
    await callback.answer()


@router.message(AddScheduleStates.waiting_for_date, F.text, F.chat.type == "private")
async def process_sched_date(message: Message, state: FSMContext, user: User | None):
    if not user:
        await message.answer(t("login_invalid_credentials"), reply_markup=get_start_keyboard())
        return

    date_str = message.text.strip()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("Noto'g'ri sana formati. Masalan: 2026-10-20", reply_markup=get_cancel_keyboard())
        return

    await state.update_data(sched_date=date_str)
    await state.set_state(AddScheduleStates.waiting_for_time)
    await message.answer(
        t("add_sched_enter_time", timezone=user.timezone),
        reply_markup=get_cancel_keyboard(),
    )


@router.message(AddScheduleStates.waiting_for_time, F.text, F.chat.type == "private")
async def process_sched_time(message: Message, state: FSMContext, user: User | None):
    if not user:
        await message.answer(t("login_invalid_credentials"), reply_markup=get_start_keyboard())
        return

    time_str = message.text.strip()
    try:
        parts = time_str.split(":")
        if len(parts) != 2:
            raise ValueError
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except Exception:
        await message.answer("Noto'g'ri vaqt formati. Masalan: 09:30 yoki 18:00", reply_markup=get_cancel_keyboard())
        return

    formatted_time = f"{h:02d}:{m:02d}"
    await state.update_data(sched_time=formatted_time)
    await state.set_state(AddScheduleStates.waiting_for_count)
    await message.answer(t("add_sched_enter_count"), reply_markup=get_cancel_keyboard())


@router.message(AddScheduleStates.waiting_for_count, F.text, F.chat.type == "private")
async def process_sched_count(message: Message, state: FSMContext, user: User | None):
    if not user:
        await message.answer(t("login_invalid_credentials"), reply_markup=get_start_keyboard())
        return

    val = message.text.strip()
    if not val.isdigit() or not (1 <= int(val) <= 10):
        await message.answer("Savollar soni 1 dan 10 gacha bo'lishi kerak.", reply_markup=get_cancel_keyboard())
        return

    await state.update_data(sched_count=int(val))
    await state.set_state(AddScheduleStates.waiting_for_order)

    buttons = [
        [
            InlineKeyboardButton(text=t("btn_order_random"), callback_data="sc_ord:random"),
            InlineKeyboardButton(text=t("btn_order_sequential"), callback_data="sc_ord:sequential"),
        ],
        [InlineKeyboardButton(text=t("btn_cancel"), callback_data="action:cancel")],
    ]
    await message.answer(
        t("add_sched_select_order"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(AddScheduleStates.waiting_for_order, F.data.startswith("sc_ord:"))
async def process_sched_order(
    callback: CallbackQuery, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    order_mode = callback.data[7:]
    data = await state.get_data()

    sched, err = await ScheduleService.create_schedule(
        session=db_session,
        owner=user,
        group_id=data.get("sched_group_id"),
        name=data.get("sched_name"),
        schedule_type=data.get("sched_type"),
        time_of_day=data.get("sched_time"),
        questions_per_run=data.get("sched_count", 1),
        order_mode=order_mode,
        test_set_id=data.get("sched_set_id"),
        weekdays=data.get("sched_weekdays"),
        one_time_date=data.get("sched_date"),
    )

    await state.clear()
    if err:
        await callback.message.edit_text(t(err), reply_markup=get_schedules_menu_keyboard([]))
    else:
        schedules = await ScheduleService.get_user_schedules(db_session, user.id)
        await callback.message.edit_text(
            t("add_sched_success") + "\n\n" + t("schedules_menu_title", count=len(schedules)),
            reply_markup=get_schedules_menu_keyboard(schedules),
            parse_mode="HTML",
        )
    await callback.answer()
