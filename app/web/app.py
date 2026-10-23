import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from aiogram import Bot, Dispatcher
from aiogram.types import Update

from app.config import get_settings
from app.web.routes.auth_routes import router as auth_router
from app.web.routes.dashboard_routes import router as dashboard_router
from app.web.routes.users_routes import router as users_router
from app.web.routes.groups_routes import router as groups_router
from app.web.routes.questions_routes import router as questions_router
from app.web.routes.schedules_routes import router as schedules_router
from app.web.routes.audit_routes import router as audit_router

settings = get_settings()


def create_app(bot: Bot | None = None, dp: Dispatcher | None = None, lifespan = None) -> FastAPI:
    app = FastAPI(
        title="ITTestBot Web Admin Panel",
        docs_url=None,  # Disable public Swagger/Redoc for security
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    # Security headers middleware
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self' data:; "
            "frame-ancestors 'none';"
        )
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # Mount static files
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Root redirect
    @app.get("/")
    async def root_redirect():
        return RedirectResponse(url="/admin/", status_code=status.HTTP_302_FOUND)

    # Telegram Webhook endpoint (if webhook configured)
    if bot and dp:
        @app.post("/tg/webhook")
        async def telegram_webhook(
            request: Request,
            x_telegram_bot_api_secret_token: str | None = Header(None),
        ):
            if settings.WEBHOOK_SECRET_TOKEN:
                if x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET_TOKEN:
                    raise HTTPException(status_code=403, detail="Invalid webhook secret token")

            update_data = await request.json()
            telegram_update = Update.model_validate(update_data, context={"bot": bot})
            await dp.feed_update(bot, telegram_update)
            return {"ok": True}

    # Register admin routers
    app.include_router(auth_router)
    app.include_router(dashboard_router)
    app.include_router(users_router)
    app.include_router(groups_router)
    app.include_router(questions_router)
    app.include_router(schedules_router)
    app.include_router(audit_router)

    return app
