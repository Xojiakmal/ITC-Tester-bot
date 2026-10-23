import hashlib
import secrets
from datetime import timedelta, datetime
from typing import Optional, Tuple, Dict, Any, List
import pyotp
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.admin import AdminUser, AdminSession
from app.models.audit import AuditLog
from app.models.user import User, UserSession
from app.models.group import TelegramGroup
from app.models.question import Question, TestSet
from app.models.schedule import Schedule, ScheduleRun, PollSendLog
from app.models.base import utc_now
from app.services.auth_service import hash_password, verify_password, hash_token, ph

ADMIN_SESSION_HOURS = 12


class AdminService:
    @staticmethod
    async def create_admin(
        session: AsyncSession, username: str, password: str, totp_secret: Optional[str] = None
    ) -> Tuple[AdminUser, str]:
        """Create an admin user. Returns (admin, totp_secret)."""
        clean_user = username.strip().lower()
        secret = totp_secret or pyotp.random_base32()
        pw_hash = hash_password(password)

        admin = AdminUser(
            username=clean_user,
            password_hash=pw_hash,
            totp_secret=secret,
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        return admin, secret

    @staticmethod
    async def get_admin_by_username(session: AsyncSession, username: str) -> Optional[AdminUser]:
        stmt = select(AdminUser).where(func.lower(AdminUser.username) == username.strip().lower())
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def authenticate_admin(
        session: AsyncSession, username: str, password: str, totp_code: str
    ) -> Tuple[Optional[AdminUser], Optional[str]]:
        admin = await AdminService.get_admin_by_username(session, username)
        if not admin or not admin.is_active:
            return None, "Noto'g'ri login yoki parol."

        if not verify_password(password, admin.password_hash):
            return None, "Noto'g'ri login yoki parol."

        # Verify TOTP 2FA
        totp = pyotp.TOTP(admin.totp_secret)
        if not totp.verify(totp_code.strip(), valid_window=1):
            return None, "2FA TOTP kodi noto'g'ri yoki eskirgan."

        admin.last_login_at = utc_now()
        await session.commit()
        return admin, None

    @staticmethod
    async def create_admin_session(
        session: AsyncSession,
        admin_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Create session token and CSRF token. Returns (raw_session_token, csrf_token)."""
        raw_token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_hex(32)
        token_hash = hash_token(raw_token)
        expires_at = utc_now() + timedelta(hours=ADMIN_SESSION_HOURS)

        admin_session = AdminSession(
            admin_id=admin_id,
            session_token_hash=token_hash,
            csrf_token=csrf_token,
            ip_address=ip_address,
            user_agent=user_agent[:255] if user_agent else None,
            expires_at=expires_at,
            is_revoked=False,
        )
        session.add(admin_session)
        await session.commit()
        return raw_token, csrf_token

    @staticmethod
    async def validate_admin_session(
        session: AsyncSession, raw_token: str
    ) -> Tuple[Optional[AdminUser], Optional[AdminSession]]:
        if not raw_token:
            return None, None

        token_hash = hash_token(raw_token)
        now = utc_now()

        stmt = (
            select(AdminSession, AdminUser)
            .join(AdminUser, AdminSession.admin_id == AdminUser.id)
            .where(
                AdminSession.session_token_hash == token_hash,
                AdminSession.is_revoked.is_(False),
                AdminSession.expires_at > now,
                AdminUser.is_active.is_(True),
            )
        )
        result = await session.execute(stmt)
        row = result.first()
        if not row:
            return None, None

        admin_session, admin = row
        return admin, admin_session

    @staticmethod
    async def revoke_admin_session(session: AsyncSession, raw_token: str) -> None:
        token_hash = hash_token(raw_token)
        stmt = (
            update(AdminSession)
            .where(AdminSession.session_token_hash == token_hash)
            .values(is_revoked=True)
        )
        await session.execute(stmt)
        await session.commit()

    @staticmethod
    async def record_audit_log(
        session: AsyncSession,
        admin_id: Optional[str],
        action: str,
        target_type: str,
        target_id: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        log = AuditLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
            ip_address=ip_address,
            created_at=utc_now(),
        )
        session.add(log)
        await session.commit()

    @staticmethod
    async def get_dashboard_stats(session: AsyncSession) -> Dict[str, int]:
        users_count = (await session.execute(select(func.count(User.id)))).scalar_one() or 0
        groups_count = (await session.execute(select(func.count(TelegramGroup.id)))).scalar_one() or 0
        questions_count = (await session.execute(select(func.count(Question.id)))).scalar_one() or 0
        schedules_count = (await session.execute(select(func.count(Schedule.id)))).scalar_one() or 0
        runs_count = (await session.execute(select(func.count(ScheduleRun.id)))).scalar_one() or 0
        active_sessions = (
            await session.execute(
                select(func.count(UserSession.id)).where(
                    UserSession.is_revoked.is_(False),
                    UserSession.expires_at > utc_now(),
                )
            )
        ).scalar_one() or 0

        return {
            "users": users_count,
            "groups": groups_count,
            "questions": questions_count,
            "schedules": schedules_count,
            "runs": runs_count,
            "active_sessions": active_sessions,
        }
