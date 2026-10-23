from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.locales.uz import t
from app.models.group import TelegramGroup
from app.models.question import Question, TestSet
from app.models.schedule import Schedule


def get_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_login"), callback_data="auth:login"),
                InlineKeyboardButton(text=t("btn_register"), callback_data="auth:register"),
            ]
        ]
    )


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_cancel"), callback_data="action:cancel")]
        ]
    )


def get_cabinet_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_menu_groups"), callback_data="cab:groups"),
                InlineKeyboardButton(text=t("btn_menu_add_group"), callback_data="cab:add_group"),
            ],
            [
                InlineKeyboardButton(text=t("btn_menu_questions"), callback_data="cab:questions"),
                InlineKeyboardButton(text=t("btn_menu_schedules"), callback_data="cab:schedules"),
            ],
            [
                InlineKeyboardButton(text=t("btn_menu_settings"), callback_data="cab:settings"),
                InlineKeyboardButton(text=t("btn_menu_logout"), callback_data="cab:logout"),
            ],
        ]
    )


def get_groups_list_keyboard(groups: List[TelegramGroup]) -> InlineKeyboardMarkup:
    buttons = []
    for g in groups:
        status_icon = "🟢" if g.is_active else "🔴"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_icon} {g.title[:25]}",
                callback_data=f"grp:v:{g.id}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text=t("btn_menu_add_group"), callback_data="cab:add_group")
    ])
    buttons.append([
        InlineKeyboardButton(text=t("btn_back"), callback_data="cab:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_group_detail_keyboard(group: TelegramGroup, has_schedules: bool) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text=t("btn_group_schedules"), callback_data=f"grp:s:{group.id}"),
        ],
        [
            InlineKeyboardButton(text=t("btn_group_pause_all"), callback_data=f"grp:pause:{group.id}"),
            InlineKeyboardButton(text=t("btn_group_resume_all"), callback_data=f"grp:resume:{group.id}"),
        ],
        [
            InlineKeyboardButton(text=t("btn_group_unlink"), callback_data=f"grp:unl:{group.id}"),
        ],
        [
            InlineKeyboardButton(text=t("btn_back"), callback_data="cab:groups"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_group_unlink_confirm_keyboard(group_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_confirm"), callback_data=f"grp:cf_unl:{group_id}"),
                InlineKeyboardButton(text=t("btn_cancel"), callback_data=f"grp:v:{group_id}"),
            ]
        ]
    )


def get_questions_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_add_question"), callback_data="q:add"),
                InlineKeyboardButton(text=t("btn_list_questions"), callback_data="q:list:1"),
            ],
            [
                InlineKeyboardButton(text=t("btn_test_sets"), callback_data="set:list"),
                InlineKeyboardButton(text=t("btn_import_csv"), callback_data="q:import_csv"),
            ],
            [
                InlineKeyboardButton(text=t("btn_csv_template"), callback_data="q:template"),
            ],
            [
                InlineKeyboardButton(text=t("btn_back"), callback_data="cab:main"),
            ],
        ]
    )


def get_questions_list_keyboard(
    questions: List[Question], page: int, total_pages: int, search_query: Optional[str] = None
) -> InlineKeyboardMarkup:
    buttons = []
    for q in questions:
        snippet = q.text[:30] + ("..." if len(q.text) > 30 else "")
        buttons.append([
            InlineKeyboardButton(text=f"❓ {snippet}", callback_data=f"q:v:{q.id}")
        ])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text=t("btn_prev_page"), callback_data=f"q:list:{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text=t("btn_next_page"), callback_data=f"q:list:{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(text=t("btn_search_questions"), callback_data="q:search"),
        InlineKeyboardButton(text=t("btn_add_question"), callback_data="q:add"),
    ])
    buttons.append([
        InlineKeyboardButton(text=t("btn_back"), callback_data="cab:questions")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_question_detail_keyboard(question_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_delete_question"), callback_data=f"q:del:{question_id}"),
            ],
            [
                InlineKeyboardButton(text=t("btn_back"), callback_data="q:list:1"),
            ],
        ]
    )


def get_options_select_keyboard(count: int) -> InlineKeyboardMarkup:
    row = []
    for i in range(count):
        row.append(InlineKeyboardButton(text=f"{i+1}", callback_data=f"q:opt:{i}"))
    return InlineKeyboardMarkup(inline_keyboard=[row, [InlineKeyboardButton(text=t("btn_cancel"), callback_data="action:cancel")]])


def get_skip_keyboard(skip_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_skip"), callback_data=skip_cb)],
            [InlineKeyboardButton(text=t("btn_cancel"), callback_data="action:cancel")],
        ]
    )


def get_sets_picker_keyboard(sets: List[TestSet], none_cb: str) -> InlineKeyboardMarkup:
    buttons = []
    for s in sets:
        buttons.append([
            InlineKeyboardButton(text=f"📁 {s.name[:25]}", callback_data=f"q:set:{s.id}")
        ])
    buttons.append([
        InlineKeyboardButton(text=t("btn_no_set"), callback_data=none_cb)
    ])
    buttons.append([
        InlineKeyboardButton(text=t("btn_cancel"), callback_data="action:cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_sets_list_keyboard(sets: List[TestSet]) -> InlineKeyboardMarkup:
    buttons = []
    for s in sets:
        buttons.append([
            InlineKeyboardButton(text=f"📁 {s.name[:25]}", callback_data=f"set:v:{s.id}")
        ])
    buttons.append([
        InlineKeyboardButton(text=t("btn_create_set"), callback_data="set:add")
    ])
    buttons.append([
        InlineKeyboardButton(text=t("btn_back"), callback_data="cab:questions")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_set_detail_keyboard(set_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_delete_set"), callback_data=f"set:del:{set_id}"),
            ],
            [
                InlineKeyboardButton(text=t("btn_back"), callback_data="set:list"),
            ],
        ]
    )


def get_schedules_menu_keyboard(schedules: List[Schedule]) -> InlineKeyboardMarkup:
    buttons = []
    for s in schedules:
        status_icon = "🟢" if not s.is_paused else "⏸"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_icon} {s.name[:22]}",
                callback_data=f"sched:v:{s.id}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text=t("btn_add_schedule"), callback_data="sched:add")
    ])
    buttons.append([
        InlineKeyboardButton(text=t("btn_back"), callback_data="cab:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_schedule_detail_keyboard(schedule: Schedule) -> InlineKeyboardMarkup:
    toggle_btn = (
        InlineKeyboardButton(text=t("btn_resume_schedule"), callback_data=f"sched:toggle:{schedule.id}")
        if schedule.is_paused
        else InlineKeyboardButton(text=t("btn_pause_schedule"), callback_data=f"sched:toggle:{schedule.id}")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [toggle_btn],
            [InlineKeyboardButton(text=t("btn_delete_schedule"), callback_data=f"sched:del:{schedule.id}")],
            [InlineKeyboardButton(text=t("btn_back"), callback_data="cab:schedules")],
        ]
    )


def get_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_change_timezone"), callback_data="set:tz")],
            [InlineKeyboardButton(text=t("btn_change_password"), callback_data="set:chpass")],
            [InlineKeyboardButton(text=t("btn_logout_everywhere"), callback_data="set:logout_all")],
            [InlineKeyboardButton(text=t("btn_delete_account"), callback_data="set:delete_acc")],
            [InlineKeyboardButton(text=t("btn_back"), callback_data="cab:main")],
        ]
    )


def get_confirm_keyboard(confirm_cb: str, cancel_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_confirm"), callback_data=confirm_cb),
                InlineKeyboardButton(text=t("btn_cancel"), callback_data=cancel_cb),
            ]
        ]
    )
