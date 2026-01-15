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
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
PORT = int(os.getenv("PORT", "10000"))

def get_base_url() -> str:
    base = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("APP_BASE_URL")
    if not base:
        raise RuntimeError("Set RENDER_EXTERNAL_URL (Render sets it automatically) or APP_BASE_URL")
    return base.rstrip("/")


async def main():
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(CommandLoggingMiddleware())
    dp.callback_query.middleware(CommandLoggingMiddleware())

    dp.include_router(profile_router)
    dp.include_router(water_router)
    dp.include_router(food_router)
    dp.include_router(workout_router)
    dp.include_router(progress_router)

    http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

    async def on_startup() -> None:
        base_url = get_base_url()
        webhook_url = f"{base_url}{WEBHOOK_PATH}"
        await bot.set_webhook(
            webhook_url,
            secret_token=WEBHOOK_SECRET,
            drop_pending_updates=True,
        )
        logging.info("Webhook set: %s", webhook_url)

    async def on_shutdown() -> None:
        await bot.delete_webhook(drop_pending_updates=True)
        await http.close()
        logging.info("Webhook deleted; http session closed")

    app = web.Application()

    async def healthz(_: web.Request) -> web.Response:
        return web.Response(text="ok")

    app.router.add_get("/healthz", healthz)

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
        http=http,  
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    await on_startup()
    try:
        web.run_app(app, host="0.0.0.0", port=PORT)
    finally:
        await on_shutdown()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
