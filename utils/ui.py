import config
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup

async def render_menu(
    bot: Bot, 
    message_id: int | None,
    text: str, 
    reply_markup: InlineKeyboardMarkup
):
    """Generic helper to render a menu, avoiding code duplication."""
    if message_id is None:
        return
    try:
        await bot.edit_message_text(
            chat_id = config.OWNER_ID,
            message_id = message_id,
            text = text,
            reply_markup = reply_markup,
            parse_mode = None,
        )
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error).lower():
            raise
