from __future__ import annotations

from uuid import uuid4

from pydantic import RootModel

from interfaces.plan import HabitAllowedCriteria, HabitModel
from memory.memory import Memory


class HabitsList(RootModel[list[HabitModel]]):
    pass


class HabitsStore:
    """Centralized CRUD for habits stored in ``.data/habits.json``."""

    PATH = "habits.json"

    def __init__(self) -> None:
        self._memory = Memory(self.PATH, HabitsList, [])

    @property
    def _habits(self) -> list[HabitModel]:
        return self._memory.data.root

    def list(self) -> list[HabitModel]:
        """Return all habits."""
        return list(self._habits)

    def get(self, uuid: str) -> HabitModel | None:
        """Return a single habit by UUID, or ``None``."""
        for habit in self._habits:
            if habit.uuid == uuid:
                return habit
        return None

    def create(
        self,
        name: str,
        minimum: int,
        maximum: int,
    ) -> HabitModel:
        """Create a new habit and persist it."""
        allowed = HabitAllowedCriteria(min=minimum, max=maximum)
        habit = HabitModel(uuid=str(uuid4()), name=name, allowed=allowed)
        self._habits.append(habit)
        self._memory.save()
        return habit

    def delete(self, uuid: str) -> bool:
        """Delete a habit by UUID. Returns ``True`` if found and removed."""
        habit = self.get(uuid)
        if habit is None:
            return False
        self._habits.remove(habit)
        self._memory.save()
        return True

    def save(self) -> None:
        """Explicitly persist the current state."""
        self._memory.save()
