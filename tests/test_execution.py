import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from endpoints.execution import create_quick_task
from interfaces.plan import PlanModel
from interfaces.state import FullState
from memory.memory import Memory


class ExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.original_data_dir = Memory.DATA_DIR
        Memory.DATA_DIR = Path(self.directory.name) / ".data"
        state = Memory("state.json", FullState)
        state.data.bot_dialog_message_id = 42
        state.data.bot_hint_message_id = 43
        state.save()

    def tearDown(self) -> None:
        Memory.DATA_DIR = self.original_data_dir
        self.directory.cleanup()

    def test_quick_task_is_created_and_started(self) -> None:
        message = AsyncMock()
        message.text = "Urgent task"
        message.message_id = 44
        state = AsyncMock()
        bot = AsyncMock()

        with (
            patch("endpoints.execution.render_menu", new=AsyncMock()),
            patch("endpoints.execution.delete_chat_message", new=AsyncMock()),
            patch("services.plans.date_for_date", return_value="14_06_2026"),
            patch("endpoints.execution.time.time", return_value=1_700_000_000),
        ):
            asyncio.run(create_quick_task(message, state, bot))

        plan = Memory("calendar/14_06_2026.json", PlanModel).data
        saved_state = Memory("state.json", FullState).data
        self.assertEqual(len(plan.tasks), 1)
        self.assertEqual(plan.tasks[0].name, "Urgent task")
        self.assertEqual(saved_state.active_task, plan.tasks[0].uuid)
        self.assertEqual(
            saved_state.tmp["execution"]["period_started_at"],
            1_700_000_000,
        )
        state.set_state.assert_awaited()
