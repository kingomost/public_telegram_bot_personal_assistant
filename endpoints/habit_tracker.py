from aiogram import Bot, F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

from content import habit_tracker_ct
from interfaces.state import FullState
from keyboards import (
    HabitTrackerActions,
    HabitTrackerAdjust,
    HabitTrackerSelect,
    habit_tracker_adjust_kb,
    habit_tracker_list_kb,
)
from memory.memory import Memory
from menu import MainMenu, get_exit_menu
from services.plans import PlanStore
from utils.chat import clear_chat_history, delete_chat_message
from utils.state import update_state
from utils.ui import render_menu


router = Router(name=__name__)


def _list_keyboard(plan: PlanStore):
    counts = {habit.uuid: plan.habit_count(habit.uuid) for habit in plan.data.habits}
    return habit_tracker_list_kb(plan.data.habits, counts)


@router.message(F.text == MainMenu.HABIT_TRACKER, default_state)
async def habit_tracker_menu(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    await clear_chat_history(current_msg_id=message.message_id, bot=bot)
    plan = PlanStore()
    menu_msg = await message.answer(
        text="HABIT TRACKER", reply_markup=get_exit_menu()
    )
    keyboard_msg = await menu_msg.reply(
        text=habit_tracker_ct(), reply_markup=_list_keyboard(plan)
    )
    await delete_chat_message(id=message.message_id, bot=bot)
    await update_state(
        bot_menu_message_id=menu_msg.message_id,
        bot_dialog_message_id=keyboard_msg.message_id,
    )


@router.callback_query(HabitTrackerSelect.filter())
async def select_habit(
    callback_query: types.CallbackQuery,
    callback_data: HabitTrackerSelect,
    bot: Bot,
):
    plan = PlanStore()
    habit = next(
        (item for item in plan.data.habits if item.uuid == callback_data.uuid),
        None,
    )
    if habit is None:
        await callback_query.answer("Habit is not active today", show_alert=True)
        return
    state = Memory("state.json", FullState).data
    await render_menu(
        bot,
        state.bot_dialog_message_id,
        habit_tracker_ct(habit.uuid),
        habit_tracker_adjust_kb(habit.uuid),
    )
    await callback_query.answer()


@router.callback_query(HabitTrackerAdjust.filter())
async def adjust_habit(
    callback_query: types.CallbackQuery,
    callback_data: HabitTrackerAdjust,
    bot: Bot,
):
    plan = PlanStore()
    count = plan.adjust_habit(callback_data.uuid, callback_data.delta)
    if count is None:
        await callback_query.answer("Habit is not active today", show_alert=True)
        return
    state = Memory("state.json", FullState).data
    await render_menu(
        bot,
        state.bot_dialog_message_id,
        habit_tracker_ct(callback_data.uuid),
        habit_tracker_adjust_kb(callback_data.uuid),
    )
    await callback_query.answer(f"Count: {count}")


@router.callback_query(HabitTrackerActions.filter())
async def habit_tracker_actions(callback_query: types.CallbackQuery, bot: Bot):
    plan = PlanStore()
    state = Memory("state.json", FullState).data
    await render_menu(
        bot,
        state.bot_dialog_message_id,
        habit_tracker_ct(),
        _list_keyboard(plan),
    )
    await callback_query.answer()
