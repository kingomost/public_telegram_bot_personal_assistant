from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

import config

async def delete_chat_message(id: int, bot: Bot):
    try:
        await bot.delete_message(chat_id=config.OWNER_ID, message_id=id)
    except TelegramBadRequest:
        pass

async def clear_chat_history(current_msg_id: int, bot: Bot):
    for i in range(1, 50):
        await delete_chat_message(id=current_msg_id - i, bot=bot)
