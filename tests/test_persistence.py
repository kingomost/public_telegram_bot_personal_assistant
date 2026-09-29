import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from interfaces.document import DocumentType
from interfaces.plan import TaskModel
from interfaces.state import FullState, UserStateEnum
from memory.documents import Documents
from memory.memory import Memory
from menu import MainMenu, get_main_menu
from services.habits import HabitsStore
from services.rituals import RitualsStore
from utils.state import is_silent_mode, update_state


class PersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.original_data_dir = Memory.DATA_DIR
        Memory.DATA_DIR = Path(self.directory.name) / ".data"

    def tearDown(self) -> None:
        Memory.DATA_DIR = self.original_data_dir
        self.directory.cleanup()

    def test_state_can_be_merged_and_explicitly_cleared(self) -> None:
        asyncio.run(
            update_state(active_task="task", tmp={"nested": {"first": 1}})
        )
        state = asyncio.run(
            update_state(active_task=None, tmp={"nested": {"second": 2}})
        )

        self.assertIsNone(state.active_task)
        self.assertEqual(state.tmp, {"nested": {"first": 1, "second": 2}})

    def test_replace_tmp_clears_execution_state(self) -> None:
        asyncio.run(update_state(tmp={"execution": {"paused": False}}))
        state = asyncio.run(update_state(tmp={}, replace_tmp=True))
        self.assertEqual(state.tmp, {})

    def test_silent_mode_is_derived_from_not_active_user_state(self) -> None:
        self.assertFalse(is_silent_mode(FullState()))
        self.assertFalse(
            is_silent_mode(FullState(user_state=UserStateEnum.ACTIVE))
        )
        self.assertTrue(
            is_silent_mode(FullState(user_state=UserStateEnum.NOT_ACTIVE))
        )

    def test_main_menu_shows_action_for_current_mode(self) -> None:
        active_keyboard = get_main_menu(active_task=False, silent_mode=False)
        silent_keyboard = get_main_menu(active_task=False, silent_mode=True)
        active_labels = {
            button.text for row in active_keyboard.keyboard for button in row
        }
        silent_labels = {
            button.text for row in silent_keyboard.keyboard for button in row
        }

        self.assertIn(MainMenu.SILENT_MODE, active_labels)
        self.assertNotIn(MainMenu.UNSILENT_MODE, active_labels)
        self.assertIn(MainMenu.UNSILENT_MODE, silent_labels)
        self.assertNotIn(MainMenu.SILENT_MODE, silent_labels)

    def test_documents_type_hint_survives_restart(self) -> None:
        documents = Documents()
        task = documents.create(
            {"name": "backlog"}, type_hint=DocumentType.TASK_MODEL
        )

        reloaded = Documents()
        indexed = {item.uuid: item.type for item in reloaded.get_list()}

        self.assertEqual(indexed[task.uuid], DocumentType.TASK_MODEL)
        self.assertIsInstance(reloaded.read(task.uuid), TaskModel)

    def test_documents_recovers_a_corrupt_index(self) -> None:
        index = Memory.DATA_DIR / "documents" / "index.json"
        index.parent.mkdir(parents=True)
        index.write_text("not json", encoding="utf-8")

        documents = Documents()

        self.assertEqual(documents.get_list(), [])
        self.assertEqual(json.loads(index.read_text(encoding="utf-8")), [])

    def test_habits_store_crud_persists(self) -> None:
        created = HabitsStore().create("Exercise", minimum=3, maximum=5)
        loaded = HabitsStore()

        self.assertEqual(loaded.get(created.uuid).name, "Exercise")
        self.assertEqual(loaded.get(created.uuid).allowed.min, 3)
        self.assertEqual(loaded.get(created.uuid).allowed.max, 5)
        self.assertTrue(loaded.delete(created.uuid))
        self.assertFalse(loaded.delete(created.uuid))

    def test_rituals_store_crud_and_plan_copy_persist(self) -> None:
        created = RitualsStore().create(
            {
                "name": "Morning",
                "expected_duration": "30 min.",
                "tags": ["#ritual"],
                "checklist": ["Water"],
            }
        )
        loaded = RitualsStore()
        copied = loaded.as_plan_task(created.uuid)

        self.assertEqual(loaded.get(created.uuid).name, "Morning")
        self.assertNotEqual(copied.uuid, created.uuid)
        self.assertEqual(copied.checklist, ["Water"])
        self.assertTrue(loaded.delete(created.uuid))
        self.assertFalse(loaded.delete(created.uuid))

    def test_rituals_store_migrates_legacy_documents(self) -> None:
        legacy = Documents().create(
            {"name": "Evening", "checklist": ["Dinner"]},
            type_hint=DocumentType.RITUAL_MODEL,
        )

        store = RitualsStore()

        self.assertEqual([ritual.name for ritual in store.list()], ["Evening"])
        self.assertTrue((Memory.DATA_DIR / "rituals.json").exists())
        self.assertEqual(
            Documents().get_list(type=DocumentType.RITUAL_MODEL), []
        )
        self.assertFalse(
            (Memory.DATA_DIR / "documents" / legacy.file).exists()
        )
