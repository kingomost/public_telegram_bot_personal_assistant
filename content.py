from typing import Any

from interfaces.plan import PlanModel, TaskModel
from interfaces.document import DocumentType
from interfaces.state import FullState
from memory.documents import Documents
from memory.memory import Memory
from services.habits import HabitsStore
from services.rituals import RitualsStore
from services.plans import PlanStore
from services.goals import GoalAnalytics, GoalsStore

def planning_select_date_ct() -> str:
    return "\n".join((
        "Date:",
        " ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀",
    ))

def plan_ct(file: str) -> str:
    plan = Memory(path = f"./calendar/{file}", model = PlanModel)
    return "\n".join((
        f"Wake up: {plan.data.wakeup_time or 'not set'}",
        f"Sleep: {plan.data.sleep_time or 'not set'}",
        f"Tasks: {len(plan.data.tasks)}",
        f"Habits: {len(plan.data.habits)}",
        f"Reminders: {len(plan.data.reminders)}",
        " ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀",
    ))

def plan_tasks_ct(file: str) -> str:
    plan = Memory(path = f"./calendar/{file}", model = PlanModel)
    lines = ["Tasks:"]
    for index, task in enumerate(plan.data.tasks, 1):
        status = "✓" if task.completed else "•"
        details = f" ({task.expected_duration})" if task.expected_duration else ""
        lines.append(f"{index}. {status} {task.name}{details}")
    if not plan.data.tasks:
        lines.append("No tasks planned.")
    lines.append(
        " ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀",
    )
    return "\n".join(lines)

def task_ct() -> str:
    full_state = Memory(path = "./state.json", model = FullState)
    task = full_state.data.tmp["task"]
    item_name = (
        "Ritual" if full_state.data.tmp.get("task_context") == "ritual" else "Task"
    )
    lines = [
        f"{item_name}: {task.get('name', 'unnamed')}",
        f"Duration: {task.get('expected_duration') or 'not set'}",
        f"Position: {task.get('position') if task.get('position') is not None else 'not set'}",
        f"Tags: {', '.join(task.get('tags', [])) or 'none'}",
        "Checklist:",
    ]
    checklist = task.get("checklist", [])
    lines.extend(f"• {item}" for item in checklist)
    if not checklist:
        lines.append("none")
    lines.append(
        " ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀",
    )
    return "\n".join(lines)

def plan_habits_ct(file: str) -> str:
    plan = Memory(path = f"./calendar/{file}", model = PlanModel)
    global_habits = HabitsStore().list()
    selected = {habit.uuid for habit in plan.data.habits}
    lines = ["All Habits:"]
    for idx, h in enumerate(global_habits, 1):
        allowed_str = f" [{h.allowed.min}-{h.allowed.max}]" if h.allowed else ""
        marker = "selected" if h.uuid in selected else "not selected"
        lines.append(f"{idx}. {h.name}{allowed_str} - {marker}")
    if not global_habits:
        lines.append("No habits configured.")
    lines.extend(("", "Selected Habits:"))
    selected_habits = [habit for habit in global_habits if habit.uuid in selected]
    for idx, h in enumerate(selected_habits, 1):
        allowed_str = f" [{h.allowed.min}-{h.allowed.max}]" if h.allowed else ""
        lines.append(f"{idx}. {h.name}{allowed_str}")
    if not selected_habits:
        lines.append("none")
    lines.append(" ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀")
    return "\n".join(lines)

def habits_ct(status: str | None = None) -> str:
    """Render the global habits management content."""
    habits = HabitsStore().list()
    lines = []
    if status:
        lines.extend((status, ""))
    lines.extend(("Global Habits:", ""))
    for index, habit in enumerate(habits, 1):
        allowed = (
            f" [{habit.allowed.min}-{habit.allowed.max}]"
            if habit.allowed
            else ""
        )
        lines.append(f"{index}. {habit.name}{allowed}")
    if not habits:
        lines.append("No habits configured.")
    lines.append(" ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀")
    return "\n".join(lines)

def rituals_ct(status: str | None = None) -> str:
    """Render global rituals with all task-template fields."""
    rituals = RitualsStore().list()
    lines = []
    if status:
        lines.extend((status, ""))
    lines.extend(("Global Rituals:", ""))
    for index, ritual in enumerate(rituals, 1):
        lines.extend((
            f"{index}. {ritual.name}",
            f"   Duration: {ritual.expected_duration or 'not set'}",
            f"   Position: {ritual.position if ritual.position is not None else 'not set'}",
            f"   Tags: {', '.join(ritual.tags) or 'none'}",
            "   Checklist: " + (
                "; ".join(ritual.checklist) if ritual.checklist else "none"
            ),
        ))
    if not rituals:
        lines.append("No rituals configured.")
    lines.append(" ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀")
    return "\n".join(lines)

def backlog_ct(status: str | None = None) -> str:
    """Render backlog tasks with their planning fields."""
    documents = Documents()
    tasks = [
        documents.read(document.uuid)
        for document in documents.get_list(type=DocumentType.TASK_MODEL)
    ]
    lines = []
    if status:
        lines.extend((status, ""))
    lines.extend(("Backlog Tasks:", ""))
    for index, task in enumerate(tasks, 1):
        lines.extend((
            f"{index}. {task.name}",
            f"   Recommended start: {task.recommended_start_time or 'not set'}",
            f"   Recommended end: {task.recommended_end_time or 'not set'}",
            f"   Duration: {task.expected_duration or 'not set'}",
            f"   Position: {task.position if task.position is not None else 'not set'}",
            f"   Tags: {', '.join(task.tags) or 'none'}",
            "   Checklist: " + (
                "; ".join(task.checklist) if task.checklist else "none"
            ),
        ))
    if not tasks:
        lines.append("No tasks in backlog.")
    lines.append(" ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀")
    return "\n".join(lines)

def reminder_draft_ct() -> str:
    """Render the reminder currently being edited."""
    state = Memory(path="./state.json", model=FullState)
    reminder = state.data.tmp.get("reminder_draft", {})
    return "\n".join((
        f"Reminder: {reminder.get('name') or 'not set'}",
        f"Time: {reminder.get('datetime') or 'not set'}",
        f"Description: {reminder.get('description') or 'none'}",
        " ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀",
    ))


def habit_tracker_ct(selected_uuid: str | None = None) -> str:
    """Render today's planned habits and their actual counts."""
    plan = PlanStore()
    lines = ["Today's Habit Tracker:", ""]
    for habit in plan.data.habits:
        count = plan.habit_count(habit.uuid)
        target = (
            f"{habit.allowed.min}-{habit.allowed.max}"
            if habit.allowed
            else "not set"
        )
        marker = "→ " if habit.uuid == selected_uuid else ""
        lines.append(f"{marker}{habit.name}: {count} (target {target})")
    if not plan.data.habits:
        lines.append("No habits are active in today's plan.")
    lines.append(" ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀")
    return "\n".join(lines)


def goals_ct(status: str | None = None) -> str:
    store = GoalsStore()
    stats, unassigned = GoalAnalytics(store).calculate()
    lines = []
    if status:
        lines.extend((status, ""))
    lines.extend(("Goals:", ""))
    for node, depth, _ in store.iter_nodes():
        item = stats[node.uuid]
        budget = (
            f"/{node.time_budget.min_hours:g}-{node.time_budget.max_hours:g}h"
            if node.time_budget
            else ""
        )
        lines.append(
            f"{'  ' * depth}{'✓' if node.done else '•'} {node.name} "
            f"[{item.hours:.1f}h{budget}, {len(item.active_dates)} active days]"
        )
    if not store.list():
        lines.append("No goals configured.")
    if unassigned.task_uuids:
        lines.append(
            f"\nUnassigned #goal work: {unassigned.hours:.1f}h, "
            f"{len(unassigned.task_uuids)} tasks"
        )
    lines.append(" ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀")
    return "\n".join(lines)


def goal_detail_ct(uuid: str, status: str | None = None) -> str:
    store = GoalsStore()
    node = store.get(uuid)
    if node is None:
        return goals_ct("Goal no longer exists.")
    stats = GoalAnalytics(store).calculate()[0][uuid]
    lines = []
    if status:
        lines.extend((status, ""))
    lines.extend((
        f"{'✓' if node.done else '🎯'} {node.name}",
        f"Tag: {node.tag}",
        f"Started: {node.start_date}",
        f"Time spent: {stats.hours:.1f} hours",
        f"Tasks: {len(stats.completed_task_uuids)}/{len(stats.task_uuids)} completed",
        f"Active days: {len(stats.active_dates)}",
    ))
    if node.time_budget:
        lines.append(
            f"Budget: {node.time_budget.min_hours:g}-{node.time_budget.max_hours:g} hours"
        )
        lines.append(GoalAnalytics.progress_bar(node, stats))
    else:
        lines.append("Budget: not set")
    duration = node.duration_days if node.duration_days is not None else "not set"
    lines.append(f"Duration: {duration} days")
    lines.append(GoalAnalytics.pace(node, stats))
    lines.append("Expected results:")
    lines.extend(f"• {result}" for result in node.expected_results)
    if not node.expected_results:
        lines.append("none")
    lines.append(f"Subgoals: {len(node.subgoals)}")
    lines.append(" ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀ ⠀")
    return "\n".join(lines)
