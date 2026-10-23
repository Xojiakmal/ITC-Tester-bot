import os
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event

# Set testing environment variables before importing app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test_secret_key_32_bytes_long_random_hex_12345"
os.environ["JOIN_CODE_PEPPER"] = "test_pepper_key_32_bytes_long_random_hex_67890"
os.environ["BOT_TOKEN"] = "123456789:TEST_BOT_TOKEN_FIXTURE"

from app.models.base import Base
from app.models.user import User, UserSession
from app.models.group import TelegramGroup, JoinCode
from app.models.question import Question, TestSet
from app.models.schedule import Schedule, ScheduleRun, ScheduleSentQuestion, PollSendLog
from app.models.admin import AdminUser, AdminSession
from app.models.audit import AuditLog
from app.services.auth_service import AuthService, hash_password
from app.services.admin_service import AdminService
import pyotp


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine):
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def user_a(db_session: AsyncSession) -> User:
    user, _ = await AuthService.register_user(
        db_session,
        telegram_id=111111,
        username="user_alice",
        password="ValidPassword123!",
    )
    return user


@pytest_asyncio.fixture(scope="function")
async def user_b(db_session: AsyncSession) -> User:
    user, _ = await AuthService.register_user(
        db_session,
        telegram_id=222222,
        username="user_bob",
        password="ValidPassword456!",
    )
    return user


@pytest_asyncio.fixture(scope="function")
async def admin_fixture(db_session: AsyncSession) -> tuple[AdminUser, str]:
    totp_secret = pyotp.random_base32()
    admin, secret = await AdminService.create_admin(
        db_session,
        username="superadmin",
        password="AdminPassword789!",
        totp_secret=totp_secret,
    )
    return admin, secret
