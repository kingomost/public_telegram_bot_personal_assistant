import time

import config
from aiogram import Bot, F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

from enums import ExecutionAction
from fsm_state import FsmState
from interfaces.state import FullState
from keyboards import (
    ExecutionActions,
    ExecutionCheckpoint,
    ExecutionCheckpointDone,
    ExecutionSelectTask,
    active_task_kb,
    execution_checkpoints_kb,
    execution_select_task_kb,
)
from memory.memory import Memory
from menu import MainMenu, get_exit_menu, get_main_menu
from services.plans import PlanStore
from utils.chat import clear_chat_history, delete_chat_message
from utils.state import is_silent_mode, update_state
from utils.ui import render_menu


router = Router(name=__name__)


def _start_task_text(tasks_info: list[dict]) -> str:
    if not tasks_info:
        return "No tasks planned for today."
    lines = ["Tasks to start:", ""]
    for index, task in enumerate(tasks_info, 1):
        markers = []
        if task["completed"]:
            markers.append("done")
        if task["has_activity"]:
            markers.append("started")
        status = f" ({', '.join(markers)})" if markers else ""
        details = []
        if task.get("expected_duration"):
            details.append(f"duration: {task['expected_duration']}")
        if task.get("recommended_start_time"):
            details.append(f"start: {task['recommended_start_time']}")
        if task.get("recommended_end_time"):
            details.append(f"end: {task['recommended_end_time']}")
        suffix = f" - {'; '.join(details)}" if details else ""
        display_name = task.get("display_name") or task["name"]
        lines.append(f"{index}. {display_name}{status}{suffix}")
    return "\n".join(lines)


def _format_spent_time(seconds: int) -> str:
    minutes = max(0, seconds) // 60
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        return f"{hours} h. {minutes} min."
    if hours:
        return f"{hours} h."
    return f"{minutes} min."


def _task_spent_seconds(plan: PlanStore, uuid: str) -> int:
    meta = plan.task_meta(uuid, create=False)
    if meta is None:
        return 0
    return sum(
        max(0, period.end.ttamp_sec - period.start.ttamp_sec)
        for period in meta.periods
    )


def _start_task_items(plan: PlanStore) -> list[dict]:
    fresh_tasks = []
    started_or_done_tasks = []
    for task in plan.data.tasks:
        has_activity = plan.task_has_activity(task.uuid)
        spent_seconds = _task_spent_seconds(plan, task.uuid)
        button_name = (
            f"({_format_spent_time(spent_seconds)}) {task.name}"
            if has_activity
            else task.name
        )
        item = {
            "uuid": task.uuid,
            "name": button_name,
            "display_name": task.name,
            "completed": task.completed,
            "has_activity": has_activity,
            "expected_duration": task.expected_duration,
            "recommended_start_time": task.recommended_start_time,
            "recommended_end_time": task.recommended_end_time,
        }
        if has_activity or task.completed:
            started_or_done_tasks.append(item)
        else:
            fresh_tasks.append(item)
    return [*fresh_tasks, *started_or_done_tasks]


def _elapsed_seconds(execution: dict, now: int | None = None) -> int:
    current = now or int(time.time())
    elapsed = int(execution.get("elapsed_seconds", 0))
    resumed_at = execution.get("resumed_at")
    if resumed_at and not execution.get("paused"):
        elapsed += max(0, current - int(resumed_at))
    return elapsed


async def _activate_task(task_uuid: str, bot: Bot) -> bool:
    """Start a plan task and synchronize execution state and menus."""
    full_state = Memory("state.json", FullState).data
    if full_state.active_task:
        return False

    now = int(time.time())
    task = PlanStore().start_task(task_uuid, now)
    if task is None:
        return False
    await update_state(
        active_task=task.uuid,
        bot_hint_message_id=None,
        tmp={
            "execution": {
                "task_uuid": task.uuid,
                "period_started_at": now,
                "resumed_at": now,
                "elapsed_seconds": 0,
                "paused": False,
                "extra_seconds": 0,
            }
        },
        replace_tmp=True,
    )
    await bot.send_message(
        chat_id=config.OWNER_ID,
        text=f"Task started: {task.name}",
        reply_markup=get_main_menu(
            active_task=True,
            silent_mode=is_silent_mode(full_state),
        ),
    )
    await render_menu(
        bot, full_state.bot_dialog_message_id, "Task is now active.", active_task_kb()
    )
    return True


@router.message(F.text == MainMenu.START_TASK, default_state)
async def start_task_menu(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    await clear_chat_history(current_msg_id=message.message_id, bot=bot)
    menu_msg = await message.answer(text="START TASK", reply_markup=get_exit_menu())

    plan = PlanStore()
    tasks_info = _start_task_items(plan)
    text = _start_task_text(tasks_info)
    keyboard_msg = await menu_msg.reply(
        text=text, reply_markup=execution_select_task_kb(tasks_info)
    )

    await delete_chat_message(id=message.message_id, bot=bot)
    await update_state(
        bot_menu_message_id=menu_msg.message_id,
        bot_dialog_message_id=keyboard_msg.message_id,
    )


@router.message(F.text == MainMenu.ACTIVE_TASK, default_state)
async def active_task_menu(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()
    await clear_chat_history(current_msg_id=message.message_id, bot=bot)
    full_state = Memory("state.json", FullState).data
    menu_msg = await message.answer(text="ACTIVE TASK", reply_markup=get_exit_menu())

    if full_state.active_task:
        plan = PlanStore()
        task = plan.task(full_state.active_task)
        elapsed = _elapsed_seconds(dict(full_state.tmp.get("execution", {})))
        minutes, seconds = divmod(elapsed, 60)
        text = (
            f"{task.name if task else 'Task'} is active.\n"
            f"Elapsed: {minutes:02d}:{seconds:02d}"
        )
        reply_markup = active_task_kb()
    else:
        text = "No active task."
        reply_markup = None

    keyboard_msg = await menu_msg.reply(text=text, reply_markup=reply_markup)
    await delete_chat_message(id=message.message_id, bot=bot)
    await update_state(
        bot_menu_message_id=menu_msg.message_id,
        bot_dialog_message_id=keyboard_msg.message_id,
    )


@router.callback_query(ExecutionSelectTask.filter())
async def select_task_to_start(
    callback_query: types.CallbackQuery,
    callback_data: ExecutionSelectTask,
    state: FSMContext,
    bot: Bot,
):
    if Memory("state.json", FullState).data.active_task:
        await callback_query.answer("Pause or finish the active task first", show_alert=True)
        return

    if not await _activate_task(callback_data.uuid, bot):
        await callback_query.answer("Task no longer exists", show_alert=True)
        return
    await callback_query.answer()


@router.message(FsmState.QUICK_TASK, F.text)
async def create_quick_task(message: types.Message, state: FSMContext, bot: Bot):
    name = (message.text or "").strip()
    if not name:
        await message.answer("Task name cannot be empty.", parse_mode=None)
        return

    full_state = Memory("state.json", FullState).data
    if full_state.active_task:
        await state.set_state(default_state)
        await message.answer("Pause or finish the active task first.", parse_mode=None)
        return

    task = PlanStore().create_task(name)
    await state.set_state(default_state)
    if full_state.bot_hint_message_id:
        await delete_chat_message(id=full_state.bot_hint_message_id, bot=bot)
    await delete_chat_message(id=message.message_id, bot=bot)
    if not await _activate_task(task.uuid, bot):
        await message.answer("Could not start the task.", parse_mode=None)


async def _stop_active_task(
    *,
    full_state: FullState,
    completed: bool,
    bot: Bot,
) -> None:
    now = int(time.time())
    execution = dict(full_state.tmp.get("execution", {}))
    elapsed = _elapsed_seconds(execution, now)
    started_at = int(execution.get("period_started_at") or max(0, now - elapsed))
    task_uuid = full_state.active_task
    plan = PlanStore()
    task = (
        plan.stop_task(
            task_uuid,
            started_at,
            now,
            completed=completed,
        )
        if task_uuid
        else None
    )
    result = "Task finished." if completed else "Task paused."
    await update_state(
        active_task=None,
        tmp={
            "checkpoint_task_uuid": task_uuid,
            "checkpoint_result": result,
        },
        replace_tmp=True,
    )
    await bot.send_message(
        chat_id=config.OWNER_ID,
        text=result,
        reply_markup=get_main_menu(
            active_task=False,
            silent_mode=is_silent_mode(full_state),
        ),
    )

    meta = plan.task_meta(task_uuid, create=False) if task_uuid else None
    if task and meta and meta.checklist:
        await render_menu(
            bot,
            full_state.bot_dialog_message_id,
            f"{result}\nMark completed checkpoints:",
            execution_checkpoints_kb(meta.checklist),
        )
    else:
        await update_state(tmp={}, replace_tmp=True)
        await render_menu(
            bot,
            full_state.bot_dialog_message_id,
            result,
            types.InlineKeyboardMarkup(inline_keyboard=[]),
        )


@router.callback_query(ExecutionActions.filter())
async def execution_actions(
    callback_query: types.CallbackQuery,
    callback_data: ExecutionActions,
    state: FSMContext,
    bot: Bot,
):
    full_state = Memory("state.json", FullState).data
    if (
        callback_data.action
        in {ExecutionAction.FINISH_TASK, ExecutionAction.PAUSE_TASK}
        and not full_state.active_task
    ):
        await callback_query.answer("No active task", show_alert=True)
        return
    if callback_data.action == ExecutionAction.FINISH_TASK:
        await _stop_active_task(full_state=full_state, completed=True, bot=bot)
    elif callback_data.action == ExecutionAction.PAUSE_TASK:
        await _stop_active_task(full_state=full_state, completed=False, bot=bot)
    elif callback_data.action == ExecutionAction.QUICK_CREATE:
        if full_state.active_task:
            await callback_query.answer(
                "Pause or finish the active task first", show_alert=True
            )
            return
        await state.set_state(FsmState.QUICK_TASK)
        await bot.edit_message_reply_markup(
            chat_id=config.OWNER_ID,
            message_id=full_state.bot_dialog_message_id,
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[]),
        )
        hint = await bot.send_message(
            chat_id=config.OWNER_ID,
            text="Please enter the task name:",
        )
        await update_state(bot_hint_message_id=hint.message_id)
    elif callback_data.action == ExecutionAction.ADD_TIME:
        execution = dict(full_state.tmp.get("execution", {}))
        execution["extra_seconds"] = int(execution.get("extra_seconds", 0)) + 300
        await update_state(tmp={"execution": execution})
        await render_menu(
            bot, full_state.bot_dialog_message_id, "Added 5 minutes.", active_task_kb()
        )
    elif callback_data.action == ExecutionAction.GO_BACK:
        await render_menu(
            bot,
            full_state.bot_dialog_message_id,
            "Execution Menu",
            types.InlineKeyboardMarkup(inline_keyboard=[]),
        )
    await callback_query.answer()


@router.callback_query(ExecutionCheckpoint.filter())
async def toggle_execution_checkpoint(
    callback_query: types.CallbackQuery,
    callback_data: ExecutionCheckpoint,
    bot: Bot,
):
    full_state = Memory("state.json", FullState).data
    task_uuid = full_state.tmp.get("checkpoint_task_uuid")
    if not task_uuid:
        await callback_query.answer("Checkpoint session expired", show_alert=True)
        return
    plan = PlanStore()
    checkpoint = plan.toggle_checkpoint(task_uuid, callback_data.index)
    meta = plan.task_meta(task_uuid, create=False)
    if checkpoint is None or meta is None:
        await callback_query.answer("Checkpoint no longer exists", show_alert=True)
        return
    await render_menu(
        bot,
        full_state.bot_dialog_message_id,
        f"{full_state.tmp.get('checkpoint_result', 'Task stopped.')}\n"
        "Mark completed checkpoints:",
        execution_checkpoints_kb(meta.checklist),
    )
    await callback_query.answer()


@router.callback_query(ExecutionCheckpointDone.filter())
async def finish_execution_checkpoints(callback_query: types.CallbackQuery, bot: Bot):
    full_state = Memory("state.json", FullState).data
    result = str(full_state.tmp.get("checkpoint_result", "Checkpoints saved."))
    await update_state(tmp={}, replace_tmp=True)
    await render_menu(
        bot,
        full_state.bot_dialog_message_id,
        f"{result}\nCheckpoints saved.",
        types.InlineKeyboardMarkup(inline_keyboard=[]),
    )
    await callback_query.answer()
