import argparse
import asyncio
import getpass
import sys
import pyotp
import qrcode
from app.database import AsyncSessionLocal
from app.services.admin_service import AdminService
from app.services.auth_service import validate_password_strength


async def create_admin_command(username: str, password: str | None = None):
    clean_username = username.strip().lower()
    if not clean_username:
        print("Error: Username cannot be empty.")
        sys.exit(1)

    if not password:
        password = getpass.getpass(prompt="Enter Admin Password: ")
        confirm_pw = getpass.getpass(prompt="Confirm Admin Password: ")
        if password != confirm_pw:
            print("Error: Passwords do not match.")
            sys.exit(1)

    valid, err = validate_password_strength(password)
    if not valid:
        print(f"Warning: Password might be weak ({err}), but proceeding as admin.")

    totp_secret = pyotp.random_base32()
    totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(
        name=clean_username, issuer_name="ITTestBot"
    )

    async with AsyncSessionLocal() as session:
        existing = await AdminService.get_admin_by_username(session, clean_username)
        if existing:
            print(f"Error: Admin '{clean_username}' already exists.")
            sys.exit(1)

        admin, secret = await AdminService.create_admin(
            session=session,
            username=clean_username,
            password=password,
            totp_secret=totp_secret,
        )

        await AdminService.record_audit_log(
            session=session,
            admin_id=admin.id,
            action="CREATE_ADMIN_CLI",
            target_type="admin",
            target_id=admin.id,
            details={"username": clean_username},
            ip_address="127.0.0.1",
        )

    print("\n" + "=" * 50)
    print(" Admin User Created Successfully!")
    print("=" * 50)
    print(f" Username    : {clean_username}")
    print(f" TOTP Secret : {totp_secret}")
    print(f" OTPAuth URI : {totp_uri}")
    print("=" * 50)
    print("\nScan this QR code in your Authenticator app (Google Authenticator, Aegis, 1Password):")

    qr = qrcode.QRCode()
    qr.add_data(totp_uri)
    qr.print_ascii(invert=True)

    print("\nKeep this TOTP secret safe! It is required for web panel login.\n")


def main():
    parser = argparse.ArgumentParser(description="ITTestBot Management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create-admin
    admin_parser = subparsers.add_parser("create-admin", help="Create an admin user for the web panel")
    admin_parser.add_argument("--username", "-u", required=True, help="Admin username")
    admin_parser.add_argument("--password", "-p", default=None, help="Admin password (prompts if omitted)")

    args = parser.parse_args()

    if args.command == "create-admin":
        asyncio.run(create_admin_command(args.username, args.password))


if __name__ == "__main__":
    main()
