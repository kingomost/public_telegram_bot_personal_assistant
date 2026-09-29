from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from time import time
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, JsonValue, RootModel, TypeAdapter, ValidationError
from pydantic_core import PydanticSerializationError, to_jsonable_python

from interfaces.document import Document, DocumentType
from interfaces.meta import MetaModel
from interfaces.plan import PlanModel, ReminderModel, TaskModel
from memory.memory import Memory


class DocumentIndex(RootModel[list[Document]]):
    pass


class JsonDocument(RootModel[JsonValue]):
    pass


_UNSET = object()


class Documents:
    """Manage typed and untyped JSON documents stored below ``data/documents``."""

    DIRECTORY = Path("documents")
    INDEX_PATH = DIRECTORY / "index.json"
    REGISTERED_TYPES: dict[DocumentType, type[BaseModel]] = {
        DocumentType.META_MODEL: MetaModel,
        DocumentType.TASK_MODEL: TaskModel,
        DocumentType.REMINDER_MODEL: ReminderModel,
        # Kept only so RitualsStore can migrate legacy document files.
        DocumentType.RITUAL_MODEL: TaskModel,
        DocumentType.PLAN_MODEL: PlanModel,
    }

    def __init__(self) -> None:
        try:
            self._index = Memory(self.INDEX_PATH, DocumentIndex, [])
        except (OSError, ValidationError, json.JSONDecodeError):
            self._index = Memory.store(self.INDEX_PATH, DocumentIndex, [])
        self.update_documents()

    @property
    def data_directory(self) -> Path:
        return self._index.file_path.parent

    def update_documents(self) -> list[Document]:
        """Rebuild the index from disk while retaining user-managed metadata."""
        previous = {document.uuid: document for document in self._index.data.root}
        documents: list[Document] = []

        for file_path in sorted(self.data_directory.glob("*.json")):
            if file_path == self._index.file_path:
                continue

            existing = previous.get(file_path.stem)
            stat = file_path.stat()
            is_valid_json, document_type = self._inspect_file(
                file_path, existing.type if existing else None
            )
            documents.append(
                Document(
                    created=(
                        existing.created if existing else int(stat.st_ctime)
                    ),
                    updated=int(stat.st_mtime),
                    uuid=file_path.stem,
                    file=file_path.name,
                    is_valid_json=is_valid_json,
                    type=document_type,
                    brief=existing.brief if existing else None,
                    tags=existing.tags if existing else None,
                )
            )

        self._index.replace(documents)
        self._index.save()
        return list(self._index.data.root)

    def get_list(
        self,
        *,
        sort_by: Literal["created", "updated"] | None = None,
        order: Literal["asc", "desc"] = "asc",
        type: DocumentType | None | object = _UNSET,
        offset: int = 0,
        step: int | None = None,
    ) -> list[Document]:
        """Return filtered, sorted, and paginated document metadata."""
        if offset < 0:
            raise ValueError("offset cannot be negative")
        if step is not None and step < 0:
            raise ValueError("step cannot be negative")

        result = list(self._index.data.root)
        if type is not _UNSET:
            requested_type = TypeAdapter(DocumentType | None).validate_python(type)
            result = [item for item in result if item.type == requested_type]
        if sort_by is not None:
            result.sort(
                key=lambda item: getattr(item, sort_by),
                reverse=order == "desc",
            )

        end = None if step is None else offset + step
        return result[offset:end]

    def create(
        self,
        value: Any,
        *,
        type_hint: DocumentType | None = None,
        brief: str | None = None,
        tags: list[str] | None = None,
    ) -> Document:
        document_type = type_hint or self._type_for_instance(value)
        document_uuid = str(uuid4())
        relative_path = self.DIRECTORY / f"{document_uuid}.json"
        timestamp = int(time())
        document = Document(
            created=timestamp,
            updated=timestamp,
            uuid=document_uuid,
            file=relative_path.name,
            is_valid_json=True,
            type=document_type,
            brief=brief,
            tags=tags,
        )
        self._write_document(relative_path, value, document_type)
        self._index.data.root.append(document)
        self._index.save()
        return document

    def read(self, uuid: str) -> BaseModel | JsonValue:
        document = self._get(uuid)
        if not document.is_valid_json:
            raise ValueError(f"Document {uuid} does not contain valid JSON")

        relative_path = self.DIRECTORY / document.file
        if document.type is None:
            return Memory(relative_path, JsonDocument).data.root
        model = self.REGISTERED_TYPES[document.type]
        return Memory(relative_path, model).data

    def update(
        self,
        uuid: str,
        value: Any = _UNSET,
        *,
        type_hint: DocumentType | None = None,
        brief: str | None | object = _UNSET,
        tags: list[str] | None | object = _UNSET,
    ) -> Document:
        document = self._get(uuid)
        candidate_data = document.model_dump(mode="python")
        if value is not _UNSET:
            candidate_data["type"] = type_hint or self._type_for_instance(value)
            candidate_data["is_valid_json"] = True
        if brief is not _UNSET:
            candidate_data["brief"] = brief
        if tags is not _UNSET:
            candidate_data["tags"] = tags
        candidate_data["updated"] = int(time())
        candidate = Document.model_validate(candidate_data)

        if value is not _UNSET:
            self._write_document(
                self.DIRECTORY / document.file,
                value,
                candidate.type,
            )
        index = self._index.data.root.index(document)
        self._index.data.root[index] = candidate
        self._index.save()
        return candidate

    def delete(self, uuid: str) -> Document:
        document = self._get(uuid)
        Memory.remove(self.DIRECTORY / document.file)
        self._index.data.root.remove(document)
        self._index.save()
        return document

    def _get(self, uuid: str) -> Document:
        for document in self._index.data.root:
            if document.uuid == uuid:
                return document
        raise KeyError(f"Unknown document UUID: {uuid}")

    def _inspect_file(
        self,
        file_path: Path,
        preferred_type: DocumentType | None = None,
    ) -> tuple[bool, DocumentType | None]:
        relative_path = self.DIRECTORY / file_path.name
        try:
            value = Memory(relative_path, JsonDocument).data.root
        except (ValueError, json.JSONDecodeError):
            return False, None

        candidates = list(self.REGISTERED_TYPES.items())
        if preferred_type is not None:
            candidates.sort(key=lambda item: item[0] != preferred_type)
        for document_type, model in candidates:
            try:
                model.model_validate(value)
            except ValueError:
                continue
            return True, document_type
        return True, None

    def _write_document(
        self,
        path: Path,
        value: Any,
        document_type: DocumentType | None,
    ) -> None:
        if document_type is not None:
            model = self.REGISTERED_TYPES[document_type]
            validated = model.model_validate(value)
            Memory.store(path, model, validated)
        else:
            validated_json = self._to_json_value(value)
            Memory.store(path, JsonDocument, validated_json)

    @classmethod
    def _type_for_instance(cls, value: Any) -> DocumentType | None:
        for document_type, model in cls.REGISTERED_TYPES.items():
            if isinstance(value, model):
                return document_type
        return None

    @staticmethod
    def _to_json_value(value: Any) -> JsonValue:
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json")
        elif isinstance(value, Mapping):
            value = dict(value)
        else:
            try:
                value = to_jsonable_python(value)
            except (PydanticSerializationError, TypeError, ValueError):
                if not hasattr(value, "__dict__"):
                    raise TypeError("Document value is not JSON serializable")
                value = to_jsonable_python(vars(value))
        return TypeAdapter(JsonValue).validate_python(value)
