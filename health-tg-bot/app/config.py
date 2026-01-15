
from types import SimpleNamespace

import os
import logging
from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
BOT_USERNAME = os.getenv("BOT_USERNAME")
OFF_USER_AGENT = os.getenv("OFF_USER_AGENT", "health-tg-bot/0.1")

aiohttp_logger = logging.getLogger("aiohttp")
aiohttp_logger.setLevel(logging.DEBUG)

settings = SimpleNamespace(
    BOT_TOKEN=BOT_TOKEN,
    BOT_USERNAME=BOT_USERNAME,
    OPENWEATHER_API_KEY=OPENWEATHER_API_KEY,
    OFF_USER_AGENT=OFF_USER_AGENT,)
