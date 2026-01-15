import logging
from typing import Callable, Awaitable, Dict, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger("bot.commands")


class CommandLoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            if event.text:
                logger.info(
                    "message user_id=%s chat_id=%s text=%r",
                    getattr(event.from_user, "id", None),
                    getattr(event.chat, "id", None),
                    event.text,
                )
        elif isinstance(event, CallbackQuery):
            logger.info(
                "callback user_id=%s data=%r",
                getattr(event.from_user, "id", None),
                event.data,
            )

        return await handler(event, data)

