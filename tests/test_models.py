import unittest

from pydantic import ValidationError

from interfaces.plan import HabitAllowedCriteria, PlanModel, ReminderModel, TaskModel


class ModelTests(unittest.TestCase):
    def test_plan_defaults_are_independent(self) -> None:
        first = PlanModel()
        second = PlanModel()
        first.tasks.append(TaskModel(name="one"))

        self.assertEqual(len(first.tasks), 1)
        self.assertEqual(second.tasks, [])

    def test_optional_legacy_lists_are_normalized(self) -> None:
        task = TaskModel(name="legacy", tags=None, checklist=None)
        plan = PlanModel(tasks=None, reminders=None, habits=None, rituals=None)
        ritual = TaskModel(name="legacy", checklist=None)

        self.assertEqual(task.tags, [])
        self.assertEqual(task.checklist, [])
        self.assertEqual(plan.tasks, [])
        self.assertEqual(ritual.checklist, [])

    def test_habit_range_must_be_ordered(self) -> None:
        with self.assertRaises(ValidationError):
            HabitAllowedCriteria(min=3, max=1)
        with self.assertRaises(ValidationError):
            HabitAllowedCriteria(min=-1, max=1)

    def test_legacy_plan_rituals_migrate_into_tasks(self) -> None:
        plan = PlanModel.model_validate(
            {"rituals": [{"name": "Morning", "checklist": ["Water"]}]}
        )
        self.assertEqual(len(plan.tasks), 1)
        self.assertEqual(plan.tasks[0].name, "Morning")

    def test_tasks_always_have_uuid_and_reminder_time_is_validated(self) -> None:
        self.assertTrue(TaskModel(name="new").uuid)
        self.assertTrue(
            TaskModel.model_validate({"name": "legacy", "uuid": None}).uuid
        )
        self.assertEqual(ReminderModel(datetime="9:05", name="test").datetime, "09:05")
        with self.assertRaises(ValidationError):
            ReminderModel(datetime="25:00", name="invalid")
