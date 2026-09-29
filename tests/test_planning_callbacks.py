import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from content import plan_habits_ct
from endpoints.planning_callbacks import planning_add_ritual, planning_add_tag, planning_reminder_fields, planning_tasks_actions, planning_toggle_habit, time_actions
from enums import OptionAction, PlanningHabitAction, PlanningReminderField, PlanningTasksAction
from interfaces.plan import HabitModel, PlanModel
from interfaces.state import FullState
from keyboards import PlanningAddRitual, PlanningAddTag, PlanningHabitToggle, PlanningReminderFields, PlanningTasksActions, TimeOptions
from memory.memory import Memory
from services.habits import HabitsStore
from services.rituals import RitualsStore


class PlanningCallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.original_data_dir = Memory.DATA_DIR
        Memory.DATA_DIR = Path(self.directory.name) / ".data"
        state = Memory("state.json", FullState)
        state.data.bot_dialog_message_id = 42
        state.data.tmp = {"plan_file": "14_06_2026.json"}
        state.save()

    def tearDown(self) -> None:
        Memory.DATA_DIR = self.original_data_dir
        self.directory.cleanup()

    def test_time_actions_updates_wakeup_and_sleep_time(self) -> None:
        callback = AsyncMock()
        bot = AsyncMock()
        state = AsyncMock()

        with patch(
            "endpoints.planning_callbacks.render_menu", new=AsyncMock()
        ):
            asyncio.run(
                time_actions(
                    callback,
                    TimeOptions(
                        obj="plan", field="wakeup_time", value="07:30"
                    ),
                    state,
                    bot,
                )
            )
            asyncio.run(
                time_actions(
                    callback,
                    TimeOptions(
                        obj="plan", field="sleep_time", value="23:15"
                    ),
                    state,
                    bot,
                )
            )

        plan = Memory("calendar/14_06_2026.json", PlanModel).data
        self.assertEqual(plan.wakeup_time, "07:30")
        self.assertEqual(plan.sleep_time, "23:15")
        self.assertEqual(callback.answer.await_count, 2)

    def test_none_tag_clears_task_tags(self) -> None:
        state_memory = Memory("state.json", FullState)
        state_memory.data.tmp = {
            "plan_file": "14_06_2026.json",
            "task": {"name": "Test", "tags": ["#other"]},
        }
        state_memory.save()
        callback = AsyncMock()

        with patch(
            "endpoints.planning_callbacks.render_menu", new=AsyncMock()
        ):
            asyncio.run(
                planning_add_tag(
                    callback,
                    PlanningAddTag(value=OptionAction.NONE),
                    AsyncMock(),
                    AsyncMock(),
                )
            )

        task = Memory("state.json", FullState).data.tmp["task"]
        self.assertEqual(task["tags"], [])
        callback.answer.assert_awaited_once()

    def test_time_actions_rejects_missing_plan_context(self) -> None:
        state_memory = Memory("state.json", FullState)
        state_memory.data.tmp = {}
        state_memory.save()
        callback = AsyncMock()

        asyncio.run(
            time_actions(
                callback,
                TimeOptions(obj="plan", field="wakeup_time", value="07:30"),
                AsyncMock(),
                AsyncMock(),
            )
        )

        callback.answer.assert_awaited_once_with(
            "Select a planning date first", show_alert=True
        )

    def test_reminder_time_updates_draft_without_changing_plan_times(self) -> None:
        state_memory = Memory("state.json", FullState)
        state_memory.data.tmp["reminder_draft"] = {
            "name": "Call",
            "datetime": None,
            "description": None,
        }
        state_memory.save()
        callback = AsyncMock()

        with patch(
            "endpoints.planning_callbacks.render_menu", new=AsyncMock()
        ):
            asyncio.run(
                time_actions(
                    callback,
                    TimeOptions(
                        obj="reminder", field="datetime", value="10:30"
                    ),
                    AsyncMock(),
                    AsyncMock(),
                )
            )

        saved_state = Memory("state.json", FullState).data
        plan = Memory("calendar/14_06_2026.json", PlanModel).data
        self.assertEqual(
            saved_state.tmp["reminder_draft"]["datetime"], "10:30"
        )
        self.assertIsNone(plan.wakeup_time)
        self.assertIsNone(plan.sleep_time)

    def test_reminder_save_persists_valid_draft(self) -> None:
        state_memory = Memory("state.json", FullState)
        state_memory.data.tmp["reminder_draft"] = {
            "name": "Call",
            "datetime": "10:30",
            "description": "Client",
        }
        state_memory.save()
        callback = AsyncMock()

        with patch(
            "endpoints.planning_callbacks.render_menu", new=AsyncMock()
        ):
            asyncio.run(
                planning_reminder_fields(
                    callback,
                    PlanningReminderFields(
                        action=PlanningReminderField.SAVE
                    ),
                    AsyncMock(),
                    AsyncMock(),
                )
            )

        plan = Memory("calendar/14_06_2026.json", PlanModel).data
        self.assertEqual(len(plan.reminders), 1)
        self.assertEqual(plan.reminders[0].name, "Call")
        self.assertEqual(plan.reminders[0].datetime, "10:30")
        self.assertNotIn(
            "reminder_draft", Memory("state.json", FullState).data.tmp
        )

    def test_reminder_save_requires_name_and_time(self) -> None:
        state_memory = Memory("state.json", FullState)
        state_memory.data.tmp["reminder_draft"] = {
            "name": None,
            "datetime": None,
            "description": None,
        }
        state_memory.save()
        callback = AsyncMock()

        asyncio.run(
            planning_reminder_fields(
                callback,
                PlanningReminderFields(action=PlanningReminderField.SAVE),
                AsyncMock(),
                AsyncMock(),
            )
        )

        callback.answer.assert_awaited_once_with(
            "Set a reminder name first", show_alert=True
        )

    def test_add_all_habits_persists_without_duplicates(self) -> None:
        store = HabitsStore()
        first = store.create("Exercise", minimum=1, maximum=1)
        second = store.create("Read", minimum=1, maximum=2)
        callback = AsyncMock()

        with patch(
            "endpoints.planning_callbacks.render_menu", new=AsyncMock()
        ):
            asyncio.run(
                planning_toggle_habit(
                    callback,
                    PlanningHabitToggle(action=PlanningHabitAction.ADD_ALL),
                    AsyncMock(),
                )
            )
            asyncio.run(
                planning_toggle_habit(
                    callback,
                    PlanningHabitToggle(action=PlanningHabitAction.ADD_ALL),
                    AsyncMock(),
                )
            )

        plan = Memory("calendar/14_06_2026.json", PlanModel).data
        self.assertEqual(
            {habit.uuid for habit in plan.habits}, {first.uuid, second.uuid}
        )
        self.assertEqual(len(plan.habits), 2)

    def test_toggle_habit_adds_and_removes_selected_habit(self) -> None:
        habit = HabitsStore().create("Exercise", minimum=1, maximum=1)
        callback = AsyncMock()
        selection = PlanningHabitToggle(
            action=PlanningHabitAction.TOGGLE_HABIT,
            uuid=habit.uuid,
        )

        with patch(
            "endpoints.planning_callbacks.render_menu", new=AsyncMock()
        ):
            asyncio.run(
                planning_toggle_habit(callback, selection, AsyncMock())
            )
            self.assertEqual(
                len(Memory("calendar/14_06_2026.json", PlanModel).data.habits),
                1,
            )
            asyncio.run(
                planning_toggle_habit(callback, selection, AsyncMock())
            )

        self.assertEqual(
            Memory("calendar/14_06_2026.json", PlanModel).data.habits, []
        )

    def test_add_ritual_reads_store_and_copies_into_plan_tasks(self) -> None:
        ritual = RitualsStore().create(
            {
                "name": "Morning",
                "completed": True,
                "started_at": 1,
                "checklist": ["Water"],
            }
        )
        callback = AsyncMock()

        with patch(
            "endpoints.planning_callbacks.render_menu", new=AsyncMock()
        ):
            asyncio.run(
                planning_add_ritual(
                    callback,
                    PlanningAddRitual(uuid=ritual.uuid),
                    AsyncMock(),
                )
            )

        task = Memory("calendar/14_06_2026.json", PlanModel).data.tasks[0]
        self.assertEqual(task.name, "Morning")
        self.assertEqual(task.checklist, ["Water"])
        self.assertNotEqual(task.uuid, ritual.uuid)
        self.assertFalse(task.completed)
        self.assertIsNone(task.started_at)

    def test_add_ritual_selector_shows_ritual_details(self) -> None:
        RitualsStore().create(
            {
                "name": "Morning",
                "expected_duration": "30 min.",
                "position": 1,
                "tags": ["#ritual"],
                "checklist": ["Water"],
            }
        )
        callback = AsyncMock()

        with patch(
            "endpoints.planning_callbacks.render_menu", new=AsyncMock()
        ) as render:
            asyncio.run(
                planning_tasks_actions(
                    callback,
                    PlanningTasksActions(action=PlanningTasksAction.ADD_RITUAL),
                    AsyncMock(),
                    AsyncMock(),
                )
            )

        text = render.await_args.args[2]
        self.assertIn("Select a ritual to add:", text)
        self.assertIn("Duration: 30 min.", text)
        self.assertIn("Position: 1", text)
        self.assertIn("Checklist: Water", text)

    def test_plan_habits_content_lists_all_and_selected_habits(self) -> None:
        exercise = HabitsStore().create("Exercise", minimum=2, maximum=4)
        read = HabitsStore().create("Read", minimum=1, maximum=1)
        plan = Memory("calendar/14_06_2026.json", PlanModel)
        plan.data.habits = [exercise]
        plan.save()

        text = plan_habits_ct("14_06_2026.json")

        self.assertIn("All Habits:", text)
        self.assertIn("Exercise [2-4] - selected", text)
        self.assertIn("Read [1-1] - not selected", text)
        self.assertIn("Selected Habits:", text)
        self.assertIn("1. Exercise [2-4]", text)


if __name__ == "__main__":
    unittest.main()
