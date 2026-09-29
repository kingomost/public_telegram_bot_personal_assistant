from aiogram import F, Bot, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
import config
from content import planning_select_date_ct, reminder_draft_ct, task_ct
from fsm_state import FsmState
from interfaces.state import FullState
from keyboards import planning_reminder_fields_kb, planning_select_date_kb, planning_task_fields_kb
from memory.memory import Memory
from menu import MainMenu, get_exit_menu
from utils.chat import clear_chat_history, delete_chat_message
from utils.state import update_state
from utils.ui import render_menu

router = Router(name = __name__)

@router.message(F.text == MainMenu.PLANNING, default_state)
async def planning_select_date(message: types.Message, state: FSMContext, bot: Bot):
    await state.set_state(FsmState.PLAN)
    msg_id = message.message_id
    await clear_chat_history(current_msg_id = msg_id, bot = bot)

    menu_msg = await message.answer(text = "PLANNING", reply_markup = get_exit_menu())

    text = planning_select_date_ct()
    reply_markup = planning_select_date_kb()
    keyboard_mgs = await menu_msg.reply(text = text, reply_markup = reply_markup)

    await delete_chat_message(id = msg_id, bot = bot)
    await update_state(
        bot_menu_message_id = menu_msg.message_id,
        bot_dialog_message_id = keyboard_mgs.message_id
    )

@router.message(FsmState.TASK, F.text)
async def planning_task_str(message: types.Message, state: FSMContext, bot: Bot):
    await state.set_state(FsmState.PLAN)
    full_state = Memory(path = "./state.json", model = FullState)
    bot_hint_message_id = full_state.data.bot_hint_message_id
    keyboard_message_id = full_state.data.bot_dialog_message_id

    if bot_hint_message_id is not None:
        await delete_chat_message(id = bot_hint_message_id, bot = bot)

    wait_field = full_state.data.tmp.get("wait_field")
    task_data = full_state.data.tmp.get("task", {})
    checklist = task_data.get("checklist", [])

    if wait_field == "task_name":
        await update_state(tmp = {"task": {"name": message.text}})
    elif wait_field == "task_checkpoint":
        checklist.append(message.text)
        await update_state(tmp = {"task": {"checklist": checklist}})
    await update_state(bot_hint_message_id=None, tmp={"wait_field": None})
    
    await delete_chat_message(id = message.message_id, bot = bot)

    await render_menu(
        bot,
        keyboard_message_id,
        task_ct(),
        planning_task_fields_kb()
    )

@router.message(FsmState.REMINDER, F.text)
async def planning_reminder_str(
    message: types.Message, state: FSMContext, bot: Bot
):
    full_state = Memory(path="./state.json", model=FullState)
    keyboard_message_id = full_state.data.bot_dialog_message_id
    value = (message.text or "").strip()
    if not value:
        await message.answer("Value cannot be empty", parse_mode=None)
        return
    wait_field = full_state.data.tmp.get("wait_field")
    if wait_field == "reminder_name":
        await update_state(tmp={"reminder_draft": {"name": value}})
    elif wait_field == "reminder_description":
        await update_state(tmp={"reminder_draft": {"description": value}})
    else:
        await message.answer("Reminder editor expired", parse_mode=None)
        return
    await state.set_state(FsmState.PLAN)
    if full_state.data.bot_hint_message_id:
        await delete_chat_message(id=full_state.data.bot_hint_message_id, bot=bot)
    await delete_chat_message(id=message.message_id, bot=bot)
    await update_state(bot_hint_message_id=None, tmp={"wait_field": None})
    await render_menu(
        bot,
        keyboard_message_id,
        reminder_draft_ct(),
        planning_reminder_fields_kb(),
    )
