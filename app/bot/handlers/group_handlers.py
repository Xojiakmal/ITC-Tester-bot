from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    ChatMemberUpdated,
    ChatMemberRestricted,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.locales.uz import t
from app.models.user import User
from app.services.group_service import GroupService
from app.services.auth_service import AuthService
from app.bot.keyboards import (
    get_groups_list_keyboard,
    get_group_detail_keyboard,
    get_group_unlink_confirm_keyboard,
    get_start_keyboard,
)
from app.bot.middlewares import delete_message_safe
from app.config import get_settings

router = Router(name="group_router")
settings = get_settings()


@router.callback_query(F.data == "cab:groups")
async def show_groups_menu(
    callback: CallbackQuery, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    groups = await GroupService.get_user_groups(db_session, user.id)
    text = t("groups_list_title")
    if not groups:
        text += t("groups_empty")

    await callback.message.edit_text(
        text,
        reply_markup=get_groups_list_keyboard(groups),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "cab:add_group")
async def generate_add_group_code(
    callback: CallbackQuery, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    current_groups = await GroupService.count_user_groups(db_session, user.id)
    if current_groups >= settings.MAX_GROUPS_PER_USER:
        await callback.answer(
            t("group_quota_exceeded", limit=settings.MAX_GROUPS_PER_USER), show_alert=True
        )
        return

    raw_code, _ = await GroupService.generate_join_code(db_session, user.id)

    me = await callback.bot.get_me()
    bot_username = me.username or "ITTestBot"
    command_full = f"/join@{bot_username} {raw_code}"

    text = t(
        "add_group_instructions",
        command=command_full,
        code=raw_code,
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_groups_list_keyboard(await GroupService.get_user_groups(db_session, user.id)),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("grp:v:"))
async def view_group_detail(
    callback: CallbackQuery, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    group_id = callback.data[6:]
    group = await GroupService.get_group_by_id(db_session, group_id, user.id)
    if not group:
        await callback.answer("Guruh topilmadi.", show_alert=True)
        return

    status_str = t("group_status_active") if group.is_active else t("group_status_inactive")
    polls_perm_str = "Ha" if group.can_send_polls else "Yo'q"
    schedules_count = len(group.schedules) if group.schedules else 0

    text = t(
        "group_detail",
        title=group.title,
        status=status_str,
        chat_id=group.chat_id,
        polls_permission=polls_perm_str,
        schedules_count=schedules_count,
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_group_detail_keyboard(group, schedules_count > 0),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("grp:pause:"))
async def pause_group_schedules(
    callback: CallbackQuery, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    group_id = callback.data[10:]
    await GroupService.toggle_group_schedules(db_session, group_id, user.id, pause=True)
    await callback.answer("Guruhdagi barcha jadvallar to'xtatildi.", show_alert=True)


@router.callback_query(F.data.startswith("grp:resume:"))
async def resume_group_schedules(
    callback: CallbackQuery, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    group_id = callback.data[11:]
    await GroupService.toggle_group_schedules(db_session, group_id, user.id, pause=False)
    await callback.answer("Guruhdagi barcha jadvallar yoqildi.", show_alert=True)


@router.callback_query(F.data.startswith("grp:unl:"))
async def confirm_unlink_group(
    callback: CallbackQuery, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    group_id = callback.data[8:]
    await callback.message.edit_text(
        t("group_unlink_confirm"),
        reply_markup=get_group_unlink_confirm_keyboard(group_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("grp:cf_unl:"))
async def execute_unlink_group(
    callback: CallbackQuery, user: User | None, db_session: AsyncSession
):
    if not user:
        await callback.answer(t("login_invalid_credentials"), show_alert=True)
        return

    group_id = callback.data[11:]
    success = await GroupService.unlink_group(db_session, group_id, user.id)
    if success:
        await callback.answer(t("group_unlinked_success"), show_alert=True)
    else:
        await callback.answer("Guruh topilmadi.", show_alert=True)

    groups = await GroupService.get_user_groups(db_session, user.id)
    await callback.message.edit_text(
        t("groups_list_title") + (t("groups_empty") if not groups else ""),
        reply_markup=get_groups_list_keyboard(groups),
        parse_mode="HTML",
    )


# --- Group Joining (/join) in Groups ---
@router.message(Command("join"), F.chat.type.in_({"group", "supergroup"}))
async def handle_join_command(
    message: Message, db_session: AsyncSession
):
    # Rate limit check on sender and chat
    sender_key = f"join:user:{message.from_user.id}"
    chat_key = f"join:chat:{message.chat.id}"

    is_sender_locked, rem_s = await AuthService.check_login_throttled(db_session, sender_key)
    is_chat_locked, rem_c = await AuthService.check_login_throttled(db_session, chat_key)

    if is_sender_locked or is_chat_locked:
        await message.reply(t("join_throttled"))
        await delete_message_safe(message)
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply("Kod ko'rsatilmadi. Masalan: /join <kod>")
        return

    raw_code = args[1].strip()

    # Check bot permissions in this group: bot must be an administrator
    try:
        bot_member = await message.chat.get_member(message.bot.id)
    except Exception:
        await message.reply(t("join_must_be_admin"), parse_mode="HTML")
        await delete_message_safe(message)
        return

    # In Telegram, status must be 'administrator' or 'creator'
    if bot_member.status not in {"administrator", "creator"}:
        await message.reply(t("join_must_be_admin"), parse_mode="HTML")
        await delete_message_safe(message)
        return

    # The bot is confirmed to be an administrator/creator above. In groups and
    # supergroups administrators can always send polls, so there is no
    # per-administrator "send polls" flag to verify against.
    # NOTE: `can_send_polls` only exists on restricted members, and
    # `can_post_messages` is a channels-only permission (it is `None`/`False`
    # for group administrators). Using either to reject an administrator was a
    # bug that made every admin /join fail with "missing permissions".
    can_send_polls = True
    if isinstance(bot_member, ChatMemberRestricted):
        can_send_polls = bool(bot_member.can_send_polls)

    if not can_send_polls:
        await message.reply(t("join_missing_permissions"), parse_mode="HTML")
        await delete_message_safe(message)
        return

    success, err_key, group = await GroupService.link_group_with_code(
        session=db_session,
        raw_code=raw_code,
        sender_telegram_id=message.from_user.id,
        chat_id=message.chat.id,
        chat_title=message.chat.title or "Telegram Group",
        chat_type=message.chat.type,
    )

    if not success:
        # Record failure throttling
        await AuthService.record_login_failure(db_session, sender_key)
        await AuthService.record_login_failure(db_session, chat_key)
        await message.reply(t(err_key))
        await delete_message_safe(message)
        return

    # Delete /join command message if bot has rights
    await delete_message_safe(message)

    # Confirm briefly in group
    await message.answer(t("join_success_group"))

    # Notify user privately
    try:
        await message.bot.send_message(
            chat_id=message.from_user.id,
            text=t("join_success_private", title=message.chat.title),
            parse_mode="HTML",
        )
    except Exception:
        pass


# --- my_chat_member updates ---
@router.my_chat_member()
async def handle_my_chat_member(
    update: ChatMemberUpdated, db_session: AsyncSession
):
    chat = update.chat
    if chat.type not in {"group", "supergroup"}:
        return

    new_status = update.new_chat_member.status
    is_active = new_status not in {"left", "kicked", "restricted"}

    await GroupService.record_or_update_group(
        session=db_session,
        chat_id=chat.id,
        title=chat.title or "Telegram Group",
        chat_type=chat.type,
        is_active=is_active,
    )


# --- Migration handler ---
@router.message(F.migrate_to_chat_id)
async def handle_migration(message: Message, db_session: AsyncSession):
    old_chat_id = message.chat.id
    new_chat_id = message.migrate_to_chat_id
    await GroupService.handle_supergroup_migration(db_session, old_chat_id, new_chat_id)
