import config

from aiogram import F, Bot, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from content import backlog_ct, plan_ct, plan_habits_ct, plan_tasks_ct, planning_select_date_ct, reminder_draft_ct, rituals_ct, task_ct
from fsm_state import FsmState
from interfaces.plan import PlanModel, ReminderModel, TaskModel
from interfaces.state import FullState
from keyboards import (
    PlanningAddTag, PlanningEditActions, PlanningSelectDate, PlanningTaskDuration, 
    PlanningTaskFields, PlanningTaskPosition, PlanningTasksActions, TimeOptions,
    PlanningHabitToggle, PlanningReminderActions, PlanningReminderFields, PlanningDeleteReminder,
    PlanningDeleteTask, PlanningAddRitual, PlanningGoalTag,
    planning_add_tag_kb, planning_edit_actions_kb, planning_select_date_kb, 
    planning_task_duration_kb, planning_task_fields_kb, planning_task_position_kb, 
    planning_tasks_actions_kb, time_options_kb, BacklogSelectTask,
    backlog_tasks_list_kb, planning_habits_kb, planning_reminder_fields_kb, planning_reminders_kb,
    planning_delete_task_kb, planning_add_ritual_kb, planning_goal_tags_kb
)
from enums import OptionAction, PlanningEditAction, PlanningTaskField, PlanningTasksAction, PlanningHabitAction, PlanningReminderAction, PlanningReminderField
from memory.memory import Memory
from utils.chat import delete_chat_message
from utils.state import update_state
from utils.ui import render_menu
from uuid import uuid4

router = Router(name=__name__)

@router.callback_query(PlanningSelectDate.filter())
async def planning_select_date(
    callback_query: types.CallbackQuery,
    callback_data: PlanningSelectDate, 
    state: FSMContext, 
    bot: Bot
):
    full_state = Memory(path="./state.json", model=FullState)
    full_state.data.tmp = {"plan_file": callback_data.file}
    keyboard_message_id = full_state.data.bot_dialog_message_id
    full_state.save()

    await render_menu(
        bot,
        keyboard_message_id,
        plan_ct(callback_data.file),
        planning_edit_actions_kb()
    )
    await callback_query.answer()

@router.callback_query(PlanningEditActions.filter())
async def planning_edit_actions(
    callback_query: types.CallbackQuery,
    callback_data: PlanningEditActions, 
    state: FSMContext, 
    bot: Bot
):
    full_state = Memory(path="./state.json", model=FullState)
    keyboard_message_id = full_state.data.bot_dialog_message_id
    plan_file = str(full_state.data.tmp.get('plan_file'))

    if callback_data.action == PlanningEditAction.WAKEUP_TIME:
        await bot.edit_message_reply_markup(
            chat_id=config.OWNER_ID,
            message_id=keyboard_message_id,
            reply_markup=time_options_kb(obj="plan", field="wakeup_time", offset=20)
        )
    elif callback_data.action == PlanningEditAction.SLEEP_TIME:
        await bot.edit_message_reply_markup(
            chat_id=config.OWNER_ID,
            message_id=keyboard_message_id,
            reply_markup=time_options_kb(obj="plan", field="sleep_time", offset=78)
        )
    elif callback_data.action == PlanningEditAction.TASKS:
        await render_menu(bot, keyboard_message_id, plan_tasks_ct(plan_file), planning_tasks_actions_kb())
    elif callback_data.action == PlanningEditAction.HABITS:
        from services.habits import HabitsStore
        plan = Memory(path=f"./calendar/{plan_file}", model=PlanModel)
        habits = HabitsStore().list()
        selected = {habit.uuid for habit in plan.data.habits}
        await render_menu(
            bot,
            keyboard_message_id,
            plan_habits_ct(plan_file),
            planning_habits_kb(habits, selected),
        )
    elif callback_data.action == PlanningEditAction.REMINDERS:
        plan = Memory(path=f"./calendar/{plan_file}", model=PlanModel)
        await render_menu(
            bot,
            keyboard_message_id,
            "Reminders for this plan:",
            planning_reminders_kb(plan.data.reminders),
        )
    elif callback_data.action == PlanningEditAction.GO_BACK:
        await render_menu(bot, keyboard_message_id, planning_select_date_ct(), planning_select_date_kb())

    await callback_query.answer()

@router.callback_query(TimeOptions.filter(), FsmState.PLAN)
async def time_actions(
    callback_query: types.CallbackQuery,
    callback_data: TimeOptions, 
    state: FSMContext, 
    bot: Bot
):
    full_state = Memory(path="./state.json", model=FullState)
    keyboard_message_id = full_state.data.bot_dialog_message_id

    plan_file = full_state.data.tmp.get('plan_file')
    if not plan_file:
        await callback_query.answer(
            "Select a planning date first", show_alert=True
        )
        return

    if callback_data.offset is not None:
        offset = callback_data.offset
        reply_markup = time_options_kb(
            obj=callback_data.obj or "plan",
            field=callback_data.field or "sleep_time",
            offset=offset,
        )
        await bot.edit_message_reply_markup(
            chat_id=config.OWNER_ID,
            message_id=keyboard_message_id,
            reply_markup=reply_markup
        )
    else:
        value = None
        if callback_data.value is not None and callback_data.value != OptionAction.NONE:
            value = callback_data.value

        if callback_data.obj == "reminder":
            await update_state(
                tmp={"reminder_draft": {"datetime": value}}
            )
            await render_menu(
                bot,
                keyboard_message_id,
                reminder_draft_ct(),
                planning_reminder_fields_kb(),
            )
        else:
            plan = Memory(path=f"./calendar/{plan_file}", model=PlanModel)
            if callback_data.field == "wakeup_time":
                plan.data.wakeup_time = value
            elif callback_data.field == "sleep_time":
                plan.data.sleep_time = value
            plan.save()
            await render_menu(
                bot,
                keyboard_message_id,
                plan_ct(plan_file),
                planning_edit_actions_kb(),
            )

    await callback_query.answer()

@router.callback_query(PlanningTasksActions.filter())
async def planning_tasks_actions(
    callback_query: types.CallbackQuery,
    callback_data: PlanningTasksActions, 
    state: FSMContext, 
    bot: Bot
):
    full_state = Memory(path="./state.json", model=FullState)
    keyboard_message_id = full_state.data.bot_dialog_message_id
    plan_file = str(full_state.data.tmp.get('plan_file'))

    if callback_data.action == PlanningTasksAction.ADD_RITUAL:
        from services.rituals import RitualsStore
        rituals = RitualsStore().list()
        text = rituals_ct("Select a ritual to add:")
        await render_menu(
            bot,
            keyboard_message_id,
            text,
            planning_add_ritual_kb(rituals),
        )
    elif callback_data.action == PlanningTasksAction.ADD_TASK:
        await update_state(
            tmp={
                "task_context": "plan",
                "task": {
                    "uuid": str(uuid4()),
                    "name": "...",
                    "recommended_start_time": None,
                    "recommended_end_time": None,
                    "expected_duration": None,
                    "position": None,
                    "tags": [],
                    "checklist": [],
                },
            },
        )
        await render_menu(bot, keyboard_message_id, task_ct(), planning_task_fields_kb())
    elif callback_data.action == PlanningTasksAction.ADD_FROM_BACKLOG:
        from memory.documents import Documents
        from interfaces.document import DocumentType
        documents = Documents()
        docs = documents.get_list(type=DocumentType.TASK_MODEL)
        tasks_info = []
        for doc in docs:
            task_data = cast(TaskModel, documents.read(doc.uuid))
            tasks_info.append({"uuid": doc.uuid, "name": task_data.name})
        await render_menu(bot, keyboard_message_id, "Select a task from the backlog:", backlog_tasks_list_kb(tasks_info))
    elif callback_data.action == PlanningTasksAction.DELETE_TASK:
        plan = Memory(path=f"./calendar/{plan_file}", model=PlanModel)
        text = "Select a task to delete:" if plan.data.tasks else "No tasks to delete."
        await render_menu(
            bot,
            keyboard_message_id,
            text,
            planning_delete_task_kb(plan.data.tasks),
        )
    elif callback_data.action == PlanningTasksAction.GO_BACK:
        await render_menu(bot, keyboard_message_id, plan_ct(plan_file), planning_edit_actions_kb())

    await callback_query.answer()

@router.callback_query(PlanningTaskFields.filter())
async def planning_task_fields(
    callback_query: types.CallbackQuery,
    callback_data: PlanningTaskFields, 
    state: FSMContext, 
    bot: Bot
):
    full_state = Memory(path="./state.json", model=FullState)
    keyboard_message_id = full_state.data.bot_dialog_message_id
    bot_hint_message_id = full_state.data.bot_hint_message_id

    if bot_hint_message_id is not None:
        await delete_chat_message(id=bot_hint_message_id, bot=bot)

    plan_file = str(full_state.data.tmp.get('plan_file'))
    plan_path = f"./calendar/{plan_file}"
    plan = Memory(path=plan_path, model=PlanModel)

    if callback_data.action in (PlanningTaskField.NAME, PlanningTaskField.CHECKPOINTS):
        await state.set_state(FsmState.TASK)
        await bot.edit_message_reply_markup(
            chat_id=config.OWNER_ID,
            message_id=keyboard_message_id,
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[])
        )
        item_name = (
            "ritual"
            if full_state.data.tmp.get("task_context") == "ritual"
            else "task"
        )
        field_prompt = (
            f"{item_name} name"
            if callback_data.action == PlanningTaskField.NAME
            else "checkpoint"
        )
        wait_field = "task_name" if callback_data.action == PlanningTaskField.NAME else "task_checkpoint"
        
        msg = await bot.send_message(chat_id=config.OWNER_ID, text=f"please type {field_prompt}")
        await update_state(bot_hint_message_id=msg.message_id, tmp={"wait_field": wait_field})
        
    elif callback_data.action == PlanningTaskField.TAGS:
        task_data = full_state.data.tmp.get("task", {})
        actual_tag = task_data.get("tags", [None])[0] if task_data.get("tags") else None
        await render_menu(bot, keyboard_message_id, task_ct(), planning_add_tag_kb(actual_tag))
        
    elif callback_data.action == PlanningTaskField.POSITION:
        task_data = full_state.data.tmp.get("task", {})
        actual_position = str(task_data.get("position")) if task_data.get("position") is not None else None
        await render_menu(bot, keyboard_message_id, task_ct(), planning_task_position_kb(actual_position))
        
    elif callback_data.action == PlanningTaskField.DURATION:
        task_data = full_state.data.tmp.get("task", {})
        actual_duration = str(task_data.get("expected_duration")) if task_data.get("expected_duration") is not None else None
        await render_menu(bot, keyboard_message_id, task_ct(), planning_task_duration_kb(actual_duration))
        
    elif callback_data.action == PlanningTaskField.ADD_TASK:
        task_payload = full_state.data.tmp.get("task", {})
        if not str(task_payload.get("name", "")).strip() or task_payload.get("name") == "...":
            item_name = (
                "ritual"
                if full_state.data.tmp.get("task_context") == "ritual"
                else "task"
            )
            await callback_query.answer(
                f"Set a {item_name} name first", show_alert=True
            )
            return
        task_context = full_state.data.tmp.get("task_context", "plan")
        if task_context == "backlog":
            from memory.documents import Documents
            from interfaces.document import DocumentType
            Documents().create(
                value=task_payload,
                type_hint=DocumentType.TASK_MODEL,
                brief=task_payload.get("name"),
                tags=task_payload.get("tags"),
            )
            await state.set_state(default_state)
            await update_state(tmp={}, replace_tmp=True)
            from keyboards import backlog_actions_kb
            await render_menu(
                bot,
                keyboard_message_id,
                backlog_ct(f"Task '{task_payload['name']}' added to backlog!"),
                backlog_actions_kb(),
            )
        elif task_context == "ritual":
            from services.rituals import RitualsStore
            ritual = RitualsStore().create(task_payload)
            await state.set_state(default_state)
            await update_state(tmp={}, replace_tmp=True)
            from keyboards import ritual_actions_kb
            await render_menu(
                bot,
                keyboard_message_id,
                rituals_ct(f"Ritual '{ritual.name}' created!"),
                ritual_actions_kb(),
            )
        else:
            plan = Memory(path=f"./calendar/{plan_file}", model=PlanModel)
            await state.set_state(FsmState.PLAN)
            plan.data.tasks.append(task_payload)
            plan.save()
            await render_menu(bot, keyboard_message_id, plan_tasks_ct(plan_file), planning_tasks_actions_kb())
        
    elif callback_data.action == PlanningTaskField.GO_BACK:
        task_context = full_state.data.tmp.get("task_context", "plan")
        if task_context == "ritual":
            from keyboards import ritual_actions_kb
            await state.set_state(default_state)
            await update_state(tmp={}, replace_tmp=True)
            await render_menu(
                bot, keyboard_message_id, rituals_ct(), ritual_actions_kb()
            )
        elif task_context == "backlog":
            from keyboards import backlog_actions_kb
            await state.set_state(default_state)
            await render_menu(
                bot, keyboard_message_id, backlog_ct(), backlog_actions_kb()
            )
        else:
            await state.set_state(FsmState.PLAN)
            await render_menu(bot, keyboard_message_id, plan_tasks_ct(plan_file), planning_tasks_actions_kb())

    await callback_query.answer()

@router.callback_query(PlanningAddTag.filter())
async def planning_add_tag(
    callback_query: types.CallbackQuery,
    callback_data: PlanningAddTag, 
    state: FSMContext, 
    bot: Bot
):
    full_state = Memory(path="./state.json", model=FullState)
    keyboard_message_id = full_state.data.bot_dialog_message_id
    bot_hint_message_id = full_state.data.bot_hint_message_id

    if bot_hint_message_id is not None:
        await delete_chat_message(id=bot_hint_message_id, bot=bot)

    if callback_data.value == config.GOAL_TAG:
        from services.goals import GoalsStore
        full_state.data.tmp["task"]["tags"] = [config.GOAL_TAG]
        full_state.save()
        store = GoalsStore()
        await render_menu(
            bot,
            keyboard_message_id,
            "Select a goal or subgoal. This is optional:",
            planning_goal_tags_kb(list(store.iter_nodes())),
        )
        await callback_query.answer()
        return
    if callback_data.value == OptionAction.NONE:
        full_state.data.tmp["task"]["tags"] = []
        full_state.save()
    elif callback_data.value != OptionAction.GO_BACK:
        tags = [config.GOAL_TAG, config.RITUAL_TAG, config.OTHER_TAG]
        if callback_data.value in tags:
            current_tags = full_state.data.tmp.get("task", {}).get("tags", [])
            if current_tags and current_tags[0] == callback_data.value:
                full_state.data.tmp["task"]["tags"] = []
            else:
                full_state.data.tmp["task"]["tags"] = [callback_data.value]
            full_state.save()       

    await render_menu(bot, keyboard_message_id, task_ct(), planning_task_fields_kb())
    await callback_query.answer()


@router.callback_query(PlanningGoalTag.filter())
async def planning_goal_tag(
    callback_query: types.CallbackQuery,
    callback_data: PlanningGoalTag,
    bot: Bot,
):
    from services.goals import GoalsStore

    full_state = Memory("state.json", FullState)
    keyboard_message_id = full_state.data.bot_dialog_message_id
    if callback_data.uuid == "back":
        await render_menu(
            bot, keyboard_message_id, task_ct(), planning_task_fields_kb()
        )
        await callback_query.answer()
        return
    if callback_data.uuid == "remove":
        full_state.data.tmp["task"]["tags"] = []
    elif callback_data.uuid == "general":
        full_state.data.tmp["task"]["tags"] = [config.GOAL_TAG]
    else:
        node = GoalsStore().get(callback_data.uuid)
        if node is None:
            await callback_query.answer("Goal no longer exists", show_alert=True)
            return
        full_state.data.tmp["task"]["tags"] = [config.GOAL_TAG, node.tag]
    full_state.save()
    await render_menu(
        bot, keyboard_message_id, task_ct(), planning_task_fields_kb()
    )
    await callback_query.answer()

@router.callback_query(PlanningTaskPosition.filter())
async def planning_add_task_position(
    callback_query: types.CallbackQuery,
    callback_data: PlanningTaskPosition, 
    state: FSMContext, 
    bot: Bot
):
    full_state = Memory(path="./state.json", model=FullState)
    keyboard_message_id = full_state.data.bot_dialog_message_id
    bot_hint_message_id = full_state.data.bot_hint_message_id

    if bot_hint_message_id is not None:
        await delete_chat_message(id=bot_hint_message_id, bot=bot)

    if callback_data.value != OptionAction.GO_BACK:
        if callback_data.value == OptionAction.NONE:
            full_state.data.tmp["task"]["position"] = None
        elif callback_data.value == "middle":
            full_state.data.tmp["task"]["position"] = callback_data.value
        else:
            full_state.data.tmp["task"]["position"] = int(callback_data.value)
        full_state.save()  

    await render_menu(bot, keyboard_message_id, task_ct(), planning_task_fields_kb())
    await callback_query.answer()

@router.callback_query(PlanningTaskDuration.filter())
async def planning_add_task_duration(
    callback_query: types.CallbackQuery,
    callback_data: PlanningTaskDuration, 
    state: FSMContext, 
    bot: Bot
):
    full_state = Memory(path="./state.json", model=FullState)
    keyboard_message_id = full_state.data.bot_dialog_message_id
    bot_hint_message_id = full_state.data.bot_hint_message_id

    if bot_hint_message_id is not None:
        await delete_chat_message(id=bot_hint_message_id, bot=bot)

    if callback_data.value != OptionAction.GO_BACK:
        if callback_data.value == OptionAction.NONE:
            full_state.data.tmp["task"]["expected_duration"] = None
        else:
            full_state.data.tmp["task"]["expected_duration"] = callback_data.value
        full_state.save()  

    await render_menu(bot, keyboard_message_id, task_ct(), planning_task_fields_kb())
    await callback_query.answer()

@router.callback_query(BacklogSelectTask.filter())
async def backlog_select_task(
    callback_query: types.CallbackQuery,
    callback_data: BacklogSelectTask, 
    state: FSMContext, 
    bot: Bot
):
    from memory.documents import Documents
    full_state = Memory(path="./state.json", model=FullState)
    keyboard_message_id = full_state.data.bot_dialog_message_id

    plan_file = str(full_state.data.tmp.get('plan_file'))
    plan_path = f"./calendar/{plan_file}"
    plan = Memory(path=plan_path, model=PlanModel)

    # Read the task from backlog
    documents = Documents()
    task_model = cast(TaskModel, documents.read(callback_data.uuid))
    
    # Append to plan
    plan.data.tasks.append(task_model)
    plan.save()

    # Delete from backlog
    documents.delete(callback_data.uuid)

    # Return to plan tasks menu
    await render_menu(bot, keyboard_message_id, plan_tasks_ct(plan_file), planning_tasks_actions_kb())
    await callback_query.answer()

@router.callback_query(PlanningDeleteTask.filter())
async def planning_delete_task(
    callback_query: types.CallbackQuery,
    callback_data: PlanningDeleteTask,
    bot: Bot,
):
    full_state = Memory(path="./state.json", model=FullState)
    plan_file = str(full_state.data.tmp.get("plan_file"))
    plan = Memory(path=f"./calendar/{plan_file}", model=PlanModel)
    plan.data.tasks = [
        task for task in plan.data.tasks if task.uuid != callback_data.uuid
    ]
    plan.save()
    await render_menu(
        bot,
        full_state.data.bot_dialog_message_id,
        plan_tasks_ct(plan_file),
        planning_tasks_actions_kb(),
    )
    await callback_query.answer("Task deleted")

@router.callback_query(PlanningAddRitual.filter())
async def planning_add_ritual(
    callback_query: types.CallbackQuery,
    callback_data: PlanningAddRitual,
    bot: Bot,
):
    from services.rituals import RitualsStore
    full_state = Memory(path="./state.json", model=FullState)
    plan_file = str(full_state.data.tmp.get("plan_file"))
    plan = Memory(path=f"./calendar/{plan_file}", model=PlanModel)
    task = RitualsStore().as_plan_task(callback_data.uuid)
    if task is None:
        await callback_query.answer("Ritual no longer exists", show_alert=True)
        return
    plan.data.tasks.append(task)
    plan.save()
    await render_menu(
        bot,
        full_state.data.bot_dialog_message_id,
        plan_tasks_ct(plan_file),
        planning_tasks_actions_kb(),
    )
    await callback_query.answer("Ritual added")

@router.callback_query(PlanningHabitToggle.filter())
async def planning_toggle_habit(
    callback_query: types.CallbackQuery,
    callback_data: PlanningHabitToggle,
    bot: Bot,
):
    from services.habits import HabitsStore
    full_state = Memory(path="./state.json", model=FullState)
    plan_file = full_state.data.tmp.get("plan_file")
    if not plan_file:
        await callback_query.answer(
            "Select a planning date first", show_alert=True
        )
        return
    plan = Memory(path=f"./calendar/{plan_file}", model=PlanModel)
    store = HabitsStore()
    global_habits = store.list()

    if callback_data.action == PlanningHabitAction.GO_BACK:
        await render_menu(
            bot,
            full_state.data.bot_dialog_message_id,
            plan_ct(plan_file),
            planning_edit_actions_kb(),
        )
    elif callback_data.action == PlanningHabitAction.ADD_ALL:
        selected_uuids = {habit.uuid for habit in plan.data.habits}
        missing = [
            habit for habit in global_habits
            if habit.uuid not in selected_uuids
        ]
        plan.data.habits.extend(missing)
        plan.save()
        await render_menu(
            bot,
            full_state.data.bot_dialog_message_id,
            plan_habits_ct(plan_file),
            planning_habits_kb(
                global_habits, {habit.uuid for habit in plan.data.habits}
            ),
        )
        await callback_query.answer(
            f"Added {len(missing)} habit{'s' if len(missing) != 1 else ''}"
        )
        return
    elif (
        callback_data.action == PlanningHabitAction.TOGGLE_HABIT
        and callback_data.uuid
    ):
        selected = next(
            (habit for habit in plan.data.habits if habit.uuid == callback_data.uuid),
            None,
        )
        if selected:
            plan.data.habits.remove(selected)
        else:
            habit = store.get(callback_data.uuid)
            if habit:
                plan.data.habits.append(habit)
        plan.save()
        await render_menu(
            bot,
            full_state.data.bot_dialog_message_id,
            plan_habits_ct(plan_file),
            planning_habits_kb(
                global_habits, {habit.uuid for habit in plan.data.habits}
            ),
        )
    await callback_query.answer()

@router.callback_query(PlanningReminderActions.filter())
async def planning_reminder_actions(
    callback_query: types.CallbackQuery,
    callback_data: PlanningReminderActions,
    state: FSMContext,
    bot: Bot,
):
    full_state = Memory(path="./state.json", model=FullState)
    plan_file = str(full_state.data.tmp.get("plan_file"))
    if callback_data.action == PlanningReminderAction.ADD_REMINDER:
        full_state.data.tmp.pop("reminder_draft", None)
        full_state.data.tmp["reminder_draft"] = {
            "name": None,
            "datetime": None,
            "description": None,
        }
        full_state.save()
        await render_menu(
            bot,
            full_state.data.bot_dialog_message_id,
            reminder_draft_ct(),
            planning_reminder_fields_kb(),
        )
    else:
        full_state.data.tmp.pop("reminder_draft", None)
        full_state.data.tmp.pop("wait_field", None)
        full_state.save()
        await render_menu(
            bot,
            full_state.data.bot_dialog_message_id,
            plan_ct(plan_file),
            planning_edit_actions_kb(),
        )
    await callback_query.answer()

@router.callback_query(PlanningReminderFields.filter())
async def planning_reminder_fields(
    callback_query: types.CallbackQuery,
    callback_data: PlanningReminderFields,
    state: FSMContext,
    bot: Bot,
):
    full_state = Memory(path="./state.json", model=FullState)
    keyboard_message_id = full_state.data.bot_dialog_message_id
    plan_file = full_state.data.tmp.get("plan_file")
    if not plan_file:
        await callback_query.answer(
            "Select a planning date first", show_alert=True
        )
        return
    if "reminder_draft" not in full_state.data.tmp:
        await callback_query.answer("Reminder draft expired", show_alert=True)
        plan = Memory(path=f"./calendar/{plan_file}", model=PlanModel)
        await render_menu(
            bot,
            keyboard_message_id,
            "Reminders for this plan:",
            planning_reminders_kb(plan.data.reminders),
        )
        return

    if callback_data.action in {
        PlanningReminderField.NAME,
        PlanningReminderField.DESCRIPTION,
    }:
        await state.set_state(FsmState.REMINDER)
        field = (
            "reminder_name"
            if callback_data.action == PlanningReminderField.NAME
            else "reminder_description"
        )
        prompt = "reminder name" if field == "reminder_name" else "description"
        message = await bot.send_message(
            chat_id=config.OWNER_ID,
            text=f"Please type the {prompt}:",
        )
        await update_state(
            bot_hint_message_id=message.message_id,
            tmp={"wait_field": field},
        )
    elif callback_data.action == PlanningReminderField.TIME:
        await bot.edit_message_reply_markup(
            chat_id=config.OWNER_ID,
            message_id=keyboard_message_id,
            reply_markup=time_options_kb(
                obj="reminder", field="datetime", offset=32
            ),
        )
    elif callback_data.action == PlanningReminderField.SAVE:
        draft = full_state.data.tmp.get("reminder_draft", {})
        if not draft.get("name"):
            await callback_query.answer("Set a reminder name first", show_alert=True)
            return
        if not draft.get("datetime"):
            await callback_query.answer("Set a reminder time first", show_alert=True)
            return
        reminder = ReminderModel.model_validate(draft)
        plan = Memory(path=f"./calendar/{plan_file}", model=PlanModel)
        plan.data.reminders.append(reminder)
        plan.save()
        full_state.data.tmp.pop("reminder_draft", None)
        full_state.data.tmp.pop("wait_field", None)
        full_state.save()
        await state.set_state(FsmState.PLAN)
        await render_menu(
            bot,
            keyboard_message_id,
            "Reminders for this plan:",
            planning_reminders_kb(plan.data.reminders),
        )
    elif callback_data.action == PlanningReminderField.GO_BACK:
        full_state.data.tmp.pop("reminder_draft", None)
        full_state.data.tmp.pop("wait_field", None)
        full_state.save()
        await state.set_state(FsmState.PLAN)
        plan = Memory(path=f"./calendar/{plan_file}", model=PlanModel)
        await render_menu(
            bot,
            keyboard_message_id,
            "Reminders for this plan:",
            planning_reminders_kb(plan.data.reminders),
        )
    await callback_query.answer()

@router.callback_query(PlanningDeleteReminder.filter())
async def planning_delete_reminder(
    callback_query: types.CallbackQuery,
    callback_data: PlanningDeleteReminder,
    bot: Bot,
):
    full_state = Memory(path="./state.json", model=FullState)
    plan_file = full_state.data.tmp.get("plan_file")
    plan = Memory(path=f"./calendar/{plan_file}", model=PlanModel)
    if 0 <= callback_data.index < len(plan.data.reminders):
        plan.data.reminders.pop(callback_data.index)
        plan.save()
    await render_menu(
        bot,
        full_state.data.bot_dialog_message_id,
        "Reminders for this plan:",
        planning_reminders_kb(plan.data.reminders),
    )
    await callback_query.answer("Reminder deleted")
