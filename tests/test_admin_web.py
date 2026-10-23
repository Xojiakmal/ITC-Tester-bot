import pyotp
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.admin import AdminUser
from app.models.audit import AuditLog
from app.models.user import User
from app.services.admin_service import AdminService
from app.web.app import create_app
from app.config import get_settings

settings = get_settings()


@pytest.mark.asyncio
async def test_admin_authentication_and_totp_2fa(
    db_session: AsyncSession, admin_fixture: tuple[AdminUser, str]
):
    admin, totp_secret = admin_fixture

    # Test wrong password
    bad_pw_admin, err = await AdminService.authenticate_admin(
        db_session, admin.username, "WrongPassword!", pyotp.TOTP(totp_secret).now()
    )
    assert bad_pw_admin is None
    assert err is not None

    # Test wrong TOTP code
    bad_totp_admin, err = await AdminService.authenticate_admin(
        db_session, admin.username, "AdminPassword789!", "000000"
    )
    assert bad_totp_admin is None
    assert "2FA" in err

    # Test correct password + valid TOTP
    valid_code = pyotp.TOTP(totp_secret).now()
    good_admin, err = await AdminService.authenticate_admin(
        db_session, admin.username, "AdminPassword789!", valid_code
    )
    assert err is None
    assert good_admin is not None
    assert good_admin.id == admin.id


@pytest.mark.asyncio
async def test_admin_csrf_protection(
    db_session: AsyncSession, admin_fixture: tuple[AdminUser, str], user_a: User
):
    admin, totp_secret = admin_fixture

    # Create session
    raw_token, csrf_token = await AdminService.create_admin_session(
        db_session, admin.id
    )

    app = create_app()

    # Override database dependency for test
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set(settings.ADMIN_SESSION_COOKIE_NAME, raw_token)

        # 1. POST without CSRF token MUST return 403 Forbidden!
        res_no_csrf = await client.post(
            f"/admin/users/{user_a.id}/toggle-block",
            data={},
        )
        assert res_no_csrf.status_code == 403

        # 2. POST with INVALID CSRF token MUST return 403 Forbidden!
        res_bad_csrf = await client.post(
            f"/admin/users/{user_a.id}/toggle-block",
            data={"csrf_token": "tampered_fake_token_12345"},
        )
        assert res_bad_csrf.status_code == 403

        # 3. POST with VALID CSRF token succeeds with 303 Redirect!
        res_valid = await client.post(
            f"/admin/users/{user_a.id}/toggle-block",
            data={"csrf_token": csrf_token},
            follow_redirects=False,
        )
        assert res_valid.status_code == 303

        # Verify audit log was recorded
        audit_stmt = select(AuditLog).where(
            AuditLog.admin_id == admin.id, AuditLog.target_id == user_a.id
        )
        audit_res = await db_session.execute(audit_stmt)
        log = audit_res.scalars().first()
        assert log is not None
        assert log.action == "BLOCK_USER"
        assert log.details["after"] is True
