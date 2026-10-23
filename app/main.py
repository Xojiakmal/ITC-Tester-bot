import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

from app.config import get_settings
from app.bot.bot_instance import create_bot_and_dispatcher
from app.services.scheduler_engine import SchedulerEngine
from app.web.app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ittestbot")
settings = get_settings()

bot, dp = create_bot_and_dispatcher()
scheduler_engine = SchedulerEngine(bot)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing ITTestBot system...")

    # Start persistent scheduler daemon
    scheduler_engine.start()

    polling_task = None
    if settings.WEBHOOK_URL:
        webhook_full_url = f"{settings.WEBHOOK_URL.rstrip('/')}/tg/webhook"
        logger.info(f"Setting Telegram webhook to: {webhook_full_url}")
        try:
            await bot.set_webhook(
                url=webhook_full_url,
                secret_token=settings.WEBHOOK_SECRET_TOKEN,
                drop_pending_updates=False,
            )
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
    else:
        # Development / Polling mode
        logger.info("Starting Telegram Bot in Long Polling mode for local dev...")
        try:
            await bot.delete_webhook(drop_pending_updates=False)
        except Exception:
            pass

        polling_task = asyncio.create_task(dp.start_polling(bot))

    yield

    logger.info("Shutting down ITTestBot system...")
    await scheduler_engine.stop()
    if polling_task:
        await dp.stop_polling()
        polling_task.cancel()
    await bot.session.close()


web_app = create_app(bot=bot, dp=dp, lifespan=lifespan)


# def run():
#     uvicorn.run(
#         "app.main:web_app",
#         host=settings.HOST,
#         port=settings.PORT,
#         reload=False,
#     )


def run():
    config = uvicorn.Config(
        app=web_app,
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


if __name__ == "__main__":
    run()