from __future__ import annotations

from uuid import uuid4

from pydantic import RootModel

from interfaces.document import DocumentType
from interfaces.plan import TaskModel
from memory.documents import Documents
from memory.memory import Memory


class RitualsList(RootModel[list[TaskModel]]):
    pass


class RitualsStore:
    """CRUD for task-shaped rituals stored in ``.data/rituals.json``."""

    PATH = "rituals.json"

    def __init__(self) -> None:
        self._memory = Memory(self.PATH, RitualsList, [])
        self._migrate_legacy_documents()

    @property
    def _rituals(self) -> list[TaskModel]:
        return self._memory.data.root

    def list(self) -> list[TaskModel]:
        return list(self._rituals)

    def get(self, uuid: str) -> TaskModel | None:
        return next(
            (ritual for ritual in self._rituals if ritual.uuid == uuid),
            None,
        )

    def create(self, value: TaskModel | dict) -> TaskModel:
        ritual = self._normalize_template(TaskModel.model_validate(value))
        if self.get(ritual.uuid) is not None:
            raise ValueError(f"Ritual UUID already exists: {ritual.uuid}")
        self._rituals.append(ritual)
        self._memory.save()
        return ritual

    def delete(self, uuid: str) -> bool:
        ritual = self.get(uuid)
        if ritual is None:
            return False
        self._rituals.remove(ritual)
        self._memory.save()
        return True

    def as_plan_task(self, uuid: str) -> TaskModel | None:
        """Return a fresh executable task copied from a ritual template."""
        ritual = self.get(uuid)
        if ritual is None:
            return None
        return TaskModel.model_validate(
            ritual.model_dump(mode="python") | {
                "uuid": str(uuid4()),
                "completed": False,
                "started_at": None,
                "finished_at": None,
            }
        )

    @staticmethod
    def _normalize_template(ritual: TaskModel) -> TaskModel:
        return TaskModel.model_validate(
            ritual.model_dump(mode="python") | {
                "completed": False,
                "started_at": None,
                "finished_at": None,
            }
        )

    def _migrate_legacy_documents(self) -> None:
        documents = Documents()
        legacy = documents.get_list(type=DocumentType.RITUAL_MODEL)
        if not legacy:
            return

        existing = {ritual.uuid for ritual in self._rituals}
        changed = False
        migrated_documents: list[str] = []
        for document in legacy:
            ritual = self._normalize_template(
                TaskModel.model_validate(documents.read(document.uuid))
            )
            if ritual.uuid not in existing:
                self._rituals.append(ritual)
                existing.add(ritual.uuid)
                changed = True
            migrated_documents.append(document.uuid)
        if changed:
            self._memory.save()
        for document_uuid in migrated_documents:
            documents.delete(document_uuid)
