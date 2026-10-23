import hmac
import hashlib
import secrets
from datetime import timedelta
from typing import Optional, Tuple, List
from sqlalchemy import select, update, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import TelegramGroup, JoinCode
from app.models.schedule import Schedule
from app.models.base import utc_now
from app.config import get_settings

settings = get_settings()

JOIN_CODE_EXPIRY_MINUTES = 15


def hash_join_code(code: str) -> str:
    """Generate keyed HMAC-SHA256 hash of join code."""
    return hmac.new(
        settings.JOIN_CODE_PEPPER.encode("utf-8"),
        code.strip().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class GroupService:
    @staticmethod
    async def count_user_groups(session: AsyncSession, owner_id: str) -> int:
        stmt = select(func.count(TelegramGroup.id)).where(TelegramGroup.owner_id == owner_id)
        result = await session.execute(stmt)
        return result.scalar_one() or 0

    @staticmethod
    async def get_user_groups(session: AsyncSession, owner_id: str) -> List[TelegramGroup]:
        stmt = (
            select(TelegramGroup)
            .where(TelegramGroup.owner_id == owner_id)
            .order_by(TelegramGroup.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_group_by_id(
        session: AsyncSession, group_id: str, owner_id: str
    ) -> Optional[TelegramGroup]:
        """Tenant-isolated group lookup."""
        stmt = select(TelegramGroup).where(
            TelegramGroup.id == group_id, TelegramGroup.owner_id == owner_id
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_group_by_chat_id(
        session: AsyncSession, chat_id: int
    ) -> Optional[TelegramGroup]:
        stmt = select(TelegramGroup).where(TelegramGroup.chat_id == chat_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def generate_join_code(session: AsyncSession, user_id: str) -> Tuple[str, str]:
        """Generate a fresh single-use join code with >=40 bits entropy and 15 min expiry.

        Returns (raw_code, join_code_id).
        """
        # 6 bytes = 48 bits of cryptographic entropy (hex representation = 12 characters)
        raw_code = secrets.token_hex(6)
        code_hash = hash_join_code(raw_code)
        expires_at = utc_now() + timedelta(minutes=JOIN_CODE_EXPIRY_MINUTES)

        join_code = JoinCode(
            user_id=user_id,
            code_hash=code_hash,
            expires_at=expires_at,
            is_used=False,
        )
        session.add(join_code)
        await session.commit()
        return raw_code, join_code.id

    @staticmethod
    async def link_group_with_code(
        session: AsyncSession,
        raw_code: str,
        sender_telegram_id: int,
        chat_id: int,
        chat_title: str,
        chat_type: str,
    ) -> Tuple[bool, Optional[str], Optional[TelegramGroup]]:
        """Validate join code, sender identity, and link group."""
        code_hash = hash_join_code(raw_code)
        now = utc_now()

        # Find code
        stmt = select(JoinCode).where(
            JoinCode.code_hash == code_hash,
            JoinCode.is_used.is_(False),
            JoinCode.expires_at > now,
        )
        result = await session.execute(stmt)
        join_code = result.scalars().first()

        if not join_code:
            return False, "join_code_invalid", None

        # Check sender's telegram ID equals the join code owner's telegram ID
        user_stmt = select(join_code.user.__class__).where(join_code.user.__class__.id == join_code.user_id)
        user_res = await session.execute(user_stmt)
        owner_user = user_res.scalars().first()

        if not owner_user or owner_user.telegram_id != sender_telegram_id:
            return False, "join_not_owner", None

        # Check user quota
        current_groups_count = await GroupService.count_user_groups(session, owner_user.id)
        if current_groups_count >= settings.MAX_GROUPS_PER_USER:
            return False, "group_quota_exceeded", None

        # Check if group already exists in DB
        group_stmt = select(TelegramGroup).where(TelegramGroup.chat_id == chat_id)
        group_res = await session.execute(group_stmt)
        group = group_res.scalars().first()

        if group:
            if group.owner_id and group.owner_id != owner_user.id:
                return False, "join_group_already_linked", None
            group.owner_id = owner_user.id
            group.title = chat_title
            group.chat_type = chat_type
            group.is_active = True
            group.linked_at = now
        else:
            group = TelegramGroup(
                owner_id=owner_user.id,
                chat_id=chat_id,
                title=chat_title,
                chat_type=chat_type,
                is_active=True,
                can_send_polls=True,
                linked_at=now,
            )
            session.add(group)

        # Mark join code as used
        join_code.is_used = True
        join_code.used_at = now
        join_code.used_in_chat_id = chat_id

        await session.commit()
        await session.refresh(group)
        return True, None, group

    @staticmethod
    async def unlink_group(
        session: AsyncSession, group_id: str, owner_id: str
    ) -> bool:
        """Unlink a group from user's cabinet, pausing and deleting all its schedules."""
        group = await GroupService.get_group_by_id(session, group_id, owner_id)
        if not group:
            return False

        # Delete all schedules associated with this group
        del_sched = delete(Schedule).where(Schedule.group_id == group.id)
        await session.execute(del_sched)

        # Clear group owner
        group.owner_id = None
        group.linked_at = None
        await session.commit()
        return True

    @staticmethod
    async def toggle_group_schedules(
        session: AsyncSession, group_id: str, owner_id: str, pause: bool
    ) -> bool:
        """Pause or resume all schedules in a group for owner."""
        group = await GroupService.get_group_by_id(session, group_id, owner_id)
        if not group:
            return False

        stmt = (
            update(Schedule)
            .where(Schedule.group_id == group.id, Schedule.owner_id == owner_id)
            .values(is_paused=pause)
        )
        await session.execute(stmt)
        await session.commit()
        return True

    @staticmethod
    async def record_or_update_group(
        session: AsyncSession, chat_id: int, title: str, chat_type: str, is_active: bool
    ) -> TelegramGroup:
        """Handle my_chat_member status update."""
        stmt = select(TelegramGroup).where(TelegramGroup.chat_id == chat_id)
        result = await session.execute(stmt)
        group = result.scalars().first()

        now = utc_now()
        if group:
            group.title = title
            group.chat_type = chat_type
            group.is_active = is_active
            group.updated_at = now
            if not is_active:
                # Pause all schedules if bot is kicked/removed
                pause_stmt = (
                    update(Schedule)
                    .where(Schedule.group_id == group.id)
                    .values(is_paused=True)
                )
                await session.execute(pause_stmt)
        else:
            group = TelegramGroup(
                owner_id=None,
                chat_id=chat_id,
                title=title,
                chat_type=chat_type,
                is_active=is_active,
                can_send_polls=True,
            )
            session.add(group)

        await session.commit()
        await session.refresh(group)
        return group

    @staticmethod
    async def handle_supergroup_migration(
        session: AsyncSession, old_chat_id: int, new_chat_id: int
    ) -> None:
        """Handle group to supergroup migration."""
        stmt = select(TelegramGroup).where(TelegramGroup.chat_id == old_chat_id)
        result = await session.execute(stmt)
        group = result.scalars().first()

        if group:
            group.chat_id = new_chat_id
            group.chat_type = "supergroup"
            group.updated_at = utc_now()
            await session.commit()
