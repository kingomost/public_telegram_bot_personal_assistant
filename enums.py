from enum import StrEnum
from typing import Any

class PlanningEditAction(StrEnum):
    WAKEUP_TIME = "WakeupTime"
    SLEEP_TIME = "SleepTime"
    TASKS = "Tasks"
    HABITS = "Habits"
    REMINDERS = "Reminders"
    GO_BACK = "GoBack"

class PlanningTasksAction(StrEnum):
    ADD_RITUAL = "AddRitual"
    ADD_TASK = "AddTask"
    ADD_FROM_BACKLOG = "AddFromBacklog"
    DELETE_TASK = "DeleteTask"
    GO_BACK = "GoBack"

class PlanningTaskField(StrEnum):
    NAME = "Name"
    CHECKPOINTS = "Checkpoints"
    TAGS = "Tags"
    POSITION = "Position"
    DURATION = "Duration"
    GO_BACK = "GoBack"
    ADD_TASK = "AddTask"

class OptionAction(StrEnum):
    GO_BACK = "GoBack"
    NONE = "None"

class BacklogAction(StrEnum):
    ADD_TASK = "AddTask"
    LIST_TASKS = "ListTasks"
    DELETE_TASK = "DeleteTask"
    GO_BACK = "GoBack"

class BacklogTaskAction(StrEnum):
    DELETE_TASK = "DeleteTask"
    EDIT_TASK = "EditTask"
    GO_BACK = "GoBack"

class HabitAction(StrEnum):
    ADD_HABIT = "AddHabit"
    LIST_HABITS = "ListHabits"
    DELETE_HABIT = "DeleteHabit"
    GO_BACK = "GoBack"

class RitualAction(StrEnum):
    ADD_RITUAL = "AddRitual"
    LIST_RITUALS = "ListRituals"
    DELETE_RITUAL = "DeleteRitual"
    GO_BACK = "GoBack"

class ExecutionAction(StrEnum):
    START_TASK = "StartTask"
    QUICK_CREATE = "QuickCreate"
    FINISH_TASK = "FinishTask"
    PAUSE_TASK = "PauseTask"
    ADD_TIME = "AddTime"
    GO_BACK = "GoBack"

class ExecutionCheckpointAction(StrEnum):
    DONE = "Done"

class HabitTrackerAction(StrEnum):
    GO_BACK = "GoBack"

class DayAction(StrEnum):
    WAKEUP = "Wakeup"
    SLEEP = "Sleep"

class AlarmAction(StrEnum):
    WOKE_UP = "WokeUp"

class GoalAction(StrEnum):
    ADD = "A"

class GoalNodeAction(StrEnum):
    ADD_SUBGOAL = "AS"
    EXPECTED_RESULT = "ER"
    BUDGET = "BU"
    DAYS = "DY"
    TOGGLE_DONE = "DN"
    DELETE = "DL"
    GO_BACK = "BK"

class ReportAction(StrEnum):
    TODAY = "T"
    YESTERDAY = "Y"
    LAST_7_DAYS = "7"
    THIS_WEEK = "W"
    GOALS = "G"

class PlanningHabitAction(StrEnum):
    TOGGLE_HABIT = "ToggleHabit"
    ADD_ALL = "AddAll"
    GO_BACK = "GoBack"

class PlanningReminderAction(StrEnum):
    ADD_REMINDER = "AddReminder"
    GO_BACK = "GoBack"

class PlanningReminderField(StrEnum):
    NAME = "Name"
    TIME = "Time"
    DESCRIPTION = "Description"
    SAVE = "Save"
    GO_BACK = "GoBack"
