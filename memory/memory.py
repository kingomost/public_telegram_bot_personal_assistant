from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from functools import wraps
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Generic, ParamSpec, TypeVar, cast

from pydantic import BaseModel, ConfigDict

from memory.templates import MEMORY_TEMPLATES, MemoryTemplate


ModelT = TypeVar("ModelT", bound=BaseModel)
P = ParamSpec("P")
R = TypeVar("R")


def validate_data_change(
    method: Callable[P, R],
) -> Callable[P, R]:
    """Revalidate a memory model after a method changes it."""

    @wraps(method)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        result = method(*args, **kwargs)
        memory = args[0]
        if not isinstance(memory, Memory):
            raise TypeError("validate_data_change can only decorate Memory methods")
        memory.data = memory._model_type.model_validate(
            memory.data.model_dump(mode="python")
        )
        return result

    return wrapper


class Memory(Generic[ModelT]):
    """JSON-backed storage for a Pydantic model."""

    DATA_DIR = Path(__file__).resolve().parent.parent / ".data"

    def __init__(
        self,
        path: str | Path,
        model: type[ModelT],
        template: MemoryTemplate | None = None,
    ) -> None:
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.file_path = self._resolve_path(path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.model = model
        self._model_type = self._assignment_validated_model(model)

        if self.file_path.exists():
            self.data = self._load()
        else:
            self.data = self._create_default(template)
            self.save()

    @classmethod
    def _resolve_path(cls, path: str | Path) -> Path:
        relative_path = Path(path)
        if relative_path.is_absolute():
            raise ValueError("Memory paths must be relative to the data directory")

        data_dir = cls.DATA_DIR.resolve()
        file_path = (data_dir / relative_path).resolve()
        if not file_path.is_relative_to(data_dir):
            raise ValueError("Memory paths cannot leave the data directory")
        return file_path

    @classmethod
    def store(
        cls,
        path: str | Path,
        model: type[ModelT],
        value: ModelT | Mapping[str, Any] | Any,
    ) -> Memory[ModelT]:
        """Validate and persist a value without loading an existing file."""
        memory = cls.__new__(cls)
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        memory.file_path = cls._resolve_path(path)
        memory.file_path.parent.mkdir(parents=True, exist_ok=True)
        memory.model = model
        memory._model_type = cls._assignment_validated_model(model)
        memory.replace(value)
        memory.save()
        return memory

    @classmethod
    def remove(cls, path: str | Path, *, missing_ok: bool = False) -> None:
        """Delete a backing file without loading or validating its contents."""
        cls._resolve_path(path).unlink(missing_ok=missing_ok)

    @staticmethod
    def _assignment_validated_model(model: type[ModelT]) -> type[ModelT]:
        config = ConfigDict(**{**model.model_config, "validate_assignment": True})
        return cast(
            type[ModelT],
            type(
                f"Validated{model.__name__}",
                (model,),
                {"model_config": config, "__module__": model.__module__},
            ),
        )

    def _load(self) -> ModelT:
        return self._model_type.model_validate_json(
            self.file_path.read_text(encoding="utf-8")
        )

    def _create_default(self, template: MemoryTemplate | None) -> ModelT:
        selected_template = template
        if selected_template is None:
            selected_template = MEMORY_TEMPLATES.get(self.model)

        if callable(selected_template):
            selected_template = selected_template()
        if selected_template is None:
            selected_template = {}
        if isinstance(selected_template, BaseModel):
            selected_template = selected_template.model_dump(mode="python")

        return self._model_type.model_validate(selected_template)

    @validate_data_change
    def set(self, key: str, value: Any) -> None:
        """Set one field, validating both its name and value."""
        if key not in self.model.model_fields:
            raise ValueError(f"Unknown field for {self.model.__name__}: {key}")
        setattr(self.data, key, value)

    @validate_data_change
    def update(self, values: Mapping[str, Any] | None = None, **kwargs: Any) -> None:
        """Validate and apply several fields as one transaction."""
        changes = dict(values or {})
        changes.update(kwargs)
        unknown = changes.keys() - self.model.model_fields.keys()
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"Unknown fields for {self.model.__name__}: {names}")

        candidate = self.data.model_dump(mode="python")
        candidate.update(changes)
        self.data = self._model_type.model_validate(candidate)

    def replace(self, value: ModelT | Mapping[str, Any] | Any) -> None:
        """Replace the complete stored value after model validation."""
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="python")
        self.data = self._model_type.model_validate(value)

    def save(self) -> None:
        """Validate and atomically persist the current data."""
        self.data = self._model_type.model_validate(
            self.data.model_dump(mode="python")
        )
        payload = self.data.model_dump(mode="json")

        temporary_path: str | None = None
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.file_path.parent,
                prefix=f".{self.file_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                json.dump(payload, temporary_file, indent=2, ensure_ascii=False)
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
                temporary_path = temporary_file.name
            os.replace(temporary_path, self.file_path)
        finally:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)

    def delete(self, *, missing_ok: bool = False) -> None:
        """Delete the backing file."""
        self.file_path.unlink(missing_ok=missing_ok)
