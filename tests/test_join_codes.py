from datetime import timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.group import JoinCode
from app.models.base import utc_now
from app.services.group_service import GroupService, hash_join_code


@pytest.mark.asyncio
async def test_join_code_generation_and_hash_storage(
    db_session: AsyncSession, user_a: User
):
    raw_code, code_id = await GroupService.generate_join_code(db_session, user_a.id)

    # 48 bits of entropy (12 hex characters)
    assert len(raw_code) == 12

    # Check database record: must NOT contain plaintext code!
    stmt = select(JoinCode).where(JoinCode.id == code_id)
    res = await db_session.execute(stmt)
    record = res.scalars().first()

    assert record is not None
    assert record.code_hash != raw_code
    assert record.code_hash == hash_join_code(raw_code)
    assert record.is_used is False


@pytest.mark.asyncio
async def test_join_code_expiry(db_session: AsyncSession, user_a: User):
    raw_code, code_id = await GroupService.generate_join_code(db_session, user_a.id)

    # Manually expire code by setting expires_at to past
    stmt = select(JoinCode).where(JoinCode.id == code_id)
    res = await db_session.execute(stmt)
    record = res.scalars().first()
    record.expires_at = utc_now() - timedelta(minutes=1)
    await db_session.commit()

    # Attempting to use expired code fails
    success, err, _ = await GroupService.link_group_with_code(
        session=db_session,
        raw_code=raw_code,
        sender_telegram_id=user_a.telegram_id,
        chat_id=-1005555555,
        chat_title="Test Group",
        chat_type="supergroup",
    )
    assert success is False
    assert err == "join_code_invalid"


@pytest.mark.asyncio
async def test_join_code_single_use(db_session: AsyncSession, user_a: User):
    raw_code, code_id = await GroupService.generate_join_code(db_session, user_a.id)

    # First use succeeds
    success_1, err_1, grp = await GroupService.link_group_with_code(
        session=db_session,
        raw_code=raw_code,
        sender_telegram_id=user_a.telegram_id,
        chat_id=-1006666666,
        chat_title="First Group",
        chat_type="supergroup",
    )
    assert success_1 is True
    assert err_1 is None

    # Second use of same code MUST FAIL
    success_2, err_2, _ = await GroupService.link_group_with_code(
        session=db_session,
        raw_code=raw_code,
        sender_telegram_id=user_a.telegram_id,
        chat_id=-1007777777,
        chat_title="Second Group",
        chat_type="supergroup",
    )
    assert success_2 is False
    assert err_2 == "join_code_invalid"


@pytest.mark.asyncio
async def test_join_command_requires_bot_admin(db_session: AsyncSession, user_a: User):
    from unittest.mock import AsyncMock, MagicMock
    from app.bot.handlers.group_handlers import handle_join_command
    from app.locales.uz import t

    raw_code, _ = await GroupService.generate_join_code(db_session, user_a.id)

    # 1. Bot is only a regular member (not admin)
    mock_chat = MagicMock()
    mock_chat.id = -1008888888
    mock_chat.title = "Non-Admin Group"
    mock_chat.type = "supergroup"

    member_mock = MagicMock()
    member_mock.status = "member"  # regular member!
    mock_chat.get_member = AsyncMock(return_value=member_mock)

    mock_msg = MagicMock()
    mock_msg.chat = mock_chat
    mock_msg.from_user.id = user_a.telegram_id
    mock_msg.text = f"/join {raw_code}"
    mock_msg.bot.id = 123456789
    mock_msg.reply = AsyncMock()
    mock_msg.answer = AsyncMock()
    mock_msg.delete = AsyncMock()

    await handle_join_command(mock_msg, db_session)

    # Must reject with join_must_be_admin
    mock_msg.reply.assert_called_once_with(t("join_must_be_admin"), parse_mode="HTML")
    # Must NOT send success confirmation
    mock_msg.answer.assert_not_called()

    # Verify group was NOT linked
    group = await GroupService.get_group_by_chat_id(db_session, -1008888888)
    assert group is None or group.owner_id != user_a.id

    # 2. Now bot is promoted to administrator with can_send_polls=True
    admin_mock = MagicMock()
    admin_mock.status = "administrator"
    admin_mock.can_send_polls = True
    admin_mock.can_post_messages = True
    mock_chat.get_member = AsyncMock(return_value=admin_mock)

    mock_msg.reply.reset_mock()
    mock_msg.answer.reset_mock()
    mock_msg.bot.send_message = AsyncMock()

    await handle_join_command(mock_msg, db_session)

    # Must confirm success in group and privately
    mock_msg.answer.assert_called_once_with(t("join_success_group"))
    linked_group = await GroupService.get_group_by_chat_id(db_session, -1008888888)
    assert linked_group is not None
    assert linked_group.owner_id == user_a.id

