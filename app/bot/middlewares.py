from typing import Any, Awaitable, Callable, Dict, Optional
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.services.auth_service import AuthService
from app.models.user import User


class AuthMiddleware(BaseMiddleware):
    """Attaches database session and authenticated user to the handler context."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with AsyncSessionLocal() as session:
            data["db_session"] = session

            telegram_id: Optional[int] = None
            if isinstance(event, Message) and event.from_user:
                telegram_id = event.from_user.id
            elif isinstance(event, CallbackQuery) and event.from_user:
                telegram_id = event.from_user.id

            user: Optional[User] = None
            if telegram_id:
                # Resolve authenticated user by active unrevoked DB session
                user, user_session = await AuthService.get_active_user_and_session_by_telegram_id(session, telegram_id)
                if not user:
                    # User is logged out or blocked
                    user = None

            data["user"] = user
            return await handler(event, data)


async def delete_message_safe(message: Optional[Message]) -> None:
    """Safely delete a message (e.g. containing sensitive passwords)."""
    if message:
        try:
            await message.delete()
        except Exception:
            pass
