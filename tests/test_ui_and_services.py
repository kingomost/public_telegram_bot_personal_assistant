import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import config
import main
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup

from interfaces.plan import PlanModel, ReminderModel, TaskModel
from interfaces.state import FullState, UserStateEnum
from keyboards import BacklogActions, BacklogSelectDelete, ExecutionActions, HabitRangeOption, PlanningHabitToggle, PlanningReminderFields, TimeOptions, backlog_actions_kb, backlog_delete_kb, execution_select_task_kb, habit_range_kb, planning_add_ritual_kb, planning_habits_kb, planning_reminder_fields_kb, planning_reminders_kb, time_options_kb
from enums import ExecutionAction, PlanningHabitAction
from interfaces.plan import HabitModel
from memory.memory import Memory
from services.heartbeat import tick
from utils.ui import render_menu
from endpoints.dashboard import progress, report
from endpoints.commands import command_menu
from endpoints.execution import _start_task_items, _start_task_text
from menu import ExitMenu, MainMenu
from services.plans import PlanStore


class UiAndServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.original_data_dir = Memory.DATA_DIR
        Memory.DATA_DIR = Path(self.directory.name) / ".data"

    def tearDown(self) -> None:
        Memory.DATA_DIR = self.original_data_dir
        self.directory.cleanup()

    def test_time_keyboard_keeps_field_when_paginating(self) -> None:
        keyboard = time_options_kb("plan", "wakeup_time", offset=20)
        callbacks = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
            if button.text in {"<", ">"}
        ]
        self.assertTrue(callbacks)
        unpacked = [TimeOptions.unpack(callback) for callback in callbacks]
        self.assertTrue(all(item.field == "wakeup_time" for item in unpacked))
        self.assertTrue(all(keyboard.inline_keyboard))

    def test_task_selection_always_includes_quick_create(self) -> None:
        keyboard = execution_select_task_kb([])
        quick_button = next(
            button
            for row in keyboard.inline_keyboard
            for button in row
            if button.text == "➕ Create quickly"
        )

        callback = ExecutionActions.unpack(quick_button.callback_data)
        self.assertEqual(callback.action, ExecutionAction.QUICK_CREATE)

    def test_task_selection_uses_two_columns(self) -> None:
        keyboard = execution_select_task_kb([
            {"uuid": "1", "name": "One"},
            {"uuid": "2", "name": "Two"},
            {"uuid": "3", "name": "Three"},
        ])

        self.assertEqual([button.text for button in keyboard.inline_keyboard[0]], ["One", "Two"])
        self.assertEqual([button.text for button in keyboard.inline_keyboard[1]], ["Three"])

    def test_start_task_items_move_started_and_done_to_end(self) -> None:
        plan_memory = Memory("calendar/test.json", PlanModel)
        plan_memory.data.tasks = [
            TaskModel(uuid="done", name="Done", completed=True),
            TaskModel(uuid="fresh", name="Fresh", expected_duration="30 min."),
            TaskModel(uuid="started", name="Started"),
        ]
        plan_memory.save()
        plan = PlanStore("test.json")
        plan.start_task("started", 1_700_000_000)
        plan.stop_task(
            "started",
            1_700_000_000,
            1_700_004_260,
            completed=False,
        )

        items = _start_task_items(plan)
        text = _start_task_text(items)

        self.assertEqual([item["uuid"] for item in items], ["fresh", "done", "started"])
        self.assertEqual(items[-1]["name"], "(1 h. 11 min.) Started")
        self.assertIn("Fresh - duration: 30 min.", text)
        self.assertIn("Done (done)", text)
        self.assertIn("Started (started)", text)

    def test_reminder_keyboard_supports_empty_lists(self) -> None:
        keyboard = planning_reminders_kb([])
        self.assertEqual(len(keyboard.inline_keyboard), 2)

    def test_reminder_editor_has_separate_field_buttons(self) -> None:
        keyboard = planning_reminder_fields_kb()
        actions = {
            PlanningReminderFields.unpack(button.callback_data).action.value
            for row in keyboard.inline_keyboard
            for button in row
        }
        self.assertEqual(
            actions, {"Name", "Time", "Description", "Save", "GoBack"}
        )

        time_keyboard = time_options_kb(
            "reminder", "datetime", offset=32
        )
        self.assertNotIn(
            "None",
            [
                button.text
                for row in time_keyboard.inline_keyboard
                for button in row
            ],
        )

    def test_habit_range_keyboard_filters_maximum_values(self) -> None:
        keyboard = habit_range_kb("max", minimum=4)
        values = [
            HabitRangeOption.unpack(button.callback_data).value
            for row in keyboard.inline_keyboard
            for button in row
            if button.callback_data.startswith("HabitRangeOption:")
        ]
        self.assertEqual(values, list(range(4, 11)))

    def test_planning_habits_keyboard_has_add_all(self) -> None:
        keyboard = planning_habits_kb(
            [
                HabitModel(
                    uuid="12345678-1234-1234-1234-123456789012",
                    name="Exercise",
                ),
                HabitModel(
                    uuid="12345678-1234-1234-1234-123456789013",
                    name="Read",
                )
            ],
            set(),
        )
        toggle = keyboard.inline_keyboard[0][0]
        self.assertLessEqual(len(toggle.callback_data.encode()), 64)
        self.assertEqual(
            [button.text for button in keyboard.inline_keyboard[0]],
            ["⬜ Exercise", "⬜ Read"],
        )
        add_all = next(
            button
            for row in keyboard.inline_keyboard
            for button in row
            if button.text == "➕ Add all"
        )
        self.assertEqual(
            PlanningHabitToggle.unpack(add_all.callback_data).action,
            PlanningHabitAction.ADD_ALL,
        )

    def test_planning_ritual_keyboard_uses_two_columns(self) -> None:
        keyboard = planning_add_ritual_kb([
            TaskModel(uuid="1", name="Morning"),
            TaskModel(uuid="2", name="Evening"),
            TaskModel(uuid="3", name="Review"),
        ])

        self.assertEqual(
            [button.text for button in keyboard.inline_keyboard[0]],
            ["Morning", "Evening"],
        )
        self.assertEqual(
            [button.text for button in keyboard.inline_keyboard[1]],
            ["Review"],
        )

    def test_backlog_keyboards_include_delete_flow(self) -> None:
        actions = backlog_actions_kb()
        delete_action = next(
            button
            for row in actions.inline_keyboard
            for button in row
            if button.text == "🗑 Delete Task"
        )
        self.assertEqual(
            BacklogActions.unpack(delete_action.callback_data).action.value,
            "DeleteTask",
        )

        choices = backlog_delete_kb([{"uuid": "task-id", "name": "Task"}])
        delete_choice = choices.inline_keyboard[0][0]
        self.assertEqual(
            BacklogSelectDelete.unpack(delete_choice.callback_data).uuid,
            "task-id",
        )

    def test_render_menu_edits_text_and_markup_together(self) -> None:
        bot = AsyncMock()
        markup = InlineKeyboardMarkup(inline_keyboard=[])

        asyncio.run(render_menu(bot, 10, "text", markup))

        bot.edit_message_text.assert_awaited_once_with(
            chat_id=config.OWNER_ID,
            message_id=10,
            text="text",
            reply_markup=markup,
            parse_mode=None,
        )

    def test_reports_replaces_main_menu_and_sends_inline_selector(self) -> None:
        message = AsyncMock()
        menu_message = AsyncMock()
        message.answer.return_value = menu_message

        asyncio.run(report(message, AsyncMock(), AsyncMock()))

        menu_markup = message.answer.await_args.kwargs["reply_markup"]
        self.assertEqual(message.answer.await_args.kwargs["text"], "REPORTS")
        self.assertEqual(
            menu_markup.keyboard[0][0].text,
            ExitMenu.GO_TO_MAIN_MENU,
        )
        selector_markup = menu_message.reply.await_args.kwargs["reply_markup"]
        self.assertEqual(menu_message.reply.await_args.args[0], "Choose a report:")
        self.assertTrue(selector_markup.inline_keyboard)

    def test_progress_replaces_main_menu_and_sends_inline_actions(self) -> None:
        message = AsyncMock()
        menu_message = AsyncMock()
        message.answer.return_value = menu_message
        plan = object()

        with (
            patch("endpoints.dashboard._today_plan") as today_plan,
            patch("endpoints.dashboard.Memory") as memory,
            patch("endpoints.dashboard._progress_text", return_value="Progress")
            as progress_text,
        ):
            today_plan.return_value.data = plan
            memory.return_value.data.active_task = "task-id"
            asyncio.run(progress(message, AsyncMock(), AsyncMock()))

        menu_markup = message.answer.await_args.kwargs["reply_markup"]
        self.assertEqual(message.answer.await_args.kwargs["text"], "PROGRESS")
        self.assertEqual(
            menu_markup.keyboard[0][0].text,
            ExitMenu.GO_TO_MAIN_MENU,
        )
        progress_text.assert_called_once_with(plan, "task-id")
        self.assertEqual(menu_message.reply.await_args.args[0], "Progress")
        self.assertTrue(
            menu_message.reply.await_args.kwargs["reply_markup"].inline_keyboard
        )

    def test_main_menu_mode_buttons_update_user_state(self) -> None:
        message = AsyncMock()
        message.message_id = 10
        state = AsyncMock()
        bot = AsyncMock()

        with (
            patch("endpoints.commands.clear_chat_history", new=AsyncMock()),
            patch("endpoints.commands.delete_chat_message", new=AsyncMock()),
        ):
            message.text = MainMenu.SILENT_MODE
            asyncio.run(command_menu(message, state, bot))

            saved = Memory("state.json", FullState).data
            self.assertEqual(saved.user_state, UserStateEnum.NOT_ACTIVE)
            silent_markup = message.answer.await_args.kwargs["reply_markup"]
            self.assertEqual(
                silent_markup.keyboard[-1][-1].text,
                MainMenu.UNSILENT_MODE,
            )

            message.text = MainMenu.UNSILENT_MODE
            asyncio.run(command_menu(message, state, bot))

        saved = Memory("state.json", FullState).data
        self.assertEqual(saved.user_state, UserStateEnum.ACTIVE)
        active_markup = message.answer.await_args.kwargs["reply_markup"]
        self.assertEqual(
            active_markup.keyboard[-1][-1].text,
            MainMenu.SILENT_MODE,
        )

    def test_render_menu_ignores_only_not_modified(self) -> None:
        bot = AsyncMock()
        bot.edit_message_text.side_effect = TelegramBadRequest(
            method=AsyncMock(), message="Bad Request: message is not modified"
        )
        asyncio.run(
            render_menu(bot, 10, "text", InlineKeyboardMarkup(inline_keyboard=[]))
        )

    def test_heartbeat_throttles_active_task_alerts(self) -> None:
        state = Memory("state.json", FullState)
        state.data.active_task = "task"
        state.data.user_last_activity_ttamp = 100
        state.data.bot_last_activity_ttamp = 100
        state.save()
        bot = AsyncMock()

        with patch("services.heartbeat.time.time", return_value=4001):
            asyncio.run(tick(bot))
        with patch("services.heartbeat.time.time", return_value=4010):
            asyncio.run(tick(bot))

        self.assertEqual(bot.send_message.await_count, 1)

    def test_heartbeat_sends_each_due_reminder_once(self) -> None:
        plan = Memory("calendar/14_06_2026.json", PlanModel)
        plan.data.reminders.append(
            ReminderModel(datetime="09:00", name="Review", description=None)
        )
        plan.save()
        bot = AsyncMock()

        with patch("services.heartbeat.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = __import__("datetime").datetime(
                2026, 6, 14, 10, 0
            )
            asyncio.run(tick(bot))
            asyncio.run(tick(bot))

        reminder_calls = [
            call for call in bot.send_message.await_args_list
            if call.kwargs.get("text", "").startswith("Reminder:")
        ]
        self.assertEqual(len(reminder_calls), 1)

    def test_config_validation(self) -> None:
        with patch.multiple(
            config,
            BOT_TOKEN="",
            OWNER_ID=1,
            TIME_ZONE="UTC",
            BOT_TICK_INTERVAL_SEC=1,
        ):
            with self.assertRaises(RuntimeError):
                main.validate_config()

        with patch.multiple(
            config,
            BOT_TOKEN="not-a-token",
            OWNER_ID=1,
            TIME_ZONE="UTC",
            BOT_TICK_INTERVAL_SEC=1,
        ):
            with self.assertRaises(RuntimeError):
                main.validate_config()

        with patch.multiple(
            config,
            BOT_TOKEN="123456789:test-token",
            OWNER_ID=1,
            TIME_ZONE="invalid/time-zone",
            BOT_TICK_INTERVAL_SEC=1,
        ):
            with self.assertRaises(RuntimeError):
                main.validate_config()
