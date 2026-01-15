import logging
import os

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.config import settings
from app.bot.handlers.profile import router as profile_router
from app.bot.handlers.water import router as water_router
from app.bot.handlers.food import router as food_router
from app.bot.handlers.workout import router as workout_router
from app.bot.handlers.progress import router as progress_router
from app.bot.middlewares.logging import CommandLoggingMiddleware

logging.basicConfig(level=logging.INFO)

WEBHOOK_PATH = "/webhook"
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")


def get_base_url() -> str:
    base = os.getenv("APP_BASE_URL") or os.getenv("RENDER_EXTERNAL_URL")
    if not base:
        raise RuntimeError("APP_BASE_URL is not set (or RENDER_EXTERNAL_URL missing)")
    return base.rstrip("/")


def main() -> None:
    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")
    if not WEBHOOK_SECRET:
        raise RuntimeError("WEBHOOK_SECRET is not set")

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(CommandLoggingMiddleware())
    dp.callback_query.middleware(CommandLoggingMiddleware())

    dp.include_router(profile_router)
    dp.include_router(water_router)
    dp.include_router(food_router)
    dp.include_router(workout_router)
    dp.include_router(progress_router)

    app = web.Application()

    async def healthz(_: web.Request) -> web.Response:
        return web.Response(text="ok")

    app.router.add_get("/healthz", healthz)

    async def on_startup(_: web.Application) -> None:
        http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        app["http"] = http

        webhook_url = f"{get_base_url()}{WEBHOOK_PATH}"
        await bot.set_webhook(
            webhook_url,
            secret_token=WEBHOOK_SECRET,
            drop_pending_updates=True,
        )
        logging.info("Webhook set: %s", webhook_url)

    async def on_shutdown(_: web.Application) -> None:
        await bot.delete_webhook(drop_pending_updates=True)
        http: aiohttp.ClientSession | None = app.get("http")
        if http:
            await http.close()
        logging.info("Webhook deleted; http session closed")

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    def data_factory(_: web.Request) -> dict:
        return {"http": app["http"]}

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    ).register(app, path=WEBHOOK_PATH, data_factory=data_factory)

    setup_application(app, dp, bot=bot)

    web.run_app(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()

