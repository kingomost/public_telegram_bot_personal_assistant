from pydantic import BaseModel
from enum import StrEnum

class DocumentType(StrEnum):
    META_MODEL = "MetaModel"
    TASK_MODEL = "TaskModel"
    REMINDER_MODEL = "ReminderModel"
    RITUAL_MODEL = "RitualModel"
    PLAN_MODEL = "PlanModel"

class Document(BaseModel):
    created: int
    updated: int
    uuid: str
    file: str
    is_valid_json: bool
    type: DocumentType | None
    brief: str | None
    tags: list[str] | None
    