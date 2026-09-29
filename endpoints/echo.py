from aiogram import F, Bot, Router, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from fsm_state import FsmState
from interfaces.state import FullState
from memory.memory import Memory
from menu import ExitMenu, get_main_menu
from utils.chat import clear_chat_history, delete_chat_message

router = Router(name = __name__)

@router.message()
async def command_menu(message: types.Message, state: FSMContext, bot: Bot):
    await clear_chat_history(current_msg_id = message.message_id, bot = bot)
    message = await message.reply(text = "Unable to determine next action")