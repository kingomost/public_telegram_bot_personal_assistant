from aiogram import F, Bot, Router, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

from fsm_state import FsmState
from interfaces.state import FullState, UserStateEnum
from memory.memory import Memory
from menu import ExitMenu, MainMenu, get_main_menu
from utils.chat import clear_chat_history, delete_chat_message
from utils.state import is_silent_mode, update_state

router = Router(name = __name__)

@router.message(CommandStart())
@router.message(Command("menu"))
@router.message(F.text == ExitMenu.GO_TO_MAIN_MENU)
@router.message(F.text == MainMenu.SILENT_MODE)
@router.message(F.text == MainMenu.UNSILENT_MODE)
async def command_menu(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    await state.set_state(default_state)
    if message.text == MainMenu.SILENT_MODE:
        await update_state(user_state=UserStateEnum.NOT_ACTIVE)
    elif message.text == MainMenu.UNSILENT_MODE:
        await update_state(user_state=UserStateEnum.ACTIVE)
    full_state = Memory(path = "./state.json", model = FullState)
    msg_id = message.message_id
    await clear_chat_history(current_msg_id = msg_id, bot = bot)
    message = await message.answer(
        text = "MAIN MENU",
        reply_markup = get_main_menu(
            active_task = full_state.data.active_task is not None,
            silent_mode = is_silent_mode(full_state.data),
        )
    )
    await delete_chat_message(id = msg_id, bot = bot)
