from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.locales.uz import t
from app.services.auth_service import (
    AuthService,
    validate_username,
    validate_password_strength,
    verify_password,
)
from app.bot.keyboards import (
    get_start_keyboard,
    get_cancel_keyboard,
    get_cabinet_menu_keyboard,
)
from app.bot.middlewares import delete_message_safe
from app.models.user import User

router = Router(name="auth_router")


class RegisterStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()
    waiting_for_confirm_password = State()


class LoginStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()


@router.message(CommandStart(), F.chat.type == "private")
async def handle_start(message: Message, state: FSMContext, user: User | None, db_session: AsyncSession):
    if user:
        # User already logged in, show cabinet
        await state.clear()
        await message.answer(
            t("cabinet_welcome", username=user.username, timezone=user.timezone),
            reply_markup=get_cabinet_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    # Check if this telegram user has an account
    existing_user = await AuthService.get_user_by_telegram_id(db_session, message.from_user.id)
    if existing_user and not existing_user.is_blocked:
        # Prompt login
        await message.answer(
            t("welcome_guest"),
            reply_markup=get_start_keyboard(),
        )
    else:
        await message.answer(
            t("welcome_guest"),
            reply_markup=get_start_keyboard(),
        )


@router.callback_query(F.data == "auth:register")
async def start_registration(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    # Check if user already exists for this telegram account
    existing_user = await AuthService.get_user_by_telegram_id(db_session, callback.from_user.id)
    if existing_user:
        await callback.answer(t("reg_already_have_account"), show_alert=True)
        return

    await state.set_state(RegisterStates.waiting_for_username)
    await callback.message.edit_text(
        t("reg_enter_username"),
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(RegisterStates.waiting_for_username, F.text, F.chat.type == "private")
async def process_reg_username(message: Message, state: FSMContext, db_session: AsyncSession):
    username = message.text.strip()
    if not validate_username(username):
        await message.answer(t("reg_username_invalid"), reply_markup=get_cancel_keyboard())
        return

    existing = await AuthService.get_user_by_username(db_session, username)
    if existing:
        await message.answer(t("reg_username_taken"), reply_markup=get_cancel_keyboard())
        return

    await state.update_data(reg_username=username)
    await state.set_state(RegisterStates.waiting_for_password)
    await message.answer(t("reg_enter_password"), reply_markup=get_cancel_keyboard())


@router.message(RegisterStates.waiting_for_password, F.text, F.chat.type == "private")
async def process_reg_password(message: Message, state: FSMContext):
    # Immediately delete the message containing the password
    password = message.text
    await delete_message_safe(message)

    valid, err_key = validate_password_strength(password)
    if not valid:
        await message.answer(t(err_key), reply_markup=get_cancel_keyboard())
        return

    await state.update_data(reg_password=password)
    await state.set_state(RegisterStates.waiting_for_confirm_password)
    await message.answer(t("reg_confirm_password"), reply_markup=get_cancel_keyboard())


@router.message(RegisterStates.waiting_for_confirm_password, F.text, F.chat.type == "private")
async def process_reg_confirm_password(
    message: Message, state: FSMContext, db_session: AsyncSession
):
    confirm_password = message.text
    await delete_message_safe(message)

    data = await state.get_data()
    original_password = data.get("reg_password")
    username = data.get("reg_username")

    if confirm_password != original_password:
        await state.clear()
        await message.answer(
            t("reg_passwords_mismatch"),
            reply_markup=get_start_keyboard(),
        )
        return

    user, err_key = await AuthService.register_user(
        db_session,
        telegram_id=message.from_user.id,
        username=username,
        password=original_password,
    )

    if err_key:
        await state.clear()
        await message.answer(t(err_key), reply_markup=get_start_keyboard())
        return

    # Automatically create session and log user in
    token = await AuthService.create_user_session(db_session, user.id)
    await state.clear()
    await state.update_data(session_token=token)

    await message.answer(
        t("reg_success") + "\n\n" + t("cabinet_welcome", username=user.username, timezone=user.timezone),
        reply_markup=get_cabinet_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "auth:login")
async def start_login(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    # Check if throttled by telegram ID
    tg_id_key = f"tg:{callback.from_user.id}"
    is_locked, remaining = await AuthService.check_login_throttled(db_session, tg_id_key)
    if is_locked:
        await callback.answer(t("login_throttled", seconds=remaining), show_alert=True)
        return

    await state.set_state(LoginStates.waiting_for_username)
    await callback.message.edit_text(
        t("login_enter_username"),
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(LoginStates.waiting_for_username, F.text, F.chat.type == "private")
async def process_login_username(message: Message, state: FSMContext, db_session: AsyncSession):
    username = message.text.strip()
    user_key = f"user:{username.lower()}"
    tg_key = f"tg:{message.from_user.id}"

    # Check throttling on username or telegram ID
    is_locked_user, rem_user = await AuthService.check_login_throttled(db_session, user_key)
    is_locked_tg, rem_tg = await AuthService.check_login_throttled(db_session, tg_key)

    if is_locked_user or is_locked_tg:
        rem = max(rem_user, rem_tg)
        await message.answer(t("login_throttled", seconds=rem), reply_markup=get_start_keyboard())
        await state.clear()
        return

    await state.update_data(login_username=username)
    await state.set_state(LoginStates.waiting_for_password)
    await message.answer(t("login_enter_password"), reply_markup=get_cancel_keyboard())


@router.message(LoginStates.waiting_for_password, F.text, F.chat.type == "private")
async def process_login_password(
    message: Message, state: FSMContext, db_session: AsyncSession
):
    password = message.text
    await delete_message_safe(message)

    data = await state.get_data()
    username = data.get("login_username", "").strip()

    tg_key = f"tg:{message.from_user.id}"
    user_key = f"user:{username.lower()}"

    user = await AuthService.get_user_by_username(db_session, username)

    # Validate user exists, password matches, and bound telegram ID equals sender
    failed = False
    if not user:
        failed = True
    elif user.telegram_id != message.from_user.id:
        failed = True
    elif not verify_password(password, user.password_hash):
        failed = True

    if failed:
        # Record failure with exponential backoff on both identifiers
        wait_tg = await AuthService.record_login_failure(db_session, tg_key)
        wait_user = await AuthService.record_login_failure(db_session, user_key)
        wait_time = max(wait_tg, wait_user)

        await state.clear()
        if wait_time > 0:
            await message.answer(
                t("login_throttled", seconds=wait_time),
                reply_markup=get_start_keyboard(),
            )
        else:
            await message.answer(
                t("login_invalid_credentials"),
                reply_markup=get_start_keyboard(),
            )
        return

    if user.is_blocked:
        await state.clear()
        await message.answer(t("login_account_blocked"), reply_markup=get_start_keyboard())
        return

    # Success: clear throttling
    await AuthService.record_login_success(db_session, tg_key)
    await AuthService.record_login_success(db_session, user_key)

    # Create server session
    token = await AuthService.create_user_session(db_session, user.id)
    await state.clear()
    await state.update_data(session_token=token)

    await message.answer(
        t("login_success") + "\n\n" + t("cabinet_welcome", username=user.username, timezone=user.timezone),
        reply_markup=get_cabinet_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "action:cancel")
async def handle_cancel(callback: CallbackQuery, state: FSMContext, user: User | None):
    await state.clear()
    if user:
        await callback.message.edit_text(
            t("cabinet_welcome", username=user.username, timezone=user.timezone),
            reply_markup=get_cabinet_menu_keyboard(),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            t("action_cancelled") + "\n\n" + t("welcome_guest"),
            reply_markup=get_start_keyboard(),
        )
    await callback.answer()
