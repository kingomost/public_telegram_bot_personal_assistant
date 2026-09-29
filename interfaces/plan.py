from pydantic import BaseModel, Field, field_validator, model_validator
from uuid import uuid4

from interfaces.meta import MetaModel

# class TaskChecklistModel(BaseModel):
#     name: str
#     status: bool | None

class TaskModel(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    recommended_start_time: str | None = None
    recommended_end_time: str | None = None
    expected_duration: str | None = None
    position: str | int | None = None
    tags: list[str] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    completed: bool = False
    started_at: int | None = None
    finished_at: int | None = None

    @field_validator("tags", "checklist", mode="before")
    @classmethod
    def normalize_optional_lists(cls, value):
        return [] if value is None else value

    @field_validator("uuid", mode="before")
    @classmethod
    def ensure_uuid(cls, value):
        return str(uuid4()) if value is None or not str(value).strip() else value

    @field_validator("position", mode="before")
    @classmethod
    def normalize_position(cls, value):
        if value is None or value == "middle":
            return value
        if isinstance(value, bool):
            raise ValueError("position must be an integer, 'middle', or None")
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                raise ValueError(
                    "position must be an integer, 'middle', or None"
                ) from None
        if value == 0:
            raise ValueError("position cannot be zero")
        return value

class ReminderModel(BaseModel):
    datetime: str
    name: str
    description: str | None = None

    @field_validator("datetime")
    @classmethod
    def validate_time(cls, value: str) -> str:
        try:
            hour, minute = (int(part) for part in value.split(":"))
        except (TypeError, ValueError):
            raise ValueError("datetime must use HH:MM format") from None
        if hour not in range(24) or minute not in range(60):
            raise ValueError("datetime must use HH:MM format")
        return f"{hour:02d}:{minute:02d}"

class HabitAllowedCriteria(BaseModel):
    min: int = Field(ge=0)
    max: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> "HabitAllowedCriteria":
        if self.min > self.max:
            raise ValueError("min cannot be greater than max")
        return self

class HabitModel(BaseModel):
    uuid: str
    name: str
    allowed: HabitAllowedCriteria | None = None

class PlanModel(BaseModel):
    wakeup_time: str | None = None
    sleep_time: str | None = None
    tasks: list[TaskModel] = Field(default_factory=list)
    reminders: list[ReminderModel] = Field(default_factory=list)
    habits: list[HabitModel] = Field(default_factory=list)
    meta: MetaModel = Field(default_factory=MetaModel)

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_rituals(cls, value):
        if not isinstance(value, dict):
            return value
        data = dict(value)
        rituals = data.pop("rituals", None) or []
        if rituals:
            data["tasks"] = [*(data.get("tasks") or []), *rituals]
        return data

    @field_validator("tasks", "reminders", "habits", mode="before")
    @classmethod
    def normalize_collections(cls, value):
        return [] if value is None else value

    @model_validator(mode="after")
    def sort_tasks(self) -> "PlanModel":
        """Keep positioned tasks at the requested part of the day."""
        positive = sorted(
            (task for task in self.tasks if isinstance(task.position, int) and task.position > 0),
            key=lambda task: task.position,
        )
        negative = sorted(
            (task for task in self.tasks if isinstance(task.position, int) and task.position < 0),
            key=lambda task: task.position,
        )
        middle = [task for task in self.tasks if task.position == "middle"]
        unpositioned = [task for task in self.tasks if task.position is None]
        split = len(unpositioned) // 2 if middle else len(unpositioned)
        object.__setattr__(self, "tasks", [
            *positive,
            *unpositioned[:split],
            *middle,
            *unpositioned[split:],
            *negative,
        ])
        return self
