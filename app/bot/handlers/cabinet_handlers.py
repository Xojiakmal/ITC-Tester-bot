from zoneinfo import ZoneInfo
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.locales.uz import t
from app.models.user import User
from app.services.auth_service import AuthService
from app.bot.keyboards import (
    get_cabinet_menu_keyboard,
    get_settings_keyboard,
    get_cancel_keyboard,
    get_start_keyboard,
    get_confirm_keyboard,
)
from app.bot.middlewares import delete_message_safe

router = Router(name="cabinet_router")


class SettingsStates(StatesGroup):
    waiting_for_timezone = State()
    chpass_old = State()
    chpass_new = State()
    chpass_confirm = State()


@router.callback_query(F.data == "cab:main")
async def show_cabinet_main(callback: CallbackQuery, state: FSMContext, user: User | None):
    if not user:
        await callback.message.edit_text(t("welcome_guest"), reply_markup=get_start_keyboard())
        await callback.answer()
        return

    await state.clear()
    await callback.message.edit_text(
        t("cabinet_welcome", username=user.username, timezone=user.timezone),
        reply_markup=get_cabinet_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "cab:logout")
async def handle_logout(
    callback: CallbackQuery, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if user:
        await AuthService.revoke_all_user_sessions(db_session, user.id)

    await state.clear()
    await callback.message.edit_text(
        t("logout_done") + "\n\n" + t("welcome_guest"),
        reply_markup=get_start_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "cab:settings")
async def show_settings_menu(callback: CallbackQuery, user: User | None):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    await callback.message.edit_text(
        t("settings_title", username=user.username, timezone=user.timezone),
        reply_markup=get_settings_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "set:tz")
async def start_change_timezone(callback: CallbackQuery, state: FSMContext, user: User | None):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    await state.set_state(SettingsStates.waiting_for_timezone)
    await callback.message.edit_text(
        t("tz_enter_name"),
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(SettingsStates.waiting_for_timezone, F.text, F.chat.type == "private")
async def process_change_timezone(
    message: Message, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if not user:
        await message.answer(t("login_invalid_credentials"), reply_markup=get_start_keyboard())
        return

    tz_name = message.text.strip()
    try:
        ZoneInfo(tz_name)
    except Exception:
        await message.answer(t("tz_invalid"), reply_markup=get_cancel_keyboard())
        return

    user.timezone = tz_name
    await db_session.commit()
    await state.clear()

    await message.answer(
        t("tz_updated", timezone=tz_name) + "\n\n" + t("cabinet_welcome", username=user.username, timezone=user.timezone),
        reply_markup=get_cabinet_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "set:chpass")
async def start_change_password(callback: CallbackQuery, state: FSMContext, user: User | None):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    await state.set_state(SettingsStates.chpass_old)
    await callback.message.edit_text(
        t("chpass_enter_old"),
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(SettingsStates.chpass_old, F.text, F.chat.type == "private")
async def process_chpass_old(message: Message, state: FSMContext, user: User | None):
    if not user:
        await message.answer(t("login_invalid_credentials"), reply_markup=get_start_keyboard())
        return

    old_pw = message.text
    await delete_message_safe(message)

    await state.update_data(chpass_old=old_pw)
    await state.set_state(SettingsStates.chpass_new)
    await message.answer(t("chpass_enter_new"), reply_markup=get_cancel_keyboard())


@router.message(SettingsStates.chpass_new, F.text, F.chat.type == "private")
async def process_chpass_new(message: Message, state: FSMContext):
    new_pw = message.text
    await delete_message_safe(message)

    await state.update_data(chpass_new=new_pw)
    await state.set_state(SettingsStates.chpass_confirm)
    await message.answer(t("chpass_confirm_new"), reply_markup=get_cancel_keyboard())


@router.message(SettingsStates.chpass_confirm, F.text, F.chat.type == "private")
async def process_chpass_confirm(
    message: Message, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if not user:
        await message.answer(t("login_invalid_credentials"), reply_markup=get_start_keyboard())
        return

    confirm_pw = message.text
    await delete_message_safe(message)

    data = await state.get_data()
    old_pw = data.get("chpass_old")
    new_pw = data.get("chpass_new")

    if confirm_pw != new_pw:
        await state.clear()
        await message.answer(t("reg_passwords_mismatch"), reply_markup=get_cabinet_menu_keyboard())
        return

    success, err_key = await AuthService.change_password(db_session, user, old_pw, new_pw)
    if not success:
        await state.clear()
        await message.answer(t(err_key), reply_markup=get_cabinet_menu_keyboard())
        return

    # Create new session for current user
    new_token = await AuthService.create_user_session(db_session, user.id)
    await state.clear()
    await state.update_data(session_token=new_token)

    await message.answer(
        t("chpass_success") + "\n\n" + t("cabinet_welcome", username=user.username, timezone=user.timezone),
        reply_markup=get_cabinet_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "set:logout_all")
async def confirm_logout_all(callback: CallbackQuery, user: User | None):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    await callback.message.edit_text(
        t("logout_everywhere_confirm"),
        reply_markup=get_confirm_keyboard(confirm_cb="set:do_logout_all", cancel_cb="cab:settings"),
    )
    await callback.answer()


@router.callback_query(F.data == "set:do_logout_all")
async def execute_logout_all(
    callback: CallbackQuery, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    await AuthService.revoke_all_user_sessions(db_session, user.id)
    await state.clear()
    await callback.message.edit_text(
        t("logout_everywhere_done") + "\n\n" + t("welcome_guest"),
        reply_markup=get_start_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "set:delete_acc")
async def confirm_delete_account(callback: CallbackQuery, user: User | None):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    await callback.message.edit_text(
        t("delete_account_confirm"),
        reply_markup=get_confirm_keyboard(confirm_cb="set:do_del_acc", cancel_cb="cab:settings"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "set:do_del_acc")
async def execute_delete_account(
    callback: CallbackQuery, state: FSMContext, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    await AuthService.delete_user_account(db_session, user.id)
    await state.clear()
    await callback.message.edit_text(
        t("delete_account_done") + "\n\n" + t("welcome_guest"),
        reply_markup=get_start_keyboard(),
    )
    await callback.answer()
