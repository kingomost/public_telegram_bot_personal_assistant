import config

from aiogram import F, Bot, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from content import backlog_ct, task_ct
from fsm_state import FsmState
from interfaces.state import FullState
from keyboards import BacklogActions, BacklogSelectDelete, backlog_actions_kb, backlog_delete_kb, planning_task_fields_kb
from enums import BacklogAction
from memory.memory import Memory
from memory.documents import Documents
from interfaces.document import DocumentType
from menu import MainMenu, get_exit_menu
from utils.chat import clear_chat_history, delete_chat_message
from utils.state import update_state
from utils.ui import render_menu
from uuid import uuid4

router = Router(name=__name__)

@router.message(F.text == MainMenu.BACKLOG, default_state)
async def backlog_menu(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    msg_id = message.message_id
    await clear_chat_history(current_msg_id=msg_id, bot=bot)

    menu_msg = await message.answer(text="BACKLOG", reply_markup=get_exit_menu())
    text = backlog_ct()
    reply_markup = backlog_actions_kb()
    keyboard_msg = await menu_msg.reply(text=text, reply_markup=reply_markup)

    await delete_chat_message(id=msg_id, bot=bot)
    await update_state(
        bot_menu_message_id=menu_msg.message_id,
        bot_dialog_message_id=keyboard_msg.message_id
    )

@router.callback_query(BacklogActions.filter())
async def backlog_actions(
    callback_query: types.CallbackQuery,
    callback_data: BacklogActions, 
    state: FSMContext, 
    bot: Bot
):
    full_state = Memory(path="./state.json", model=FullState)
    keyboard_message_id = full_state.data.bot_dialog_message_id

    if callback_data.action == BacklogAction.ADD_TASK:
        await update_state(
            tmp={
                "task_context": "backlog",
                "task": {
                    "uuid": str(uuid4()),
                    "name": "...",
                    "recommended_start_time": None,
                    "recommended_end_time": None,
                    "expected_duration": None,
                    "position": None,
                    "tags": [],
                    "checklist": []
                },
            },
            replace_tmp=True,
        )
        await render_menu(bot, keyboard_message_id, task_ct(), planning_task_fields_kb())
    elif callback_data.action == BacklogAction.LIST_TASKS:
        await render_menu(
            bot, keyboard_message_id, backlog_ct(), backlog_actions_kb()
        )
    elif callback_data.action == BacklogAction.DELETE_TASK:
        documents = Documents()
        tasks = []
        for document in documents.get_list(type=DocumentType.TASK_MODEL):
            task = documents.read(document.uuid)
            tasks.append({"uuid": document.uuid, "name": task.name})
        if tasks:
            await render_menu(
                bot,
                keyboard_message_id,
                "Select a backlog task to delete:",
                backlog_delete_kb(tasks),
            )
        else:
            await render_menu(
                bot, keyboard_message_id, backlog_ct(), backlog_actions_kb()
            )
    elif callback_data.action == BacklogAction.GO_BACK:
        await render_menu(
            bot, keyboard_message_id, backlog_ct(), backlog_actions_kb()
        )

    await callback_query.answer()

@router.callback_query(BacklogSelectDelete.filter())
async def delete_backlog_task(
    callback_query: types.CallbackQuery,
    callback_data: BacklogSelectDelete,
    bot: Bot,
):
    full_state = Memory(path="./state.json", model=FullState)
    documents = Documents()
    task = documents.read(callback_data.uuid)
    documents.delete(callback_data.uuid)
    await render_menu(
        bot,
        full_state.data.bot_dialog_message_id,
        backlog_ct(f"Task '{task.name}' deleted from backlog!"),
        backlog_actions_kb(),
    )
    await callback_query.answer()
