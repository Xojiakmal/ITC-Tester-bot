from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import get_settings
from app.bot.fsm_storage import DatabaseFsmStorage
from app.bot.middlewares import AuthMiddleware
from app.bot.handlers.auth_handlers import router as auth_router
from app.bot.handlers.cabinet_handlers import router as cabinet_router
from app.bot.handlers.group_handlers import router as group_router
from app.bot.handlers.question_handlers import router as question_router
from app.bot.handlers.schedule_handlers import router as schedule_router

settings = get_settings()


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    storage = DatabaseFsmStorage()
    dp = Dispatcher(storage=storage)

    # Register middleware
    auth_middleware = AuthMiddleware()
    dp.message.middleware(auth_middleware)
    dp.callback_query.middleware(auth_middleware)

    # Register routers
    dp.include_router(auth_router)
    dp.include_router(cabinet_router)
    dp.include_router(group_router)
    dp.include_router(question_router)
    dp.include_router(schedule_router)

    return bot, dp
