from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import RootModel, ValidationError

import config
from interfaces.goal import GoalModel, GoalTimeBudget
from interfaces.plan import PlanModel
from memory.memory import Memory
from utils.datetime import local_datetime


class GoalsList(RootModel[list[GoalModel]]):
    pass


@dataclass
class GoalStats:
    seconds: int = 0
    task_uuids: set[str] = field(default_factory=set)
    completed_task_uuids: set[str] = field(default_factory=set)
    active_dates: set[str] = field(default_factory=set)

    @property
    def hours(self) -> float:
        return self.seconds / 3600


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized[:24] or "goal"


class GoalsStore:
    PATH = "goals.json"

    def __init__(self) -> None:
        self._memory = Memory(self.PATH, GoalsList, [])

    def list(self) -> list[GoalModel]:
        return list(self._memory.data.root)

    def iter_nodes(self):
        def walk(nodes: list[GoalModel], depth: int, parent: GoalModel | None):
            for node in nodes:
                yield node, depth, parent
                yield from walk(node.subgoals, depth + 1, node)

        yield from walk(self._memory.data.root, 0, None)

    def get(self, uuid: str) -> GoalModel | None:
        return next((node for node, _, _ in self.iter_nodes() if node.uuid == uuid), None)

    def get_by_tag(self, tag: str) -> GoalModel | None:
        return next((node for node, _, _ in self.iter_nodes() if node.tag == tag), None)

    def descendants(self, uuid: str) -> list[GoalModel]:
        node = self.get(uuid)
        if node is None:
            return []
        result: list[GoalModel] = []

        def walk(item: GoalModel) -> None:
            result.append(item)
            for child in item.subgoals:
                walk(child)

        walk(node)
        return result

    def create(self, name: str, parent_uuid: str | None = None) -> GoalModel:
        node = GoalModel(
            name=name,
            tag=f"{config.GOAL_TAG}/{_slug(name)}-{uuid4().hex[:6]}",
            start_date=local_datetime().date().isoformat(),
        )
        if parent_uuid is None:
            self._memory.data.root.append(node)
        else:
            parent = self.get(parent_uuid)
            if parent is None:
                raise KeyError(f"Unknown parent goal: {parent_uuid}")
            parent.subgoals.append(node)
        self._memory.save()
        return node

    def update(
        self,
        uuid: str,
        *,
        expected_result: str | None = None,
        budget: GoalTimeBudget | None = None,
        duration_days: int | None = None,
    ) -> GoalModel:
        node = self.get(uuid)
        if node is None:
            raise KeyError(f"Unknown goal: {uuid}")
        if expected_result:
            node.expected_results.append(expected_result.strip())
        if budget is not None:
            node.time_budget = budget
        if duration_days is not None:
            node.duration_days = duration_days
        self._memory.save()
        return node

    def toggle_done(self, uuid: str) -> GoalModel:
        node = self.get(uuid)
        if node is None:
            raise KeyError(f"Unknown goal: {uuid}")
        node.done = not node.done
        self._memory.save()
        return node

    def delete(self, uuid: str) -> bool:
        for node in list(self._memory.data.root):
            if node.uuid == uuid:
                self._memory.data.root.remove(node)
                self._memory.save()
                return True
        for parent, _, _ in self.iter_nodes():
            for child in list(parent.subgoals):
                if child.uuid == uuid:
                    parent.subgoals.remove(child)
                    self._memory.save()
                    return True
        return False


class GoalAnalytics:
    def __init__(self, store: GoalsStore | None = None) -> None:
        self.store = store or GoalsStore()

    def calculate(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[dict[str, GoalStats], GoalStats]:
        direct = {node.uuid: GoalStats() for node, _, _ in self.store.iter_nodes()}
        unassigned = GoalStats()
        tag_to_node = {node.tag: node for node, _, _ in self.store.iter_nodes()}

        calendar = Memory.DATA_DIR / "calendar"
        if calendar.exists():
            for path in sorted(calendar.glob("*.json")):
                try:
                    plan_day = datetime.strptime(path.stem, "%d_%m_%Y").date()
                except ValueError:
                    continue
                if date_from and plan_day < date_from:
                    continue
                if date_to and plan_day > date_to:
                    continue
                try:
                    plan = Memory(Path("calendar") / path.name, PlanModel).data
                except (OSError, ValueError, ValidationError):
                    continue
                self._collect_plan(plan, path.stem, tag_to_node, direct, unassigned)

        aggregated: dict[str, GoalStats] = {}
        for node, _, _ in self.store.iter_nodes():
            total = GoalStats()
            for descendant in self.store.descendants(node.uuid):
                item = direct[descendant.uuid]
                total.seconds += item.seconds
                total.task_uuids.update(item.task_uuids)
                total.completed_task_uuids.update(item.completed_task_uuids)
                total.active_dates.update(item.active_dates)
            aggregated[node.uuid] = total
        return aggregated, unassigned

    @staticmethod
    def _collect_plan(plan, plan_date, tag_to_node, direct, unassigned) -> None:
        meta_by_uuid = {item.uuid: item for item in plan.meta.tasks}
        for task in plan.tasks:
            if config.GOAL_TAG not in task.tags:
                continue
            node = next((tag_to_node[tag] for tag in task.tags if tag in tag_to_node), None)
            stats = direct[node.uuid] if node else unassigned
            stats.task_uuids.add(task.uuid)
            if task.completed:
                stats.completed_task_uuids.add(task.uuid)
            task_meta = meta_by_uuid.get(task.uuid)
            seconds = 0
            if task_meta:
                seconds = sum(
                    max(0, period.end.ttamp_sec - period.start.ttamp_sec)
                    for period in task_meta.periods
                )
            stats.seconds += seconds
            if seconds:
                stats.active_dates.add(plan_date)

    @staticmethod
    def progress_bar(node: GoalModel, stats: GoalStats, width: int = 10) -> str:
        if not node.time_budget or node.time_budget.min_hours <= 0:
            return "[----------] budget not set"
        ratio = stats.hours / node.time_budget.min_hours
        filled = min(width, max(0, round(ratio * width)))
        return f"[{'#' * filled}{'-' * (width - filled)}] {ratio * 100:.0f}%"

    @staticmethod
    def pace(node: GoalModel, stats: GoalStats) -> str:
        if not node.time_budget or not node.duration_days:
            return "Set budget and days to calculate pace"
        start = date.fromisoformat(node.start_date)
        elapsed = max(1, (local_datetime().date() - start).days + 1)
        remaining_days = max(0, node.duration_days - elapsed)
        remaining_hours = max(0.0, node.time_budget.min_hours - stats.hours)
        required = remaining_hours / remaining_days if remaining_days else remaining_hours
        average = stats.hours / elapsed
        expected_now = node.time_budget.min_hours * min(
            elapsed / node.duration_days, 1
        )
        pace_delta = stats.hours - expected_now
        pace_status = (
            f"{abs(pace_delta):.1f}h ahead"
            if pace_delta >= 0
            else f"{abs(pace_delta):.1f}h behind"
        )
        return (
            f"Pace {average:.1f} h/day ({pace_status}); "
            f"need {required:.1f} h/day; "
            f"{remaining_days} days left"
        )
