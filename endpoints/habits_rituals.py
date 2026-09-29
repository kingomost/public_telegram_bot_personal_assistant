import config

from aiogram import F, Bot, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from interfaces.state import FullState
from keyboards import HabitActions, HabitRangeOption, RitualActions, HabitSelectDelete, RitualSelectDelete, habit_actions_kb, habit_delete_kb, habit_range_kb, ritual_actions_kb, ritual_delete_kb, planning_task_fields_kb
from content import habits_ct, rituals_ct, task_ct
from enums import HabitAction, RitualAction
from fsm_state import FsmState
from menu import MainMenu, get_exit_menu
from services.habits import HabitsStore
from services.rituals import RitualsStore
from utils.chat import clear_chat_history, delete_chat_message
from utils.state import update_state
from utils.ui import render_menu

router = Router(name=__name__)

@router.message(F.text == MainMenu.HABITS, default_state)
async def habits_menu(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    msg_id = message.message_id
    await clear_chat_history(current_msg_id=msg_id, bot=bot)

    menu_msg = await message.answer(text="HABITS", reply_markup=get_exit_menu())
    keyboard_msg = await menu_msg.reply(
        text=habits_ct(), reply_markup=habit_actions_kb()
    )

    await delete_chat_message(id=msg_id, bot=bot)
    await update_state(
        bot_menu_message_id=menu_msg.message_id,
        bot_dialog_message_id=keyboard_msg.message_id
    )

@router.message(F.text == MainMenu.RITUALS, default_state)
async def rituals_menu(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    msg_id = message.message_id
    await clear_chat_history(current_msg_id=msg_id, bot=bot)

    menu_msg = await message.answer(text="RITUALS", reply_markup=get_exit_menu())
    keyboard_msg = await menu_msg.reply(
        text=rituals_ct(), reply_markup=ritual_actions_kb()
    )

    await delete_chat_message(id=msg_id, bot=bot)
    await update_state(
        bot_menu_message_id=menu_msg.message_id,
        bot_dialog_message_id=keyboard_msg.message_id
    )

@router.callback_query(HabitActions.filter())
async def habit_actions(
    callback_query: types.CallbackQuery,
    callback_data: HabitActions, 
    state: FSMContext, 
    bot: Bot
):
    from memory.memory import Memory
    full_state = Memory(path="./state.json", model=FullState)
    keyboard_message_id = full_state.data.bot_dialog_message_id

    if callback_data.action == HabitAction.LIST_HABITS:
        await render_menu(
            bot, keyboard_message_id, habits_ct(), habit_actions_kb()
        )
    elif callback_data.action == HabitAction.ADD_HABIT:
        full_state.data.tmp.pop("habit_draft", None)
        full_state.save()
        await state.set_state(FsmState.HABIT)
        msg = await bot.send_message(
            chat_id=config.OWNER_ID,
            text="Please type the new habit name:",
        )
        await update_state(
            bot_hint_message_id=msg.message_id,
        )
    elif callback_data.action == HabitAction.DELETE_HABIT:
        store = HabitsStore()
        habits = store.list()
        if habits:
            await render_menu(bot, keyboard_message_id, "Select habit to delete:", habit_delete_kb(habits))
        else:
            await render_menu(bot, keyboard_message_id, "No habits to delete.", habit_actions_kb())
    elif callback_data.action == HabitAction.GO_BACK:
        if full_state.data.bot_hint_message_id:
            await delete_chat_message(
                id=full_state.data.bot_hint_message_id, bot=bot
            )
        full_state.data.tmp.pop("habit_draft", None)
        full_state.data.bot_hint_message_id = None
        full_state.save()
        await state.set_state(default_state)
        await render_menu(
            bot, keyboard_message_id, habits_ct(), habit_actions_kb()
        )

    await callback_query.answer()

@router.message(FsmState.HABIT, F.text)
async def create_habit(message: types.Message, state: FSMContext, bot: Bot):
    name = (message.text or "").strip()
    if not name:
        await message.answer("Habit name cannot be empty.", parse_mode=None)
        return
    await state.set_state(default_state)
    from memory.memory import Memory
    full_state = Memory(path="./state.json", model=FullState)
    bot_hint_message_id = full_state.data.bot_hint_message_id
    keyboard_message_id = full_state.data.bot_dialog_message_id

    if bot_hint_message_id:
        await delete_chat_message(id=bot_hint_message_id, bot=bot)
    await delete_chat_message(id=message.message_id, bot=bot)

    await update_state(
        bot_hint_message_id=None,
        tmp={"habit_draft": {"name": name}},
    )
    await render_menu(
        bot,
        keyboard_message_id,
        f"Habit: {name}\nSelect minimum:",
        habit_range_kb("min"),
    )

@router.callback_query(HabitRangeOption.filter())
async def select_habit_range(
    callback_query: types.CallbackQuery,
    callback_data: HabitRangeOption,
    bot: Bot,
):
    from memory.memory import Memory
    full_state = Memory(path="./state.json", model=FullState)
    keyboard_message_id = full_state.data.bot_dialog_message_id
    draft = dict(full_state.data.tmp.get("habit_draft", {}))
    name = draft.get("name")
    if not name:
        await callback_query.answer("Habit draft expired", show_alert=True)
        await render_menu(
            bot, keyboard_message_id, habits_ct(), habit_actions_kb()
        )
        return

    if callback_data.field == "min":
        draft["min"] = callback_data.value
        await update_state(tmp={"habit_draft": draft})
        await render_menu(
            bot,
            keyboard_message_id,
            f"Habit: {name}\nMinimum: {callback_data.value}\nSelect maximum:",
            habit_range_kb("max", minimum=callback_data.value),
        )
    elif callback_data.field == "max" and "min" in draft:
        minimum = int(draft["min"])
        maximum = callback_data.value
        habit = HabitsStore().create(
            name=name,
            minimum=minimum,
            maximum=maximum,
        )
        full_state.data.tmp.pop("habit_draft", None)
        full_state.save()
        await render_menu(
            bot,
            keyboard_message_id,
            habits_ct(
                f"Habit '{habit.name}' created with range {minimum}-{maximum}!"
            ),
            habit_actions_kb(),
        )
    else:
        await callback_query.answer("Select minimum first", show_alert=True)
        return
    await callback_query.answer()

@router.callback_query(HabitSelectDelete.filter())
async def delete_habit(
    callback_query: types.CallbackQuery,
    callback_data: HabitSelectDelete,
    state: FSMContext,
    bot: Bot
):
    from memory.memory import Memory
    full_state = Memory(path="./state.json", model=FullState)
    keyboard_message_id = full_state.data.bot_dialog_message_id

    store = HabitsStore()
    habit = store.get(callback_data.uuid)
    habit_name = habit.name if habit else "Unknown"
    store.delete(callback_data.uuid)

    await render_menu(
        bot,
        keyboard_message_id,
        habits_ct(f"Habit '{habit_name}' deleted!"),
        habit_actions_kb(),
    )
    await callback_query.answer()

@router.callback_query(RitualActions.filter())
async def ritual_actions(
    callback_query: types.CallbackQuery,
    callback_data: RitualActions, 
    state: FSMContext, 
    bot: Bot
):
    from memory.memory import Memory
    full_state = Memory(path="./state.json", model=FullState)
    keyboard_message_id = full_state.data.bot_dialog_message_id

    if callback_data.action == RitualAction.LIST_RITUALS:
        await render_menu(
            bot, keyboard_message_id, rituals_ct(), ritual_actions_kb()
        )
    elif callback_data.action == RitualAction.ADD_RITUAL:
        from uuid import uuid4
        await update_state(
            tmp={
                "task_context": "ritual",
                "task": {
                    "uuid": str(uuid4()),
                    "name": "...",
                    "recommended_start_time": None,
                    "recommended_end_time": None,
                    "expected_duration": None,
                    "position": None,
                    "tags": [config.RITUAL_TAG],
                    "checklist": [],
                },
            },
            replace_tmp=True,
        )
        await render_menu(
            bot,
            keyboard_message_id,
            task_ct(),
            planning_task_fields_kb(),
        )
    elif callback_data.action == RitualAction.DELETE_RITUAL:
        rituals = RitualsStore().list()
        if rituals:
            await render_menu(
                bot,
                keyboard_message_id,
                "Select ritual to delete:",
                ritual_delete_kb(rituals),
            )
        else:
            await render_menu(
                bot, keyboard_message_id, "No rituals to delete.", ritual_actions_kb()
            )
    elif callback_data.action == RitualAction.GO_BACK:
        await render_menu(
            bot, keyboard_message_id, rituals_ct(), ritual_actions_kb()
        )

    await callback_query.answer()

@router.callback_query(RitualSelectDelete.filter())
async def delete_ritual(
    callback_query: types.CallbackQuery,
    callback_data: RitualSelectDelete,
    bot: Bot,
):
    from memory.memory import Memory
    full_state = Memory(path="./state.json", model=FullState)
    store = RitualsStore()
    ritual = store.get(callback_data.uuid)
    if ritual is None:
        await callback_query.answer("Ritual no longer exists", show_alert=True)
        return
    store.delete(callback_data.uuid)
    await render_menu(
        bot,
        full_state.data.bot_dialog_message_id,
        rituals_ct(f"Ritual '{ritual.name}' deleted!"),
        ritual_actions_kb(),
    )
    await callback_query.answer()
