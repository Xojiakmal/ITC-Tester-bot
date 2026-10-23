from datetime import timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.base import utc_now
from app.services.auth_service import (
    AuthService,
    validate_username,
    validate_password_strength,
    verify_password,
)


@pytest.mark.asyncio
async def test_username_validation():
    assert validate_username("valid_user123") is True
    assert validate_username("abc") is True
    assert validate_username("ab") is False  # too short (<3)
    assert validate_username("a" * 33) is False  # too long (>32)
    assert validate_username("invalid-user") is False  # hyphen not allowed
    assert validate_username("user name") is False  # space not allowed


@pytest.mark.asyncio
async def test_password_strength_and_common_rejection():
    # Too short (<10 chars)
    valid, err = validate_password_strength("Short1!")
    assert valid is False
    assert err == "reg_password_too_short"

    # Common passwords blacklist
    valid, err = validate_password_strength("1234567890")
    assert valid is False
    assert err == "reg_password_too_common"

    valid, err = validate_password_strength("password123")
    assert valid is False
    assert err == "reg_password_too_common"

    valid, err = validate_password_strength("telegram123")
    assert valid is False
    assert err == "reg_password_too_common"

    # Low entropy
    valid, err = validate_password_strength("aaaaaaaaaaa")
    assert valid is False
    assert err == "reg_password_too_common"

    # Strong password
    valid, err = validate_password_strength("SecureP@ssw0rd2026!")
    assert valid is True
    assert err is None


@pytest.mark.asyncio
async def test_user_registration_and_argon2(db_session: AsyncSession):
    user, err = await AuthService.register_user(
        db_session,
        telegram_id=987654321,
        username="SecurityHero",
        password="MyStrongPassword123#",
    )
    assert err is None
    assert user is not None
    assert user.username == "SecurityHero"

    # Argon2id verification
    assert user.password_hash.startswith("$argon2id$")
    assert verify_password("MyStrongPassword123#", user.password_hash) is True
    assert verify_password("WrongPassword!", user.password_hash) is False

    # Unique username case-insensitively
    dup_user, dup_err = await AuthService.register_user(
        db_session,
        telegram_id=987654322,
        username="securityhero",  # lowercase duplicate
        password="AnotherPassword123#",
    )
    assert dup_user is None
    assert dup_err == "reg_username_taken"

    # One account per Telegram ID
    tg_dup, tg_err = await AuthService.register_user(
        db_session,
        telegram_id=987654321,  # same telegram ID
        username="different_name",
        password="AnotherPassword123#",
    )
    assert tg_dup is None
    assert tg_err == "reg_already_have_account"


@pytest.mark.asyncio
async def test_session_lifecycle_and_logout_everywhere(
    db_session: AsyncSession, user_a: User
):
    # Create two sessions for user_a (e.g. desktop and mobile)
    token_1 = await AuthService.create_user_session(db_session, user_a.id)
    token_2 = await AuthService.create_user_session(db_session, user_a.id)

    # Both tokens are valid
    valid_u1 = await AuthService.validate_session(db_session, token_1)
    valid_u2 = await AuthService.validate_session(db_session, token_2)
    assert valid_u1 is not None and valid_u1.id == user_a.id
    assert valid_u2 is not None and valid_u2.id == user_a.id

    # Single logout revokes only token_1
    await AuthService.revoke_session(db_session, token_1)
    assert await AuthService.validate_session(db_session, token_1) is None
    assert await AuthService.validate_session(db_session, token_2) is not None

    # Log out everywhere revokes token_2 as well
    await AuthService.revoke_all_user_sessions(db_session, user_a.id)
    assert await AuthService.validate_session(db_session, token_2) is None


@pytest.mark.asyncio
async def test_login_throttling_exponential_backoff(db_session: AsyncSession):
    identifier = "tg:9999999"

    # Initial state
    locked, rem = await AuthService.check_login_throttled(db_session, identifier)
    assert locked is False

    # Attempts 1 and 2
    wait1 = await AuthService.record_login_failure(db_session, identifier)
    assert wait1 == 0
    wait2 = await AuthService.record_login_failure(db_session, identifier)
    assert wait2 == 0

    # Attempt 3: triggers 15s lock
    wait3 = await AuthService.record_login_failure(db_session, identifier)
    assert wait3 == 15
    locked, rem = await AuthService.check_login_throttled(db_session, identifier)
    assert locked is True
    assert 0 < rem <= 15

    # Attempt 4: triggers 30s lock
    wait4 = await AuthService.record_login_failure(db_session, identifier)
    assert wait4 == 30

    # Clear on success
    await AuthService.record_login_success(db_session, identifier)
    locked, _ = await AuthService.check_login_throttled(db_session, identifier)
    assert locked is False


@pytest.mark.asyncio
async def test_active_user_session_persistence_and_logout(
    db_session: AsyncSession, user_a: User
):
    # Before session creation, user has no active session
    active_user, sess = await AuthService.get_active_user_and_session_by_telegram_id(
        db_session, user_a.telegram_id
    )
    assert active_user is None
    assert sess is None

    # User logs in / creates session
    token = await AuthService.create_user_session(db_session, user_a.id)
    assert token is not None

    # Now get_active_user_and_session_by_telegram_id resolves the user
    active_user, sess = await AuthService.get_active_user_and_session_by_telegram_id(
        db_session, user_a.telegram_id
    )
    assert active_user is not None
    assert active_user.id == user_a.id
    assert sess is not None
    assert sess.is_revoked is False

    # A second request resolves the same user (persistent session, e.g. after /start or menu navigation)
    active_user_2, sess_2 = await AuthService.get_active_user_and_session_by_telegram_id(
        db_session, user_a.telegram_id
    )
    assert active_user_2 is not None
    assert active_user_2.id == user_a.id

    # If user is blocked, active session returns None immediately
    user_a.is_blocked = True
    await db_session.commit()
    blocked_user, _ = await AuthService.get_active_user_and_session_by_telegram_id(
        db_session, user_a.telegram_id
    )
    assert blocked_user is None

    # Unblock
    user_a.is_blocked = False
    await db_session.commit()

    # User clicks 'Chiqish' (logout): revoke all sessions
    await AuthService.revoke_all_user_sessions(db_session, user_a.id)

    # Now user is logged out: no active session found
    logged_out_user, logged_out_sess = await AuthService.get_active_user_and_session_by_telegram_id(
        db_session, user_a.telegram_id
    )
    assert logged_out_user is None
    assert logged_out_sess is None

