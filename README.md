# ITTestBot — Telegram Bot Quiz Scheduler & Web Admin Panel

ITTestBot is a secure, multi-tenant Telegram bot and web administrative system that allows registered educators, tutors, and group owners to manage their question banks, organize test sets, link Telegram groups via cryptographic join codes, and post native Telegram quiz polls on flexible schedules.

> 📖 **Foydalanuvchi qo'llanmasi (bot va admin panel uchun):** [FOYDALANISH.md](FOYDALANISH.md)

---

## Tech Stack Justification
> **Python 3.12+ (asyncio)** with **aiogram 3** (native Bot API 7.x, async FSM), **FastAPI** (high-performance typed web framework for admin & webhooks), **SQLAlchemy 2.0 + Alembic** (robust async ORM with schema migrations supporting SQLite locally and PostgreSQL in production), and a **database-backed atomic scheduler queue** (using `SELECT FOR UPDATE SKIP LOCKED` / atomic row transitions). This provides maximum reliability across restarts, zero double-posting across multi-worker deployments, zero external broker dependencies (no Redis/Celery required), and minimal VPS resource footprint.

---

## Key Features

1. **Telegram User Accounts & Security**:
   - Accounts permanently bound to Telegram user IDs (1 Telegram account = 1 user).
   - Passwords hashed with **Argon2id** (memory=64MB, time=3, parallelism=4).
   - Rejection of weak and common passwords.
   - Immediate message deletion for all password inputs.
   - Throttled failed logins (per Telegram ID & username) with exponential backoff.
   - Server-side sessions with 7-day idle expiry, logout, and "log out everywhere".
   - Database-persisted FSM conversation state surviving bot restarts.

2. **Personal Cabinet (Uzbek Latin UI)**:
   - Centralized localization file (`app/locales/uz.py`).
   - **Guruhlarim**: Linked groups status, pause/resume group schedules, unlink.
   - **Guruh qo'shish**: Ephemeral 15-minute join codes (HMAC-SHA256 hashed).
   - **Savollarim**: Guided question creator (2-10 options, correct answer, explanation), pagination, search, test sets, CSV bulk import with template.
   - **Jadvallar**: Recurring (weekdays + time) and one-time schedules with IANA timezone support, non-repeating random or sequential pool modes.
   - **Sozlamalar**: Change timezone, change password, invalidate all sessions, delete account.

3. **Secure Group Linking (`/join`)**:
   - Bot privacy mode stays ON; reacts only to `/join <code>` and `/join@<bot_username> <code>`.
   - Checks sender identity against code owner, ensures group unlinked, verifies bot quiz permissions (`can_send_polls`).
   - Tracks `my_chat_member` events and handles group to supergroup migrations.

4. **Persistent Scheduler & Quiz Poster**:
   - Computes next occurrences in UTC based on owner's IANA timezone.
   - Atomic worker claim prevents duplicate postings even across multiple instances.
   - 10-minute grace window for overdue runs.
   - Handles Telegram rate limits (`retry_after` backoff).
   - Automatically detects bot removal/kick: deactivates group, pauses schedules, and alerts owner privately.

5. **Web Admin Panel**:
   - Dedicated administration with mandatory **TOTP 2FA** (RFC 6238).
   - Strict cookies (`HttpOnly`, `SameSite=Lax`, `Secure`).
   - CSRF token validation on all state-changing endpoints.
   - Comprehensive Security Headers (`Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`).
   - Full CRUD over users (block/unblock, force logout, re-bind Telegram ID, delete), groups (unlink/delete), questions (search/edit/delete), and schedules (pause/resume/delete).
   - Append-only audit trail logging every admin action with before/after state diffs and IP addresses.

---

## Threat Model & Security Architecture

| Threat | Mitigation |
| :--- | :--- |
| **Cross-Tenant Data Tampering (IDOR)** | All queries strictly filter by `owner_id == authenticated_user_id`. UUIDs are used for all IDs to prevent enumeration. `callback_data` and parameters are treated as untrusted. |
| **Credential Stuffing & Brute Force** | Password inputs deleted immediately. Argon2id hashing with strong parameters. Exponential backoff rate limiting per Telegram ID, username, and IP. Generic error messages. |
| **CSRF in Admin Panel** | Anti-CSRF tokens generated per admin session and enforced on all state-changing POST requests. |
| **Group Data Snooping** | Bot Privacy Mode remains enabled. Bot never reads, logs, or stores arbitrary group chat messages. |
| **Replay / Join-Code Theft** | Join codes possess >=40 bits entropy, expire in 15 minutes, are single-use, and stored only as keyed HMAC-SHA256 hashes. Sender Telegram ID must match code owner. |
| **Double-Posting on Crash / Restart** | Atomic database transaction transitions `ScheduleRun` from `PENDING` to `PROCESSING`. Missed runs outside the 10-minute grace window are marked `SKIPPED`. |

---

## Quick Start (Local Setup)

### 1. Prerequisites
- Python 3.11+
- Virtual environment tool

### 2. Installation
```bash
git clone <repository_url>
cd ITTestBot

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the template and fill in your values:
```bash
cp .env.example .env
```
Generate secure random keys:
```bash
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
python -c "import secrets; print('JOIN_CODE_PEPPER=' + secrets.token_hex(32))"
```
Edit `.env` and set:
- `BOT_TOKEN`: Your Telegram Bot API token from [@BotFather](https://t.me/BotFather).
- `SECRET_KEY`: Random 64-character hex string.
- `JOIN_CODE_PEPPER`: Random 64-character hex string.
- `DATABASE_URL`: `sqlite+aiosqlite:///./ittestbot.db` (for SQLite) or PostgreSQL URL.

### 4. Database Migrations
Run Alembic migrations to create the database schema:
```bash
alembic upgrade head
```

### 5. Create First Admin User
Create your admin credentials and generate the 2FA TOTP secret:
```bash
python -m app.cli create-admin --username admin --password "YourStrongAdminPassword123!"
```
*Scan the generated QR code in Google Authenticator, Aegis, or 1Password.*

### 6. Run the Application
```bash
python -m app.main
```
- Web Admin Panel: `http://localhost:8000/admin`
- Telegram Bot: Polling starts automatically when `WEBHOOK_URL` is empty.

---

## Running with Docker Compose (Production)

### 1. Configure `.env`
Edit `.env`:
```ini
BOT_TOKEN=your_telegram_bot_token
SECRET_KEY=your_secure_secret_key
JOIN_CODE_PEPPER=your_secure_pepper
ENVIRONMENT=production
COOKIE_SECURE=true

# PostgreSQL configuration
POSTGRES_USER=ittestuser
POSTGRES_PASSWORD=strong_postgres_password
POSTGRES_DB=ittestdb
```

### 2. Start Services
```bash
docker compose up -d --build
```

### 3. Create First Admin in Container
```bash
docker compose exec app python -m app.cli create-admin --username admin
```

---

## Telegram Webhook Setup (Production HTTPS)

For high-concurrency production deployments behind a reverse proxy (e.g., Caddy, Nginx):
1. In `.env`:
   ```ini
   WEBHOOK_URL=https://yourdomain.com
   WEBHOOK_SECRET_TOKEN=secure_random_token_header
   ```
2. Restart the app. The bot will automatically register the webhook endpoint at `https://yourdomain.com/tg/webhook` with the secret header.

---

## Testing

Run the full automated test suite verifying tenant isolation, auth throttling, join-code security, scheduler atomicity, CSRF, and admin operations:
```bash
pytest tests/ -v
```

---

## Database Backup & Restore

### SQLite
- **Backup**:
  ```bash
  sqlite3 ittestbot.db ".backup 'ittestbot_backup_$(date +%Y%m%d_%H%M%S).db'"
  ```
- **Restore**:
  ```bash
  cp ittestbot_backup_YYYYMMDD_HHMMSS.db ittestbot.db
  ```

### PostgreSQL (Docker)
- **Backup**:
  ```bash
  docker compose exec postgres pg_dump -U ittestuser ittestdb > backup_$(date +%Y%m%d_%H%M%S).sql
  ```
- **Restore**:
  ```bash
  cat backup_YYYYMMDD_HHMMSS.sql | docker compose exec -T postgres psql -U ittestuser -d ittestdb
  ```

---

## Assumptions & Design Choices

1. **One Account per Telegram ID**: A single Telegram user account can be linked to exactly one ITTestBot account to ensure auditability and prevent sybil abuse.
2. **Bot Permissions in Groups**: The bot requires standard poll creation permissions (`can_send_polls`). It does not require administrator privileges unless group settings restrict poll creation.
3. **Question Pool Reset**: When a schedule is set to "random without repeats" and all questions in the target pool have been posted, the schedule's sent-history automatically resets and restarts the pool cycle.
4. **Timezone Handling**: Users specify their preferred IANA timezone (default: `Asia/Tashkent`). All schedules calculate next run times locally and store timestamps in UTC.
5. **Localization**: All Telegram bot texts are maintained in `app/locales/uz.py` (Uzbek Latin script). Admin web interface and logs are in English.
