import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserSession, LoginAttempt
from app.models.base import utc_now, ensure_utc

ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    type=Type.ID,
)

COMMON_PASSWORDS = {
    "1234567890",
    "12345678910",
    "password123",
    "password1234",
    "qwertyuiop",
    "qwertyuiop1",
    "admin12345",
    "administrator",
    "telegram123",
    "iloveyou123",
    "welcome1234",
    "letmein1234",
    "monkey12345",
    "dragon12345",
    "football123",
    "master12345",
    "trustno1123",
    "passwords123",
    "testpassword",
    "ittestbot123",
}

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
SESSION_EXPIRY_DAYS = 7


def validate_username(username: str) -> bool:
    return bool(USERNAME_REGEX.match(username))


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    if len(password) < 10:
        return False, "reg_password_too_short"
    if password.lower() in COMMON_PASSWORDS:
        return False, "reg_password_too_common"
    # Basic check for repeated characters like 'aaaaaaaaaa'
    if len(set(password)) < 3:
        return False, "reg_password_too_common"
    return True, None


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    @staticmethod
    async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
        stmt = select(User).where(func.lower(User.username) == username.lower().strip())
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: str) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def check_login_throttled(session: AsyncSession, identifier: str) -> Tuple[bool, int]:
        """Check if identifier (tg:ID or user:username) is throttled. Returns (is_locked, remaining_seconds)."""
        now = utc_now()
        stmt = select(LoginAttempt).where(LoginAttempt.identifier == identifier)
        result = await session.execute(stmt)
        attempt = result.scalars().first()

        if not attempt:
            return False, 0

        locked_until = ensure_utc(attempt.locked_until)
        if locked_until and locked_until > now:
            remaining = int((locked_until - now).total_seconds())
            return True, max(1, remaining)

        # If previous lock expired long ago (e.g. > 15 mins), reset attempts
        last_att = ensure_utc(attempt.last_attempt_at)
        if last_att and (now - last_att) > timedelta(minutes=15):
            attempt.attempt_count = 0
            attempt.locked_until = None
            await session.commit()
            return False, 0

        return False, 0

    @staticmethod
    async def record_login_failure(session: AsyncSession, identifier: str) -> int:
        """Record failure and apply exponential backoff. Returns wait seconds."""
        now = utc_now()
        stmt = select(LoginAttempt).where(LoginAttempt.identifier == identifier)
        result = await session.execute(stmt)
        attempt = result.scalars().first()

        if not attempt:
            attempt = LoginAttempt(
                identifier=identifier,
                attempt_count=1,
                last_attempt_at=now,
            )
            session.add(attempt)
            await session.commit()
            return 0

        attempt.attempt_count += 1
        attempt.last_attempt_at = now

        # Exponential backoff:
        # attempts 1-2: 0s
        # attempt 3: 15s
        # attempt 4: 30s
        # attempt 5: 60s
        # attempt 6+: 300s (5 mins)
        lock_seconds = 0
        if attempt.attempt_count == 3:
            lock_seconds = 15
        elif attempt.attempt_count == 4:
            lock_seconds = 30
        elif attempt.attempt_count == 5:
            lock_seconds = 60
        elif attempt.attempt_count >= 6:
            lock_seconds = 300

        if lock_seconds > 0:
            attempt.locked_until = now + timedelta(seconds=lock_seconds)

        await session.commit()
        return lock_seconds

    @staticmethod
    async def record_login_success(session: AsyncSession, identifier: str) -> None:
        """Clear login attempts on successful authentication."""
        stmt = delete(LoginAttempt).where(LoginAttempt.identifier == identifier)
        await session.execute(stmt)
        await session.commit()

    @staticmethod
    async def register_user(
        session: AsyncSession, telegram_id: int, username: str, password: str
    ) -> Tuple[Optional[User], Optional[str]]:
        # Check if Telegram ID already has an account
        existing_tg = await AuthService.get_user_by_telegram_id(session, telegram_id)
        if existing_tg:
            return None, "reg_already_have_account"

        # Check username format
        username_clean = username.strip()
        if not validate_username(username_clean):
            return None, "reg_username_invalid"

        # Check unique username case-insensitively
        existing_username = await AuthService.get_user_by_username(session, username_clean)
        if existing_username:
            return None, "reg_username_taken"

        # Validate password strength
        valid_pw, err_key = validate_password_strength(password)
        if not valid_pw:
            return None, err_key

        # Hash with Argon2id
        hashed_password = hash_password(password)

        user = User(
            telegram_id=telegram_id,
            username=username_clean,
            password_hash=hashed_password,
            timezone="Asia/Tashkent",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user, None

    @staticmethod
    async def create_user_session(session: AsyncSession, user_id: str) -> str:
        """Create a server-side session token with 7-day idle expiry."""
        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_token(raw_token)
        expires_at = utc_now() + timedelta(days=SESSION_EXPIRY_DAYS)

        user_session = UserSession(
            user_id=user_id,
            session_token_hash=token_hash,
            expires_at=expires_at,
            last_active_at=utc_now(),
            is_revoked=False,
        )
        session.add(user_session)
        await session.commit()
        return raw_token

    @staticmethod
    async def validate_session(session: AsyncSession, raw_token: str) -> Optional[User]:
        """Validate session token, check expiry, update last_active_at."""
        if not raw_token:
            return None

        token_hash = hash_token(raw_token)
        now = utc_now()

        stmt = (
            select(UserSession, User)
            .join(User, UserSession.user_id == User.id)
            .where(
                UserSession.session_token_hash == token_hash,
                UserSession.is_revoked.is_(False),
                UserSession.expires_at > now,
                User.is_blocked.is_(False),
            )
        )
        result = await session.execute(stmt)
        row = result.first()
        if not row:
            return None

        user_session, user = row
        # Update last_active_at and slide expiration window
        user_session.last_active_at = now
        user_session.expires_at = now + timedelta(days=SESSION_EXPIRY_DAYS)
        await session.commit()
        return user

    @staticmethod
    async def get_active_user_and_session_by_telegram_id(
        session: AsyncSession, telegram_id: int
    ) -> Tuple[Optional[User], Optional[UserSession]]:
        """Look up user by telegram_id and verify active (unrevoked, unexpired) session."""
        now = utc_now()
        stmt = (
            select(User, UserSession)
            .join(UserSession, UserSession.user_id == User.id)
            .where(
                User.telegram_id == telegram_id,
                UserSession.is_revoked.is_(False),
                UserSession.expires_at > now,
                User.is_blocked.is_(False),
            )
            .order_by(UserSession.last_active_at.desc())
        )
        result = await session.execute(stmt)
        row = result.first()
        if not row:
            return None, None

        user, user_session = row
        user_session.last_active_at = now
        user_session.expires_at = now + timedelta(days=SESSION_EXPIRY_DAYS)
        await session.commit()
        return user, user_session

    @staticmethod
    async def revoke_session(session: AsyncSession, raw_token: str) -> None:
        """Revoke a single session token."""
        token_hash = hash_token(raw_token)
        stmt = (
            update(UserSession)
            .where(UserSession.session_token_hash == token_hash)
            .values(is_revoked=True)
        )
        await session.execute(stmt)
        await session.commit()

    @staticmethod
    async def revoke_all_user_sessions(session: AsyncSession, user_id: str) -> None:
        """Log out everywhere: revoke all active sessions for this user."""
        stmt = (
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.is_revoked.is_(False))
            .values(is_revoked=True)
        )
        await session.execute(stmt)
        await session.commit()

    @staticmethod
    async def change_password(
        session: AsyncSession, user: User, old_password: str, new_password: str
    ) -> Tuple[bool, Optional[str]]:
        if not verify_password(old_password, user.password_hash):
            return False, "chpass_old_wrong"

        valid_pw, err_key = validate_password_strength(new_password)
        if not valid_pw:
            return False, err_key

        user.password_hash = hash_password(new_password)
        # Invalidate other sessions on password change for security
        await AuthService.revoke_all_user_sessions(session, user.id)
        await session.commit()
        return True, None

    @staticmethod
    async def delete_user_account(session: AsyncSession, user_id: str) -> None:
        """Permanently delete user and all associated data."""
        stmt = delete(User).where(User.id == user_id)
        await session.execute(stmt)
        await session.commit()
