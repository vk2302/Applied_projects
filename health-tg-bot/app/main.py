import asyncio
import logging

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.bot.handlers.start import router as start_router
from app.bot.handlers.profile import router as profile_router
from app.bot.handlers.water import router as water_router
from app.bot.handlers.food import router as food_router
from app.bot.handlers.workout import router as workout_router
from app.bot.handlers.progress import router as progress_router

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(water_router)
    dp.include_router(food_router)
    dp.include_router(workout_router)
    dp.include_router(progress_router)

    http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
    dp.workflow_data["http"] = http

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await http.close()


if __name__ == "__main__":
    asyncio.run(main())




