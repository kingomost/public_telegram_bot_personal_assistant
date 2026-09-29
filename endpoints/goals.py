import config
from aiogram import Bot, F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from pydantic import ValidationError

from content import goal_detail_ct, goals_ct
from enums import GoalAction, GoalNodeAction
from fsm_state import FsmState
from interfaces.goal import GoalTimeBudget
from interfaces.state import FullState
from keyboards import (
    GoalActions,
    GoalBudgetField,
    GoalBudgetValue,
    GoalDurationValue,
    GoalNodeActions,
    GoalSelect,
    goal_budget_kb,
    goal_budget_values_kb,
    goal_duration_kb,
    goal_node_kb,
    goals_kb,
)
from memory.memory import Memory
from menu import MainMenu, get_exit_menu
from services.goals import GoalsStore
from utils.chat import clear_chat_history, delete_chat_message
from utils.state import update_state
from utils.ui import render_menu


router = Router(name=__name__)


@router.message(F.text == MainMenu.GOAL, default_state)
async def goals_menu(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    await clear_chat_history(current_msg_id=message.message_id, bot=bot)
    menu_msg = await message.answer(text="GOALS", reply_markup=get_exit_menu())
    store = GoalsStore()
    dialog = await menu_msg.reply(
        text=goals_ct(), reply_markup=goals_kb(list(store.iter_nodes()))
    )
    await delete_chat_message(id=message.message_id, bot=bot)
    await update_state(
        bot_menu_message_id=menu_msg.message_id,
        bot_dialog_message_id=dialog.message_id,
    )


async def _ask_for_value(
    *, state: FSMContext, bot: Bot, field: str, uuid: str | None, prompt: str
) -> None:
    full_state = Memory("state.json", FullState).data
    await state.set_state(FsmState.GOAL)
    await bot.edit_message_reply_markup(
        chat_id=config.OWNER_ID,
        message_id=full_state.bot_dialog_message_id,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[]),
    )
    hint = await bot.send_message(chat_id=config.OWNER_ID, text=prompt)
    await update_state(
        bot_hint_message_id=hint.message_id,
        tmp={"goal_input": {"field": field, "uuid": uuid}},
    )


@router.callback_query(GoalActions.filter())
async def goal_actions(
    callback_query: types.CallbackQuery,
    callback_data: GoalActions,
    state: FSMContext,
    bot: Bot,
):
    if callback_data.action == GoalAction.ADD:
        await _ask_for_value(
            state=state,
            bot=bot,
            field="name",
            uuid=None,
            prompt="Enter the main goal name:",
        )
    await callback_query.answer()


@router.callback_query(GoalSelect.filter())
async def select_goal(
    callback_query: types.CallbackQuery,
    callback_data: GoalSelect,
    bot: Bot,
):
    state = Memory("state.json", FullState).data
    if GoalsStore().get(callback_data.uuid) is None:
        await callback_query.answer("Goal no longer exists", show_alert=True)
        return
    await render_menu(
        bot,
        state.bot_dialog_message_id,
        goal_detail_ct(callback_data.uuid),
        goal_node_kb(callback_data.uuid),
    )
    await callback_query.answer()


@router.callback_query(GoalNodeActions.filter())
async def goal_node_actions(
    callback_query: types.CallbackQuery,
    callback_data: GoalNodeActions,
    state: FSMContext,
    bot: Bot,
):
    store = GoalsStore()
    node = store.get(callback_data.uuid)
    full_state = Memory("state.json", FullState).data
    if node is None:
        await callback_query.answer("Goal no longer exists", show_alert=True)
        return
    action = callback_data.action
    if action == GoalNodeAction.ADD_SUBGOAL:
        await _ask_for_value(
            state=state, bot=bot, field="name", uuid=node.uuid,
            prompt=f"Enter a subgoal name for '{node.name}':",
        )
    elif action == GoalNodeAction.EXPECTED_RESULT:
        await _ask_for_value(
            state=state, bot=bot, field="expected_result", uuid=node.uuid,
            prompt="Enter one expected result:",
        )
    elif action == GoalNodeAction.BUDGET:
        budget = node.time_budget
        draft = {
            "uuid": node.uuid,
            "min": int(budget.min_hours) if budget else None,
            "max": int(budget.max_hours) if budget else None,
        }
        await update_state(tmp={"goal_budget": draft})
        await render_menu(
            bot,
            full_state.bot_dialog_message_id,
            "Set the minimum and maximum time budget in hours.",
            goal_budget_kb(node.uuid, draft["min"], draft["max"]),
        )
    elif action == GoalNodeAction.DAYS:
        await render_menu(
            bot,
            full_state.bot_dialog_message_id,
            "Set the goal duration in days.",
            goal_duration_kb(node.uuid),
        )
    elif action == GoalNodeAction.TOGGLE_DONE:
        node = store.toggle_done(node.uuid)
        await render_menu(
            bot, full_state.bot_dialog_message_id,
            goal_detail_ct(node.uuid, "Goal status updated."), goal_node_kb(node.uuid),
        )
    elif action == GoalNodeAction.DELETE:
        store.delete(node.uuid)
        await render_menu(
            bot, full_state.bot_dialog_message_id,
            goals_ct(f"Goal '{node.name}' and its subgoals deleted."),
            goals_kb(list(store.iter_nodes())),
        )
    elif action == GoalNodeAction.GO_BACK:
        await render_menu(
            bot, full_state.bot_dialog_message_id,
            goals_ct(), goals_kb(list(store.iter_nodes())),
        )
    await callback_query.answer()


def _budget_draft(uuid: str) -> dict[str, int | str | None]:
    full_state = Memory("state.json", FullState).data
    draft = dict(full_state.tmp.get("goal_budget", {}))
    if draft.get("uuid") == uuid:
        return draft
    node = GoalsStore().get(uuid)
    budget = node.time_budget if node else None
    return {
        "uuid": uuid,
        "min": int(budget.min_hours) if budget else None,
        "max": int(budget.max_hours) if budget else None,
    }


@router.callback_query(GoalBudgetField.filter())
async def goal_budget_field(
    callback_query: types.CallbackQuery,
    callback_data: GoalBudgetField,
    bot: Bot,
):
    full_state = Memory("state.json", FullState).data
    draft = _budget_draft(callback_data.uuid)
    await render_menu(
        bot,
        full_state.bot_dialog_message_id,
        f"Set {callback_data.field}imum expected hours.",
        goal_budget_values_kb(
            callback_data.uuid,
            callback_data.field,
            draft.get("min"),
            draft.get("max"),
        ),
    )
    await callback_query.answer()


@router.callback_query(GoalBudgetValue.filter())
async def goal_budget_value(
    callback_query: types.CallbackQuery,
    callback_data: GoalBudgetValue,
    bot: Bot,
):
    full_state = Memory("state.json", FullState).data
    draft = _budget_draft(callback_data.uuid)
    if callback_data.offset is not None:
        await render_menu(
            bot,
            full_state.bot_dialog_message_id,
            f"Set {callback_data.field}imum expected hours.",
            goal_budget_values_kb(
                callback_data.uuid,
                callback_data.field,
                draft.get("min"),
                draft.get("max"),
                callback_data.offset,
            ),
        )
        await callback_query.answer()
        return
    if callback_data.value is None:
        await callback_query.answer("Choose a value", show_alert=True)
        return
    draft[callback_data.field] = callback_data.value
    await update_state(tmp={"goal_budget": draft})
    minimum = draft.get("min")
    maximum = draft.get("max")
    status = "Time budget draft updated."
    if isinstance(minimum, int) and isinstance(maximum, int):
        GoalsStore().update(
            callback_data.uuid,
            budget=GoalTimeBudget(min_hours=minimum, max_hours=maximum),
        )
        status = "Time budget updated."
    await render_menu(
        bot,
        full_state.bot_dialog_message_id,
        status,
        goal_budget_kb(
            callback_data.uuid,
            minimum if isinstance(minimum, int) else None,
            maximum if isinstance(maximum, int) else None,
        ),
    )
    await callback_query.answer()


@router.callback_query(GoalDurationValue.filter())
async def goal_duration_value(
    callback_query: types.CallbackQuery,
    callback_data: GoalDurationValue,
    bot: Bot,
):
    full_state = Memory("state.json", FullState).data
    if callback_data.offset is not None:
        await render_menu(
            bot,
            full_state.bot_dialog_message_id,
            "Set the goal duration in days.",
            goal_duration_kb(callback_data.uuid, callback_data.offset),
        )
        await callback_query.answer()
        return
    if callback_data.value is None:
        await callback_query.answer("Choose a value", show_alert=True)
        return
    node = GoalsStore().update(
        callback_data.uuid, duration_days=callback_data.value
    )
    await render_menu(
        bot,
        full_state.bot_dialog_message_id,
        goal_detail_ct(node.uuid, "Duration updated."),
        goal_node_kb(node.uuid),
    )
    await callback_query.answer()


@router.message(FsmState.GOAL, F.text)
async def goal_input(message: types.Message, state: FSMContext, bot: Bot):
    value = (message.text or "").strip()
    if not value:
        await message.answer("Value cannot be empty.", parse_mode=None)
        return
    full_state = Memory("state.json", FullState).data
    input_data = dict(full_state.tmp.get("goal_input", {}))
    field = input_data.get("field")
    uuid = input_data.get("uuid")
    store = GoalsStore()
    try:
        if field == "name":
            node = store.create(value, parent_uuid=uuid)
            status = "Goal created." if uuid is None else "Subgoal created."
        elif field == "expected_result" and uuid:
            node = store.update(uuid, expected_result=value)
            status = "Expected result added."
        else:
            raise ValueError("Goal editor expired.")
    except (KeyError, ValidationError, ValueError) as error:
        await message.answer(str(error), parse_mode=None)
        return

    await state.set_state(default_state)
    if full_state.bot_hint_message_id:
        await delete_chat_message(id=full_state.bot_hint_message_id, bot=bot)
    await delete_chat_message(id=message.message_id, bot=bot)
    state_memory = Memory("state.json", FullState)
    state_memory.data.tmp.pop("goal_input", None)
    state_memory.data.bot_hint_message_id = None
    state_memory.save()
    await render_menu(
        bot,
        full_state.bot_dialog_message_id,
        goal_detail_ct(node.uuid, status),
        goal_node_kb(node.uuid),
    )
