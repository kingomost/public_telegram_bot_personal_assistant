from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, TypeAlias

from pydantic import BaseModel

from interfaces.meta import MetaModel
from interfaces.plan import PlanModel, TaskModel
from interfaces.state import FullState


MemoryTemplate: TypeAlias = (
    BaseModel
    | Mapping[str, Any]
    | list[Any]
    | Callable[[], BaseModel | Mapping[str, Any] | list[Any]]
)


# Register defaults here for models whose fields do not all define defaults.
MEMORY_TEMPLATES: dict[type[BaseModel], MemoryTemplate] = {
    MetaModel: {},
    PlanModel: {},
    FullState: {},
    TaskModel: {
        "name": "",
    }
}
