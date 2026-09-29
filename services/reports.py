from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from pydantic import ValidationError

import config
from interfaces.plan import PlanModel
from memory.memory import Memory
from services.goals import GoalAnalytics, GoalsStore


@dataclass
class DaySummary:
    day: date
    tasks: int = 0
    completed_tasks: int = 0
    tracked_seconds: int = 0
    goal_seconds: int = 0
    habit_count: int = 0


def _plan_for(day: date) -> PlanModel | None:
    path = Path("calendar") / f"{day.strftime('%d_%m_%Y')}.json"
    if not (Memory.DATA_DIR / path).exists():
        return None
    try:
        return Memory(path, PlanModel).data
    except (OSError, ValueError, ValidationError):
        return None


def day_summary(day: date) -> DaySummary:
    summary = DaySummary(day=day)
    plan = _plan_for(day)
    if plan is None:
        return summary
    summary.tasks = len(plan.tasks)
    summary.completed_tasks = sum(task.completed for task in plan.tasks)
    task_by_uuid = {task.uuid: task for task in plan.tasks}
    for meta in plan.meta.tasks:
        seconds = sum(
            max(0, period.end.ttamp_sec - period.start.ttamp_sec)
            for period in meta.periods
        )
        summary.tracked_seconds += seconds
        task = task_by_uuid.get(meta.uuid)
        if task and config.GOAL_TAG in task.tags:
            summary.goal_seconds += seconds
    summary.habit_count = sum(item.real_count for item in plan.meta.habits)
    return summary


def range_summaries(start: date, end: date) -> list[DaySummary]:
    return [
        day_summary(start + timedelta(days=offset))
        for offset in range((end - start).days + 1)
    ]


def render_range_report(title: str, start: date, end: date) -> str:
    summaries = range_summaries(start, end)
    tracked = sum(item.tracked_seconds for item in summaries) / 3600
    goal = sum(item.goal_seconds for item in summaries) / 3600
    completed = sum(item.completed_tasks for item in summaries)
    tasks = sum(item.tasks for item in summaries)
    active_days = sum(item.tracked_seconds > 0 for item in summaries)
    lines = [
        title,
        f"{start.isoformat()} to {end.isoformat()}",
        "",
        f"Tasks completed: {completed}/{tasks}",
        f"Tracked work: {tracked:.1f} hours",
        f"Goal work: {goal:.1f} hours",
        f"Active days: {active_days}/{len(summaries)}",
        f"Habit actions: {sum(item.habit_count for item in summaries)}",
        "",
        "Daily:",
    ]
    for item in summaries:
        lines.append(
            f"{item.day.strftime('%d.%m')}: "
            f"{item.completed_tasks}/{item.tasks} tasks, "
            f"{item.tracked_seconds / 3600:.1f}h total, "
            f"{item.goal_seconds / 3600:.1f}h goal"
        )
    return "\n".join(lines)


def render_goal_report() -> str:
    store = GoalsStore()
    stats, unassigned = GoalAnalytics(store).calculate()
    lines = ["Goal Progress Report", ""]
    for node, depth, _ in store.iter_nodes():
        item = stats[node.uuid]
        budget = (
            f" / {node.time_budget.min_hours:g}-{node.time_budget.max_hours:g}h"
            if node.time_budget
            else ""
        )
        lines.extend((
            f"{'  ' * depth}{'✓' if node.done else '•'} {node.name}",
            f"{'  ' * depth}  {item.hours:.1f}h{budget}; "
            f"{len(item.completed_task_uuids)}/{len(item.task_uuids)} tasks; "
            f"{len(item.active_dates)} days",
        ))
        if depth == 0:
            lines.append(f"  {GoalAnalytics.progress_bar(node, item)}")
            lines.append(f"  {GoalAnalytics.pace(node, item)}")
    if not store.list():
        lines.append("No goals configured.")
    if unassigned.task_uuids:
        lines.append(
            f"\nUnassigned #goal: {unassigned.hours:.1f}h across "
            f"{len(unassigned.task_uuids)} tasks"
        )
    return "\n".join(lines)
