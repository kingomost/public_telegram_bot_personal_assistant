from __future__ import annotations

from datetime import date
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class GoalTimeBudget(BaseModel):
    min_hours: float = Field(ge=0)
    max_hours: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> "GoalTimeBudget":
        if self.min_hours > self.max_hours:
            raise ValueError("min_hours cannot exceed max_hours")
        return self


class GoalModel(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    tag: str
    done: bool = False
    expected_results: list[str] = Field(default_factory=list)
    time_budget: GoalTimeBudget | None = None
    duration_days: int | None = Field(default=None, ge=0)
    start_date: str = Field(default_factory=lambda: date.today().isoformat())
    notes: list[str] = Field(default_factory=list)
    subgoals: list[GoalModel] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("goal name cannot be empty")
        return value

    @field_validator("expected_results", "notes", "subgoals", mode="before")
    @classmethod
    def normalize_lists(cls, value):
        return [] if value is None else value

    @field_validator("start_date")
    @classmethod
    def validate_start_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value
