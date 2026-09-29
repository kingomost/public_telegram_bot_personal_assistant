import config
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject
from typing import Callable, Any, Awaitable, Dict


class AuthMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.owner_id: int = config.OWNER_ID

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = getattr(event, "from_user", None)
        if not user or user.id != self.owner_id:
            if isinstance(event, CallbackQuery):
                await event.answer()
            return
        return await handler(event, data)
