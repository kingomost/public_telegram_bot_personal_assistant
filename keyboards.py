from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters.callback_data import CallbackData
from interfaces.plan import PlanModel, TaskModel
from interfaces.state import FullState
from memory.memory import Memory
from utils.datetime import list_of_dates

from enums import AlarmAction, OptionAction, PlanningEditAction, PlanningTaskField, PlanningTasksAction, BacklogAction, BacklogTaskAction, HabitAction, RitualAction, ExecutionAction, ExecutionCheckpointAction, HabitTrackerAction, DayAction, GoalAction, GoalNodeAction, ReportAction, PlanningHabitAction, PlanningReminderAction, PlanningReminderField
import config

def _button_rows(buttons: list[InlineKeyboardButton], columns: int = 2):
    return [
        buttons[index:index + columns]
        for index in range(0, len(buttons), columns)
    ]

class ExecutionActions(CallbackData, prefix="ExecutionActions"):
    action: ExecutionAction

def active_task_kb():
    Ikb = InlineKeyboardButton
    Cbd = ExecutionActions
    Act = ExecutionAction
    return InlineKeyboardMarkup(inline_keyboard=[
        [Ikb(text="⏸ Pause", callback_data=Cbd(action=Act.PAUSE_TASK).pack()), Ikb(text="⏱ +5 Min", callback_data=Cbd(action=Act.ADD_TIME).pack())],
        [Ikb(text="✅ Finish", callback_data=Cbd(action=Act.FINISH_TASK).pack())],
        [Ikb(text="Go back", callback_data=Cbd(action=Act.GO_BACK).pack())]
    ])

class ExecutionSelectTask(CallbackData, prefix="ExecutionSelectTask"):
    uuid: str

def execution_select_task_kb(tasks):
    Ikb = InlineKeyboardButton
    Cbd = ExecutionSelectTask
    buttons = [
        Ikb(text=task["name"], callback_data=Cbd(uuid=task["uuid"]).pack())
        for task in tasks
    ]
    inline_keyboard = _button_rows(buttons, columns=2)

    inline_keyboard.append([
        Ikb(
            text="➕ Create quickly",
            callback_data=ExecutionActions(
                action=ExecutionAction.QUICK_CREATE
            ).pack(),
        )
    ])
    inline_keyboard.append([Ikb(text="Go back", callback_data=ExecutionActions(action=ExecutionAction.GO_BACK).pack())])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

class ExecutionCheckpoint(CallbackData, prefix="ExecCheckpoint"):
    index: int

class ExecutionCheckpointDone(CallbackData, prefix="ExecCheckpointDone"):
    action: ExecutionCheckpointAction

def execution_checkpoints_kb(checkpoints) -> InlineKeyboardMarkup:
    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=f"{'✅' if checkpoint.completed else '⬜'} {checkpoint.name}",
                callback_data=ExecutionCheckpoint(index=index).pack(),
            )
        ]
        for index, checkpoint in enumerate(checkpoints)
    ]
    inline_keyboard.append([
        InlineKeyboardButton(
            text="Done",
            callback_data=ExecutionCheckpointDone(
                action=ExecutionCheckpointAction.DONE
            ).pack(),
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

class HabitTrackerSelect(CallbackData, prefix="HabitTrackSelect"):
    uuid: str

class HabitTrackerAdjust(CallbackData, prefix="HabitTrackAdjust"):
    uuid: str
    delta: int

class HabitTrackerActions(CallbackData, prefix="HabitTrackActions"):
    action: HabitTrackerAction

def habit_tracker_list_kb(habits, counts: dict[str, int]) -> InlineKeyboardMarkup:
    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=f"{habit.name}: {counts.get(habit.uuid, 0)}",
                callback_data=HabitTrackerSelect(uuid=habit.uuid).pack(),
            )
        ]
        for habit in habits
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def habit_tracker_adjust_kb(uuid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➖ -1",
                callback_data=HabitTrackerAdjust(uuid=uuid, delta=-1).pack(),
            ),
            InlineKeyboardButton(
                text="➕ +1",
                callback_data=HabitTrackerAdjust(uuid=uuid, delta=1).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Go back",
                callback_data=HabitTrackerActions(
                    action=HabitTrackerAction.GO_BACK
                ).pack(),
            )
        ],
    ])

class DayActions(CallbackData, prefix="DayActions"):
    action: DayAction

class AlarmActions(CallbackData, prefix="AlarmActions"):
    action: AlarmAction

class ActualSleepTime(CallbackData, prefix="ActualSleepTime", sep=";"):
    value: str | None = None
    offset: int | None = None

def alarm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="☀️ I am awake",
                callback_data=AlarmActions(action=AlarmAction.WOKE_UP).pack(),
            )
        ]
    ])

def actual_sleep_time_kb(offset: int = 76, count: int = 12) -> InlineKeyboardMarkup:
    times = [
        f"{hour:02d}:{minute:02d}"
        for hour in range(24)
        for minute in range(0, 60, 15)
    ]
    offset = min(max(offset, 0), max(len(times) - count, 0))
    selected = times[offset:offset + count]
    rows = [
        [
            InlineKeyboardButton(
                text=value,
                callback_data=ActualSleepTime(value=value).pack(),
            )
            for value in selected[index:index + 4]
        ]
        for index in range(0, len(selected), 4)
    ]
    navigation = []
    if offset > 0:
        navigation.append(InlineKeyboardButton(
            text="<",
            callback_data=ActualSleepTime(
                offset=max(0, offset - count)
            ).pack(),
        ))
    if offset + count < len(times):
        navigation.append(InlineKeyboardButton(
            text=">",
            callback_data=ActualSleepTime(
                offset=min(len(times) - count, offset + count)
            ).pack(),
        ))
    if navigation:
        rows.append(navigation)
    return InlineKeyboardMarkup(inline_keyboard=rows)

def day_actions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="☀️ I woke up",
                callback_data=DayActions(action=DayAction.WAKEUP).pack(),
            ),
            InlineKeyboardButton(
                text="🌙 Going to sleep",
                callback_data=DayActions(action=DayAction.SLEEP).pack(),
            ),
        ]
    ])

class GoalActions(CallbackData, prefix="GoalActions"):
    action: GoalAction

class GoalSelect(CallbackData, prefix="GoalSelect"):
    uuid: str

class GoalNodeActions(CallbackData, prefix="GoalNode"):
    action: GoalNodeAction
    uuid: str

class GoalBudgetField(CallbackData, prefix="GBF"):
    field: str
    uuid: str

class GoalBudgetValue(CallbackData, prefix="GBV"):
    field: str
    uuid: str
    value: int | None = None
    offset: int | None = None

class GoalDurationValue(CallbackData, prefix="GDV"):
    uuid: str
    value: int | None = None
    offset: int | None = None

def _number_options_kb(
    values: list[int],
    offset: int,
    count: int,
    callback,
) -> InlineKeyboardMarkup:
    offset = min(max(offset, 0), max(len(values) - count, 0))
    selected = values[offset:offset + count]
    rows = [
        [
            InlineKeyboardButton(text=str(value), callback_data=callback(value, None))
            for value in selected[index:index + 4]
        ]
        for index in range(0, len(selected), 4)
    ]
    navigation = []
    if offset > 0:
        navigation.append(InlineKeyboardButton(
            text="<", callback_data=callback(None, max(0, offset - count))
        ))
    if offset + count < len(values):
        navigation.append(InlineKeyboardButton(
            text=">",
            callback_data=callback(None, min(len(values) - count, offset + count)),
        ))
    if navigation:
        rows.append(navigation)
    return InlineKeyboardMarkup(inline_keyboard=rows)

def goal_budget_kb(
    uuid: str,
    min_hours: int | None,
    max_hours: int | None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"Set min ({min_hours if min_hours is not None else 'not set'})",
                callback_data=GoalBudgetField(field="min", uuid=uuid).pack(),
            ),
            InlineKeyboardButton(
                text=f"Set max ({max_hours if max_hours is not None else 'not set'})",
                callback_data=GoalBudgetField(field="max", uuid=uuid).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Go back",
                callback_data=GoalSelect(uuid=uuid).pack(),
            )
        ],
    ])

def goal_budget_values_kb(
    uuid: str,
    field: str,
    min_hours: int | None,
    max_hours: int | None,
    offset: int | None = None,
) -> InlineKeyboardMarkup:
    if field == "min":
        upper = max_hours if max_hours is not None else 1000
        values = list(range(0, upper + 1, 20))
        initial_offset = 10
    else:
        lower = min_hours if min_hours is not None else 0
        values = list(range(lower, 1001, 20))
        initial_offset = 15
    return _number_options_kb(
        values,
        initial_offset if offset is None else offset,
        12,
        lambda value, page: GoalBudgetValue(
            field=field, uuid=uuid, value=value, offset=page
        ).pack(),
    )

def goal_duration_kb(
    uuid: str, offset: int = 0
) -> InlineKeyboardMarkup:
    return _number_options_kb(
        list(range(0, 101, 5)),
        offset,
        12,
        lambda value, page: GoalDurationValue(
            uuid=uuid, value=value, offset=page
        ).pack(),
    )

def goals_kb(nodes) -> InlineKeyboardMarkup:
    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=f"{'  ' * depth}{'✅' if node.done else '🎯'} {node.name}",
                callback_data=GoalSelect(uuid=node.uuid).pack(),
            )
        ]
        for node, depth, _ in nodes
    ]
    inline_keyboard.append([
        InlineKeyboardButton(
            text="➕ Add goal",
            callback_data=GoalActions(action=GoalAction.ADD).pack(),
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def goal_node_kb(uuid: str) -> InlineKeyboardMarkup:
    callback = GoalNodeActions
    action = GoalNodeAction
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ Subgoal",
                callback_data=callback(action=action.ADD_SUBGOAL, uuid=uuid).pack(),
            ),
            InlineKeyboardButton(
                text="Expected result",
                callback_data=callback(action=action.EXPECTED_RESULT, uuid=uuid).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Time budget",
                callback_data=callback(action=action.BUDGET, uuid=uuid).pack(),
            ),
            InlineKeyboardButton(
                text="Duration days",
                callback_data=callback(action=action.DAYS, uuid=uuid).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="✅ Toggle done",
                callback_data=callback(action=action.TOGGLE_DONE, uuid=uuid).pack(),
            ),
            InlineKeyboardButton(
                text="🗑 Delete",
                callback_data=callback(action=action.DELETE, uuid=uuid).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Go back",
                callback_data=callback(action=action.GO_BACK, uuid=uuid).pack(),
            )
        ],
    ])

class ReportActions(CallbackData, prefix="Reports"):
    action: ReportAction

def reports_kb() -> InlineKeyboardMarkup:
    callback = ReportActions
    action = ReportAction
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Today", callback_data=callback(action=action.TODAY).pack()),
            InlineKeyboardButton(text="Yesterday", callback_data=callback(action=action.YESTERDAY).pack()),
        ],
        [
            InlineKeyboardButton(text="Last 7 days", callback_data=callback(action=action.LAST_7_DAYS).pack()),
            InlineKeyboardButton(text="This week", callback_data=callback(action=action.THIS_WEEK).pack()),
        ],
        [
            InlineKeyboardButton(text="Goal progress", callback_data=callback(action=action.GOALS).pack()),
        ],
    ])

class PlanningGoalTag(CallbackData, prefix="TaskGoal"):
    uuid: str

def planning_goal_tags_kb(nodes) -> InlineKeyboardMarkup:
    inline_keyboard = [[
        InlineKeyboardButton(
            text="General goal work (no subtag)",
            callback_data=PlanningGoalTag(uuid="general").pack(),
        )
    ]]
    inline_keyboard.extend(
        [
            InlineKeyboardButton(
                text=f"{'  ' * depth}{node.name}",
                callback_data=PlanningGoalTag(uuid=node.uuid).pack(),
            )
        ]
        for node, depth, _ in nodes
    )
    inline_keyboard.append([
        InlineKeyboardButton(
            text="Remove goal tag",
            callback_data=PlanningGoalTag(uuid="remove").pack(),
        ),
        InlineKeyboardButton(
            text="Go back",
            callback_data=PlanningGoalTag(uuid="back").pack(),
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

class HabitActions(CallbackData, prefix="HabitActions"):
    action: HabitAction

class HabitRangeOption(CallbackData, prefix="HabitRangeOption"):
    field: str
    value: int

def habit_actions_kb():
    Ikb = InlineKeyboardButton
    Cbd = HabitActions
    Act = HabitAction
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            Ikb(text="➕ Add Habit", callback_data=Cbd(action=Act.ADD_HABIT).pack()), 
        #     Ikb(text="📋 List Habits", callback_data=Cbd(action=Act.LIST_HABITS).pack())
        # ],
        # [
            Ikb(text="🗑 Delete Habit", callback_data=Cbd(action=Act.DELETE_HABIT).pack())
        ],
        # [Ikb(text="Go back", callback_data=Cbd(action=Act.GO_BACK).pack())]
    ])

def habit_range_kb(field: str, minimum: int = 0) -> InlineKeyboardMarkup:
    """Build min/max choices for habit completion criteria."""
    if field not in {"min", "max"}:
        raise ValueError("field must be 'min' or 'max'")
    values = list(range(minimum, 11))
    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=str(value),
                callback_data=HabitRangeOption(field=field, value=value).pack(),
            )
            for value in values[index:index + 4]
        ]
        for index in range(0, len(values), 4)
    ]
    inline_keyboard.append([
        InlineKeyboardButton(
            text="Cancel",
            callback_data=HabitActions(action=HabitAction.GO_BACK).pack(),
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

class RitualActions(CallbackData, prefix="RitualActions"):
    action: RitualAction

def ritual_actions_kb():
    Ikb = InlineKeyboardButton
    Cbd = RitualActions
    Act = RitualAction
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            Ikb(text="➕ Add Ritual", callback_data=Cbd(action=Act.ADD_RITUAL).pack()), 
        #     Ikb(text="📋 List Rituals", callback_data=Cbd(action=Act.LIST_RITUALS).pack())
        # ],
        # [
            Ikb(text="🗑 Delete Ritual", callback_data=Cbd(action=Act.DELETE_RITUAL).pack())
        ],
        # [Ikb(text="Go back", callback_data=Cbd(action=Act.GO_BACK).pack())]
    ])

class HabitSelectDelete(CallbackData, prefix="HabitSelectDelete"):
    uuid: str

def habit_delete_kb(habits):
    """Render each habit as a button for deletion."""
    Ikb = InlineKeyboardButton
    Cbd = HabitSelectDelete
    inline_keyboard = []
    for habit in habits:
        inline_keyboard.append([Ikb(text=f"🗑 {habit.name}", callback_data=Cbd(uuid=habit.uuid).pack())])
    inline_keyboard.append([Ikb(text="Go back", callback_data=HabitActions(action=HabitAction.GO_BACK).pack())])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

class RitualSelectDelete(CallbackData, prefix="RitualSelectDelete"):
    uuid: str

def ritual_delete_kb(rituals):
    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=f"🗑 {ritual.name}",
                callback_data=RitualSelectDelete(uuid=ritual.uuid).pack(),
            )
        ]
        for ritual in rituals
    ]
    inline_keyboard.append([
        InlineKeyboardButton(
            text="Go back",
            callback_data=RitualActions(action=RitualAction.GO_BACK).pack(),
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

class BacklogActions(CallbackData, prefix="BacklogActions"):
    action: BacklogAction

def backlog_actions_kb():
    Ikb = InlineKeyboardButton
    Cbd = BacklogActions
    Act = BacklogAction
    return InlineKeyboardMarkup(inline_keyboard = [
        [
            Ikb(text = "➕ Add Task", callback_data = Cbd(action = Act.ADD_TASK).pack()),
        #     Ikb(text = "📋 List Tasks", callback_data = Cbd(action = Act.LIST_TASKS).pack())
        # ],
        # [
            Ikb(text="🗑 Delete Task", callback_data=Cbd(action=Act.DELETE_TASK).pack()),
        ],
        # [
        #     Ikb(text = "Go back", callback_data = Cbd(action = Act.GO_BACK).pack())
        # ]
    ])

class BacklogSelectDelete(CallbackData, prefix="BacklogSelectDelete"):
    uuid: str

def backlog_delete_kb(tasks):
    """Render backlog tasks as deletion choices."""
    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=f"🗑 {task['name']}",
                callback_data=BacklogSelectDelete(uuid=task["uuid"]).pack(),
            )
        ]
        for task in tasks
    ]
    inline_keyboard.append([
        InlineKeyboardButton(
            text="Go back",
            callback_data=BacklogActions(action=BacklogAction.GO_BACK).pack(),
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

class BacklogSelectTask(CallbackData, prefix="BacklogSelectTask"):
    uuid: str

def backlog_tasks_list_kb(tasks):
    Ikb = InlineKeyboardButton
    Cbd = BacklogSelectTask
    inline_keyboard = []
    for doc in tasks:
        # doc is a Document object. We can use the brief or file name if we didn't load it, 
        # but the caller will likely pass the actual task names or we just load it here.
        # It's better if caller passes a list of tuples (uuid, name)
        inline_keyboard.append([Ikb(text=doc["name"], callback_data=Cbd(uuid=doc["uuid"]).pack())])
    
    inline_keyboard.append([Ikb(text="Go back", callback_data=PlanningTasksActions(action=PlanningTasksAction.GO_BACK).pack())])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

class PlanningDeleteTask(CallbackData, prefix="PlanningDeleteTask"):
    uuid: str

def planning_delete_task_kb(tasks):
    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=f"🗑 {task.name}",
                callback_data=PlanningDeleteTask(uuid=task.uuid or "").pack(),
            )
        ]
        for task in tasks
        if task.uuid
    ]
    inline_keyboard.append([
        InlineKeyboardButton(
            text="Go back",
            callback_data=PlanningTasksActions(
                action=PlanningTasksAction.GO_BACK
            ).pack(),
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

class PlanningAddRitual(CallbackData, prefix="PlanningAddRitual"):
    uuid: str

def planning_add_ritual_kb(rituals):
    buttons = [
        InlineKeyboardButton(
            text=ritual.name,
            callback_data=PlanningAddRitual(uuid=ritual.uuid).pack(),
        )
        for ritual in rituals
    ]
    inline_keyboard = _button_rows(buttons, columns=2)
    inline_keyboard.append([
        InlineKeyboardButton(
            text="Go back",
            callback_data=PlanningTasksActions(
                action=PlanningTasksAction.GO_BACK
            ).pack(),
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

class PlanningSelectDate(CallbackData, prefix="PlanningSelectDate"):
    file: str
def planning_select_date_kb():
    list = []
    tmp_row = []
    calendar = list_of_dates(0, 6)
    for day in calendar:
        tmp_row.append(InlineKeyboardButton(
            text = day.replace("_", "."),
            callback_data = PlanningSelectDate(file = f"{day}.json").pack(),
        ))
        if len(tmp_row) == 2:
            list.append(tmp_row)
            tmp_row = []
    return InlineKeyboardMarkup(inline_keyboard = list)

class PlanningEditActions(CallbackData, prefix="PlanningEditActions"):
    action: PlanningEditAction

def planning_edit_actions_kb():
    Ikb = InlineKeyboardButton
    Cbd = PlanningEditActions
    Act = PlanningEditAction
    return InlineKeyboardMarkup(inline_keyboard = [
        [
            Ikb(text = "Wakeup time", callback_data = Cbd(action = Act.WAKEUP_TIME).pack()),
            Ikb(text = "Sleep time", callback_data = Cbd(action = Act.SLEEP_TIME).pack())
        ],
        [
            Ikb(text = "Tasks", callback_data = Cbd(action = Act.TASKS).pack()),
            Ikb(text = "Habits", callback_data = Cbd(action = Act.HABITS).pack())
        ],
        [
            Ikb(text = "Reminders", callback_data = Cbd(action = Act.REMINDERS).pack()),
            Ikb(text = "Go back", callback_data = Cbd(action = Act.GO_BACK).pack())
        ]
    ])

class TimeOptions(CallbackData, prefix="TimeOptions", sep=";"):
    obj: str | None = None
    field: str | None = None
    value: str | None = None
    offset: int | None = None
def time_options_kb(obj: str, field: str, offset: int = 20, count: int = 9):
    if count <= 0:
        raise ValueError("count must be positive")
    times = [
        f"{hour:02d}:{minute:02d}"
        for hour in range(24)
        for minute in range(0, 60, 15)
    ]
    offset = min(max(offset, 0), max(len(times) - count, 0))
    selected = times[offset:offset + count]
    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=value,
                callback_data=TimeOptions(
                    value=value, field=field, obj=obj
                ).pack(),
            )
            for value in selected[index:index + 3]
        ]
        for index in range(0, len(selected), 3)
    ]

    navigation = []
    if offset > 0:
        navigation.append(InlineKeyboardButton(
            text="<",
            callback_data=TimeOptions(
                offset=max(0, offset - count), field=field, obj=obj
            ).pack(),
        ))
    if obj != "reminder":
        navigation.append(InlineKeyboardButton(
            text="None",
            callback_data=TimeOptions(
                value=OptionAction.NONE, field=field, obj=obj
            ).pack(),
        ))
    if offset + count < len(times):
        navigation.append(InlineKeyboardButton(
            text=">",
            callback_data=TimeOptions(
                offset=min(len(times) - count, offset + count),
                field=field,
                obj=obj,
            ).pack(),
        ))
    inline_keyboard.append(navigation)
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

class PlanningTasksActions(CallbackData, prefix="PlanningTasksActions"):
    action: PlanningTasksAction

def planning_tasks_actions_kb():
    Ikb = InlineKeyboardButton
    Cbd = PlanningTasksActions
    Act = PlanningTasksAction

    inline_keyboard = []
    inline_keyboard.append([
        Ikb(text = "Add ritual", callback_data = Cbd(action = Act.ADD_RITUAL).pack()),
        Ikb(text = "Add task", callback_data = Cbd(action = Act.ADD_TASK).pack())
    ])
    inline_keyboard.append([
        Ikb(text = "Add from backlog", callback_data = Cbd(action = Act.ADD_FROM_BACKLOG).pack()),
        Ikb(text = "Delete task", callback_data = Cbd(action = Act.DELETE_TASK).pack())
    ])
    inline_keyboard.append([
        Ikb(text = "Go back", callback_data = Cbd(action = Act.GO_BACK).pack())
    ])

    return InlineKeyboardMarkup(inline_keyboard = inline_keyboard)

class PlanningTaskFields(CallbackData, prefix="PlanningTaskFields"):
    action: PlanningTaskField

def planning_task_fields_kb():
    Ikb = InlineKeyboardButton
    Cbd = PlanningTaskFields
    Act = PlanningTaskField

    inline_keyboard = []
    inline_keyboard.append([
        Ikb(text = "Name", callback_data = Cbd(action = Act.NAME).pack()),
        Ikb(text = "Add checkpoint", callback_data = Cbd(action = Act.CHECKPOINTS).pack()),
        Ikb(text = "Add tag", callback_data = Cbd(action = Act.TAGS).pack())
    ])
    inline_keyboard.append([
        Ikb(text = "Position", callback_data = Cbd(action = Act.POSITION).pack()),
        Ikb(text = "Duration", callback_data = Cbd(action = Act.DURATION).pack())
    ])
    inline_keyboard.append([
        Ikb(text = "Go back", callback_data = Cbd(action = Act.GO_BACK).pack()),
        Ikb(text = "✔️ Save", callback_data = Cbd(action = Act.ADD_TASK).pack())
    ])

    return InlineKeyboardMarkup(inline_keyboard = inline_keyboard)

def _build_single_choice_kb(options: list[str], current_value: str | None, cbd_cls) -> InlineKeyboardMarkup:
    Ikb = InlineKeyboardButton
    kb_row = []
    for opt in options:
        text = f"✔️ {opt}" if opt == current_value else opt
        kb_row.append(Ikb(text=text, callback_data=cbd_cls(value=opt).pack()))
    
    management_row = [
        Ikb(text="None", callback_data=cbd_cls(value=OptionAction.NONE).pack()),
        Ikb(text="Go back", callback_data=cbd_cls(value=OptionAction.GO_BACK).pack()),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[kb_row, management_row])

class PlanningAddTag(CallbackData, prefix="PlanningAddTag"):
    value: str

def planning_add_tag_kb(tag: str | None = None):
    options = [config.GOAL_TAG, config.RITUAL_TAG, config.OTHER_TAG]
    return _build_single_choice_kb(options, tag, PlanningAddTag)

class PlanningTaskPosition(CallbackData, prefix="PlanningTaskPosition"):
    value: str

def planning_task_position_kb(position: str | None = None):
    options = ["1", "2", "middle", "-2", "-1"]
    return _build_single_choice_kb(options, position, PlanningTaskPosition)

class PlanningTaskDuration(CallbackData, prefix="PlanningTaskDuration"):
    value: str

def planning_task_duration_kb(duration: str | None = None):
    options = ["30 min.", "45 min.", "1 hour", "2 hours", "3 hours"]
    return _build_single_choice_kb(options, duration, PlanningTaskDuration)

class PlanningHabitToggle(CallbackData, prefix="PlanHabit"):
    action: PlanningHabitAction
    uuid: str | None = None

def planning_habits_kb(global_habits, plan_habit_uuids):
    """Render global habits as toggleable buttons for planning.

    ``plan_habit_uuids`` is a set/list of UUIDs already in today's plan.
    """
    Ikb = InlineKeyboardButton
    Cbd = PlanningHabitToggle
    Act = PlanningHabitAction
    inline_keyboard = []
    buttons = []
    for habit in global_habits:
        is_active = habit.uuid in plan_habit_uuids
        prefix = "✅" if is_active else "⬜"
        buttons.append(
            Ikb(
                text=f"{prefix} {habit.name}",
                callback_data=Cbd(action=Act.TOGGLE_HABIT, uuid=habit.uuid).pack(),
            )
        )
    inline_keyboard.extend(_button_rows(buttons, columns=2))
    if global_habits:
        inline_keyboard.append([
            Ikb(
                text="➕ Add all",
                callback_data=Cbd(action=Act.ADD_ALL).pack(),
            )
        ])
    else:
        inline_keyboard.append([Ikb(text="No habits configured", callback_data=Cbd(action=Act.GO_BACK).pack())])
    inline_keyboard.append([Ikb(text="Go back", callback_data=Cbd(action=Act.GO_BACK).pack())])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

class PlanningReminderActions(CallbackData, prefix="PlanningReminderActions"):
    action: PlanningReminderAction

class PlanningReminderFields(CallbackData, prefix="PlanningReminderFields"):
    action: PlanningReminderField

class PlanningDeleteReminder(CallbackData, prefix="PlanningDeleteReminder"):
    index: int

def planning_reminders_kb(reminders):
    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=f"🗑 {reminder.datetime} {reminder.name}",
                callback_data=PlanningDeleteReminder(index=index).pack(),
            )
        ]
        for index, reminder in enumerate(reminders)
    ]
    inline_keyboard.extend([
        [
            InlineKeyboardButton(
                text="➕ Add reminder",
                callback_data=PlanningReminderActions(
                    action=PlanningReminderAction.ADD_REMINDER
                ).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="Go back",
                callback_data=PlanningReminderActions(
                    action=PlanningReminderAction.GO_BACK
                ).pack(),
            )
        ],
    ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def planning_reminder_fields_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Name",
                callback_data=PlanningReminderFields(
                    action=PlanningReminderField.NAME
                ).pack(),
            ),
            InlineKeyboardButton(
                text="Time",
                callback_data=PlanningReminderFields(
                    action=PlanningReminderField.TIME
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Description",
                callback_data=PlanningReminderFields(
                    action=PlanningReminderField.DESCRIPTION
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Go back",
                callback_data=PlanningReminderFields(
                    action=PlanningReminderField.GO_BACK
                ).pack(),
            ),
            InlineKeyboardButton(
                text="✔️ Save",
                callback_data=PlanningReminderFields(
                    action=PlanningReminderField.SAVE
                ).pack(),
            ),
        ],
    ])
