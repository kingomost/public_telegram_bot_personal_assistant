import asyncio
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import config
from endpoints.dashboard import confirm_alarm
from enums import AlarmAction
from interfaces.plan import PlanModel, ReminderModel, TaskModel
from interfaces.state import FullState, UserStateEnum
from keyboards import AlarmActions, ActualSleepTime
from memory.memory import Memory
from services.heartbeat import tick
from services.plans import PlanStore


class HeartbeatDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.original_data_dir = Memory.DATA_DIR
        Memory.DATA_DIR = Path(self.directory.name) / ".data"

    def tearDown(self) -> None:
        Memory.DATA_DIR = self.original_data_dir
        self.directory.cleanup()

    def _run_tick(self, now: datetime, timestamp: int, bot: AsyncMock) -> None:
        with (
            patch("services.heartbeat.datetime") as mocked_datetime,
            patch("services.heartbeat.time.time", return_value=timestamp),
        ):
            mocked_datetime.now.return_value = now
            asyncio.run(tick(bot))

    def test_alarm_is_delivered_in_silent_mode_and_throttled(self) -> None:
        Memory.store(
            "calendar/15_06_2026.json",
            PlanModel,
            {"wakeup_time": "07:00"},
        )
        Memory.store(
            "state.json",
            FullState,
            {"user_state": UserStateEnum.NOT_ACTIVE},
        )
        bot = AsyncMock()
        now = datetime(2026, 6, 15, 7, 5)

        self._run_tick(now, 1_000, bot)
        self._run_tick(now, 1_100, bot)

        self.assertEqual(bot.send_message.await_count, 1)
        call = bot.send_message.await_args
        self.assertTrue(call.kwargs["text"].startswith("Alarm:"))
        self.assertTrue(call.kwargs["reply_markup"].inline_keyboard)

    def test_silent_mode_suppresses_coaching(self) -> None:
        Memory.store(
            "calendar/15_06_2026.json",
            PlanModel,
            {"tasks": [TaskModel(name="Write report")]},
        )
        Memory.store(
            "state.json",
            FullState,
            {
                "user_state": UserStateEnum.NOT_ACTIVE,
                "user_last_activity_ttamp": 1,
            },
        )
        bot = AsyncMock()

        self._run_tick(datetime(2026, 6, 15, 12, 0), 10_000, bot)

        bot.send_message.assert_not_awaited()

    def test_due_reminder_wins_over_task_coaching(self) -> None:
        Memory.store(
            "calendar/15_06_2026.json",
            PlanModel,
            {
                "tasks": [TaskModel(name="Write report")],
                "reminders": [
                    ReminderModel(datetime="09:00", name="Call client")
                ],
            },
        )
        Memory.store(
            "state.json",
            FullState,
            {"user_last_activity_ttamp": 1},
        )
        bot = AsyncMock()

        self._run_tick(datetime(2026, 6, 15, 12, 0), 10_000, bot)

        self.assertEqual(bot.send_message.await_count, 1)
        self.assertEqual(
            bot.send_message.await_args.kwargs["text"],
            "Reminder: Call client",
        )

    def test_previous_sleep_time_uses_previous_calendar_day(self) -> None:
        plan = PlanStore("test.json")
        wakeup = datetime(2026, 6, 15, 7, 0, tzinfo=ZoneInfo(config.TIME_ZONE))

        sleep = plan.set_previous_sleep_time("23:30", wakeup.timestamp())

        self.assertEqual(sleep.date, "14_06_2026")
        self.assertEqual(sleep.time, "23:30:00")

    def test_alarm_confirmation_logs_wakeup_and_asks_for_sleep(self) -> None:
        callback = AsyncMock()
        callback.message.message_id = 42
        bot = AsyncMock()
        plan = MagicMock()
        plan.set_real_wakeup.return_value = SimpleNamespace(time="07:05:00")

        with patch("endpoints.dashboard.PlanStore", return_value=plan):
            asyncio.run(
                confirm_alarm(
                    callback,
                    AlarmActions(action=AlarmAction.WOKE_UP),
                    bot,
                )
            )

        plan.set_real_wakeup.assert_called_once_with()
        call = bot.edit_message_text.await_args
        self.assertIn("What time did you fall asleep", call.kwargs["text"])
        sleep_callback = call.kwargs["reply_markup"].inline_keyboard[0][0]
        self.assertIsNotNone(
            ActualSleepTime.unpack(sleep_callback.callback_data).value
        )
