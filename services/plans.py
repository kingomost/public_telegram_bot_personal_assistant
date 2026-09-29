from __future__ import annotations

from interfaces.meta import (
    MetaHabitModel,
    MetaTaskCheckpointModel,
    MetaTaskModel,
    MetaTaskPeriodModel,
    MetaTimeModel,
)
from interfaces.plan import PlanModel, TaskModel
from memory.memory import Memory
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import config
from utils.datetime import DATE_FORMAT, date_for_date, local_datetime


def meta_time(timestamp: int | float | None = None) -> MetaTimeModel:
    value = local_datetime(timestamp)
    return MetaTimeModel(
        date=value.strftime(DATE_FORMAT),
        time=value.strftime("%H:%M:%S"),
        ttamp_sec=int(value.timestamp()),
    )


class PlanStore:
    """Validated access to one daily plan and its activity log."""

    def __init__(self, plan_file: str | None = None) -> None:
        self.plan_file = plan_file or f"{date_for_date('today')}.json"
        self._memory = Memory(f"calendar/{self.plan_file}", PlanModel)

    @property
    def data(self) -> PlanModel:
        return self._memory.data

    def save(self) -> None:
        self._memory.save()

    def task(self, uuid: str) -> TaskModel | None:
        return next((task for task in self.data.tasks if task.uuid == uuid), None)

    def create_task(self, name: str) -> TaskModel:
        """Create a task with default planning fields in this plan."""
        task = TaskModel(name=name)
        self.data.tasks.append(task)
        self.save()
        return task

    def task_meta(self, uuid: str, *, create: bool = True) -> MetaTaskModel | None:
        found = next((item for item in self.data.meta.tasks if item.uuid == uuid), None)
        if found is not None:
            task = self.task(uuid) if create else None
            if task is not None:
                existing = {item.name for item in found.checklist}
                found.checklist.extend(
                    MetaTaskCheckpointModel(name=name, completed=False)
                    for name in task.checklist
                    if name not in existing
                )
            return found
        if not create:
            return None
        task = self.task(uuid)
        if task is None:
            return None
        found = MetaTaskModel(
            uuid=uuid,
            checklist=[
                MetaTaskCheckpointModel(name=name, completed=False)
                for name in task.checklist
            ],
        )
        self.data.meta.tasks.append(found)
        return found

    def task_has_activity(self, uuid: str) -> bool:
        meta = self.task_meta(uuid, create=False)
        task = self.task(uuid)
        return bool((meta and meta.periods) or (task and task.started_at))

    def start_task(self, uuid: str, timestamp: int) -> TaskModel | None:
        task = self.task(uuid)
        if task is None:
            return None
        self.task_meta(uuid)
        task.started_at = task.started_at or timestamp
        task.completed = False
        self.save()
        return task

    def stop_task(
        self,
        uuid: str,
        started_at: int,
        ended_at: int,
        *,
        completed: bool,
    ) -> TaskModel | None:
        task = self.task(uuid)
        meta = self.task_meta(uuid)
        if task is None or meta is None:
            return None
        start = min(started_at, ended_at)
        meta.periods.append(
            MetaTaskPeriodModel(start=meta_time(start), end=meta_time(ended_at))
        )
        task.finished_at = ended_at
        task.completed = completed
        self.save()
        return task

    def toggle_checkpoint(self, uuid: str, index: int) -> MetaTaskCheckpointModel | None:
        meta = self.task_meta(uuid)
        if meta is None or not 0 <= index < len(meta.checklist):
            return None
        checkpoint = meta.checklist[index]
        checkpoint.completed = not checkpoint.completed
        self.save()
        return checkpoint

    def habit_count(self, uuid: str) -> int:
        item = next((habit for habit in self.data.meta.habits if habit.uuid == uuid), None)
        return item.real_count if item else 0

    def adjust_habit(self, uuid: str, delta: int) -> int | None:
        if not any(habit.uuid == uuid for habit in self.data.habits):
            return None
        item = next((habit for habit in self.data.meta.habits if habit.uuid == uuid), None)
        if item is None:
            item = MetaHabitModel(uuid=uuid, real_count=0)
            self.data.meta.habits.append(item)
        item.real_count = max(0, item.real_count + delta)
        self.save()
        return item.real_count

    def set_real_wakeup(self, timestamp: int | float | None = None) -> MetaTimeModel:
        value = meta_time(timestamp)
        self.data.meta.real_wakeup_time = value
        self.save()
        return value

    def set_real_sleep(self, timestamp: int | float | None = None) -> MetaTimeModel:
        value = meta_time(timestamp)
        self.data.meta.real_sleep_time = value
        self.save()
        return value

    def set_previous_sleep_time(
        self,
        value: str,
        wakeup_timestamp: int | float | None = None,
    ) -> MetaTimeModel:
        hour, minute = (int(part) for part in value.split(":"))
        wakeup = local_datetime(wakeup_timestamp)
        sleep_date = wakeup.date() - timedelta(days=1)
        sleep = datetime(
            sleep_date.year,
            sleep_date.month,
            sleep_date.day,
            hour,
            minute,
            tzinfo=ZoneInfo(config.TIME_ZONE),
        )
        return self.set_real_sleep(sleep.timestamp())
