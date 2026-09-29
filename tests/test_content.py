import tempfile
import unittest
from pathlib import Path

from content import backlog_ct, habits_ct, rituals_ct
from interfaces.document import DocumentType
from memory.documents import Documents
from memory.memory import Memory
from services.habits import HabitsStore
from services.rituals import RitualsStore


class ContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.original_data_dir = Memory.DATA_DIR
        Memory.DATA_DIR = Path(self.directory.name) / ".data"

    def tearDown(self) -> None:
        Memory.DATA_DIR = self.original_data_dir
        self.directory.cleanup()

    def test_habits_content_lists_global_habits_and_ranges(self) -> None:
        HabitsStore().create("Exercise", minimum=3, maximum=5)

        content = habits_ct()

        self.assertIn("Global Habits:", content)
        self.assertIn("1. Exercise [3-5]", content)

    def test_habits_content_supports_status_and_empty_state(self) -> None:
        content = habits_ct("Habit deleted!")

        self.assertTrue(content.startswith("Habit deleted!"))
        self.assertIn("No habits configured.", content)

    def test_rituals_content_lists_all_template_fields(self) -> None:
        RitualsStore().create(
            {
                "name": "Morning",
                "expected_duration": "30 min.",
                "position": 1,
                "tags": ["#ritual"],
                "checklist": ["Water", "Stretch"],
            }
        )

        content = rituals_ct()

        self.assertIn("Global Rituals:", content)
        self.assertIn("1. Morning", content)
        self.assertIn("Duration: 30 min.", content)
        self.assertIn("Position: 1", content)
        self.assertIn("Tags: #ritual", content)
        self.assertIn("Checklist: Water; Stretch", content)

    def test_rituals_content_supports_status_and_empty_state(self) -> None:
        content = rituals_ct("Ritual deleted!")

        self.assertTrue(content.startswith("Ritual deleted!"))
        self.assertIn("No rituals configured.", content)

    def test_backlog_content_lists_all_task_fields(self) -> None:
        Documents().create(
            {
                "name": "Prepare release",
                "recommended_start_time": "09:00",
                "recommended_end_time": "10:00",
                "expected_duration": "1 hour",
                "position": 2,
                "tags": ["#goal"],
                "checklist": ["Tests", "Deploy"],
            },
            type_hint=DocumentType.TASK_MODEL,
        )

        content = backlog_ct()

        self.assertIn("Backlog Tasks:", content)
        self.assertIn("1. Prepare release", content)
        self.assertIn("Recommended start: 09:00", content)
        self.assertIn("Recommended end: 10:00", content)
        self.assertIn("Duration: 1 hour", content)
        self.assertIn("Position: 2", content)
        self.assertIn("Tags: #goal", content)
        self.assertIn("Checklist: Tests; Deploy", content)

    def test_backlog_content_supports_status_and_empty_state(self) -> None:
        content = backlog_ct("Task added!")

        self.assertTrue(content.startswith("Task added!"))
        self.assertIn("No tasks in backlog.", content)


if __name__ == "__main__":
    unittest.main()
