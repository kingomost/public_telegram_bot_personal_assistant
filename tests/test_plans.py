import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from interfaces.plan import HabitModel, PlanModel, TaskModel
from memory.memory import Memory
from services.plans import PlanStore


class PlanServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.original_data_dir = Memory.DATA_DIR
        Memory.DATA_DIR = Path(self.directory.name) / ".data"

    def tearDown(self) -> None:
        Memory.DATA_DIR = self.original_data_dir
        self.directory.cleanup()

    def test_tasks_are_sorted_by_position_and_none_is_split_around_middle(self) -> None:
        positions = [None, None, 2, 1, None, -2, -1, None, "middle", -2, 1, None, "middle"]
        plan = PlanModel(
            tasks=[TaskModel(name=str(index), position=position) for index, position in enumerate(positions)]
        )

        self.assertEqual(
            [task.position for task in plan.tasks],
            [1, 1, 2, None, None, "middle", "middle", None, None, None, -2, -2, -1],
        )

    def test_position_zero_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            TaskModel(name="invalid", position=0)
        with self.assertRaises(ValidationError):
            TaskModel(name="invalid", position="0")

    def test_task_sessions_and_checkpoints_are_persisted(self) -> None:
        task = TaskModel(name="Work", checklist=["First", "Second"])
        Memory.store("calendar/test.json", PlanModel, {"tasks": [task]})
        plan = PlanStore("test.json")

        plan.start_task(task.uuid, 1_700_000_000)
        plan.stop_task(
            task.uuid,
            1_700_000_000,
            1_700_000_600,
            completed=False,
        )
        plan.toggle_checkpoint(task.uuid, 0)
        plan.start_task(task.uuid, 1_700_001_000)
        plan.stop_task(
            task.uuid,
            1_700_001_000,
            1_700_001_300,
            completed=True,
        )

        loaded = PlanStore("test.json")
        task_meta = loaded.task_meta(task.uuid, create=False)
        self.assertEqual(len(task_meta.periods), 2)
        self.assertTrue(task_meta.checklist[0].completed)
        self.assertTrue(loaded.task(task.uuid).completed)
        self.assertTrue(loaded.task_has_activity(task.uuid))

    def test_habit_count_never_drops_below_zero(self) -> None:
        habit = HabitModel(uuid="habit", name="Water")
        Memory.store("calendar/test.json", PlanModel, {"habits": [habit]})
        plan = PlanStore("test.json")

        self.assertEqual(plan.adjust_habit("habit", 1), 1)
        self.assertEqual(plan.adjust_habit("habit", -2), 0)
        self.assertIsNone(plan.adjust_habit("missing", 1))
        self.assertEqual(PlanStore("test.json").habit_count("habit"), 0)

    def test_real_wakeup_and_sleep_are_logged(self) -> None:
        plan = PlanStore("test.json")
        wakeup = plan.set_real_wakeup(1_700_000_000)
        sleep = plan.set_real_sleep(1_700_003_600)

        loaded = PlanStore("test.json").data.meta
        self.assertEqual(loaded.real_wakeup_time.ttamp_sec, wakeup.ttamp_sec)
        self.assertEqual(loaded.real_sleep_time.ttamp_sec, sleep.ttamp_sec)

    def test_create_task_uses_task_defaults(self) -> None:
        task = PlanStore("test.json").create_task("Unexpected work")
        loaded = PlanStore("test.json").task(task.uuid)

        self.assertEqual(loaded.name, "Unexpected work")
        self.assertIsNone(loaded.position)
        self.assertIsNone(loaded.expected_duration)
        self.assertEqual(loaded.tags, [])
        self.assertEqual(loaded.checklist, [])
        self.assertFalse(loaded.completed)
