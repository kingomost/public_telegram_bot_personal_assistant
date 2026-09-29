import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from utils.state import update_state

class ActivityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Execute the handler first
        result = await handler(event, data)
        
        # After execution, update the activity timestamps
        await update_state(
            user_last_activity_ttamp = int(time.time()),
            bot_last_activity_ttamp = int(time.time())
        )
        
        return result
