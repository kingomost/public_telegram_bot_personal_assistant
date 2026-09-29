import asyncio
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

import config
from endpoints.goals import goal_budget_value, goal_duration_value
from endpoints.planning_callbacks import planning_goal_tag
from interfaces.goal import GoalTimeBudget
from interfaces.plan import PlanModel, TaskModel
from interfaces.state import FullState
from keyboards import (
    GoalBudgetValue,
    GoalDurationValue,
    PlanningGoalTag,
    goal_budget_values_kb,
    goal_duration_kb,
)
from memory.memory import Memory
from services.goals import GoalAnalytics, GoalsStore
from services.plans import PlanStore
from services.reports import render_goal_report, render_range_report


class GoalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.original_data_dir = Memory.DATA_DIR
        Memory.DATA_DIR = Path(self.directory.name) / ".data"

    def tearDown(self) -> None:
        Memory.DATA_DIR = self.original_data_dir
        self.directory.cleanup()

    def test_nested_goals_persist_and_have_unique_task_tags(self) -> None:
        store = GoalsStore()
        root = store.create("Remote job")
        child = store.create("Portfolio", parent_uuid=root.uuid)
        sibling = store.create("Portfolio", parent_uuid=root.uuid)
        store.update(
            root.uuid,
            budget=GoalTimeBudget(min_hours=100, max_hours=120),
            duration_days=14,
            expected_result="Receive an offer",
        )

        loaded = GoalsStore()
        self.assertEqual(loaded.get(child.uuid).name, "Portfolio")
        self.assertNotEqual(child.tag, sibling.tag)
        self.assertTrue(child.tag.startswith(f"{config.GOAL_TAG}/portfolio-"))
        self.assertEqual(loaded.get(root.uuid).duration_days, 14)
        self.assertEqual(loaded.get(root.uuid).time_budget.max_hours, 120)

    def test_goal_budget_options_use_offsets_and_existing_bounds(self) -> None:
        uuid = "12345678-1234-1234-1234-123456789012"
        minimum = goal_budget_values_kb(uuid, "min", None, None)
        maximum = goal_budget_values_kb(uuid, "max", None, None)
        constrained_min = goal_budget_values_kb(uuid, "min", None, 240)
        constrained_max = goal_budget_values_kb(uuid, "max", 400, None, offset=0)

        def values(keyboard):
            return [
                GoalBudgetValue.unpack(button.callback_data).value
                for row in keyboard.inline_keyboard
                for button in row
                if button.text not in {"<", ">"}
            ]

        self.assertEqual(values(minimum)[0], 200)
        self.assertEqual(values(maximum)[0], 300)
        self.assertLessEqual(max(values(constrained_min)), 240)
        self.assertGreaterEqual(min(values(constrained_max)), 400)

    def test_goal_duration_options_cover_zero_to_one_hundred(self) -> None:
        uuid = "12345678-1234-1234-1234-123456789012"
        first = goal_duration_kb(uuid)
        last = goal_duration_kb(uuid, offset=20)

        def values(keyboard):
            return [
                GoalDurationValue.unpack(button.callback_data).value
                for row in keyboard.inline_keyboard
                for button in row
                if button.text not in {"<", ">"}
            ]

        self.assertEqual(values(first), list(range(0, 60, 5)))
        self.assertEqual(values(last)[-1], 100)

    def test_goal_budget_and_duration_callbacks_persist_values(self) -> None:
        node = GoalsStore().create("Course")
        state = Memory("state.json", FullState)
        state.data.bot_dialog_message_id = 42
        state.save()
        callback = AsyncMock()
        bot = AsyncMock()

        with patch("endpoints.goals.render_menu", new=AsyncMock()):
            asyncio.run(
                goal_budget_value(
                    callback,
                    GoalBudgetValue(field="min", uuid=node.uuid, value=200),
                    bot,
                )
            )
            asyncio.run(
                goal_budget_value(
                    callback,
                    GoalBudgetValue(field="max", uuid=node.uuid, value=400),
                    bot,
                )
            )
            asyncio.run(
                goal_duration_value(
                    callback,
                    GoalDurationValue(uuid=node.uuid, value=0),
                    bot,
                )
            )

        loaded = GoalsStore().get(node.uuid)
        self.assertEqual(loaded.time_budget.min_hours, 200)
        self.assertEqual(loaded.time_budget.max_hours, 400)
        self.assertEqual(loaded.duration_days, 0)

    def test_child_time_rolls_up_to_parent(self) -> None:
        store = GoalsStore()
        root = store.create("Career")
        child = store.create("Portfolio", parent_uuid=root.uuid)
        linked = TaskModel(
            name="Build project", tags=[config.GOAL_TAG, child.tag]
        )
        generic = TaskModel(name="Research", tags=[config.GOAL_TAG])
        Memory.store(
            "calendar/14_06_2026.json",
            PlanModel,
            {"tasks": [linked, generic]},
        )
        plan = PlanStore("14_06_2026.json")
        plan.start_task(linked.uuid, 1_700_000_000)
        plan.stop_task(
            linked.uuid, 1_700_000_000, 1_700_003_600, completed=True
        )
        plan.start_task(generic.uuid, 1_700_004_000)
        plan.stop_task(
            generic.uuid, 1_700_004_000, 1_700_005_800, completed=False
        )

        stats, unassigned = GoalAnalytics(store).calculate()
        self.assertEqual(stats[child.uuid].hours, 1)
        self.assertEqual(stats[root.uuid].hours, 1)
        self.assertEqual(unassigned.hours, 0.5)
        self.assertEqual(len(stats[root.uuid].active_dates), 1)

    def test_selecting_subgoal_adds_general_and_specific_tags(self) -> None:
        node = GoalsStore().create("Course")
        state = Memory("state.json", FullState)
        state.data.bot_dialog_message_id = 42
        state.data.tmp = {"task": {"name": "Study", "tags": []}}
        state.save()

        with patch(
            "endpoints.planning_callbacks.render_menu", new=AsyncMock()
        ):
            asyncio.run(
                planning_goal_tag(
                    AsyncMock(),
                    PlanningGoalTag(uuid=node.uuid),
                    AsyncMock(),
                )
            )

        tags = Memory("state.json", FullState).data.tmp["task"]["tags"]
        self.assertEqual(tags, [config.GOAL_TAG, node.tag])

    def test_goal_and_range_reports_render_measured_time(self) -> None:
        root = GoalsStore().create("Launch")
        task = TaskModel(name="Ship", tags=[config.GOAL_TAG, root.tag])
        Memory.store(
            "calendar/14_06_2026.json", PlanModel, {"tasks": [task]}
        )
        plan = PlanStore("14_06_2026.json")
        plan.start_task(task.uuid, 1_700_000_000)
        plan.stop_task(task.uuid, 1_700_000_000, 1_700_003_600, completed=True)

        goal_report = render_goal_report()
        range_report = render_range_report(
            "Test", date(2026, 6, 14), date(2026, 6, 14)
        )
        self.assertIn("Launch", goal_report)
        self.assertIn("1.0h", goal_report)
        self.assertIn("Goal work: 1.0 hours", range_report)
