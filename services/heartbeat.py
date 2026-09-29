import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import config
from aiogram import Bot

from interfaces.plan import PlanModel, TaskModel
from interfaces.state import FullState, UserStateEnum
from keyboards import active_task_kb, alarm_kb, execution_select_task_kb
from memory.memory import Memory


ACTIVE_CHECKIN_SECONDS = 60 * 60
IDLE_PROMPT_SECONDS = 90 * 60
COACHING_COOLDOWN_SECONDS = 60 * 60
ALARM_COOLDOWN_SECONDS = 3 * 60


def _duration_seconds(value: str | None) -> int | None:
    if value is None:
        return None
    durations = {
        "30 min.": 30 * 60,
        "45 min.": 45 * 60,
        "1 hour": 60 * 60,
        "2 hours": 2 * 60 * 60,
        "3 hours": 3 * 60 * 60,
    }
    return durations.get(value)


def _heartbeat_state(full_state: FullState, plan_file: str) -> dict[str, Any]:
    heartbeat = dict(full_state.tmp.get("heartbeat", {}))
    if heartbeat.get("plan_file") != plan_file:
        heartbeat = {"plan_file": plan_file, "sent": {}}
    heartbeat["sent"] = dict(heartbeat.get("sent", {}))
    return heartbeat


def _was_sent(
    heartbeat: dict[str, Any],
    key: str,
    now: int,
    cooldown: int | None = None,
) -> bool:
    sent_at = heartbeat["sent"].get(key)
    if sent_at is None:
        return False
    return cooldown is None or now - int(sent_at) < cooldown


def _record_intervention(
    state: Memory[FullState],
    heartbeat: dict[str, Any],
    key: str,
    now: int,
) -> None:
    heartbeat["sent"][key] = now
    state.data.tmp["heartbeat"] = heartbeat
    state.data.bot_last_activity_ttamp = now
    state.save()


def _next_task(plan: PlanModel, current_time: str) -> TaskModel | None:
    unfinished = [task for task in plan.tasks if not task.completed]
    due = [
        task
        for task in unfinished
        if task.recommended_start_time
        and task.recommended_start_time <= current_time
    ]
    return due[0] if due else (unfinished[0] if unfinished else None)


async def tick(bot: Bot) -> None:
    state = Memory(path="./state.json", model=FullState)
    local_now = datetime.now(ZoneInfo(config.TIME_ZONE))
    now = int(time.time())
    plan_file = local_now.strftime("%d_%m_%Y.json")
    plan = Memory(path=f"./calendar/{plan_file}", model=PlanModel).data
    heartbeat = _heartbeat_state(state.data, plan_file)
    current_time = local_now.strftime("%H:%M")

    # The alarm is an explicit request and remains active in silent mode.
    if (
        plan.wakeup_time
        and current_time >= plan.wakeup_time
        and plan.meta.real_wakeup_time is None
        and not _was_sent(
            heartbeat, "wakeup_alarm", now, ALARM_COOLDOWN_SECONDS
        )
    ):
        await bot.send_message(
            chat_id=config.OWNER_ID,
            text=f"Alarm: planned wakeup time was {plan.wakeup_time}.",
            reply_markup=alarm_kb(),
            parse_mode=None,
        )
        _record_intervention(state, heartbeat, "wakeup_alarm", now)
        return

    # Explicit reminders are delivered once and outrank coaching messages.
    for reminder in plan.reminders:
        key = f"reminder:{reminder.datetime}|{reminder.name}"
        if reminder.datetime <= current_time and not _was_sent(
            heartbeat, key, now
        ):
            description = f"\n{reminder.description}" if reminder.description else ""
            await bot.send_message(
                chat_id=config.OWNER_ID,
                text=f"Reminder: {reminder.name}{description}",
                parse_mode=None,
            )
            _record_intervention(state, heartbeat, key, now)
            return

    if state.data.user_state == UserStateEnum.NOT_ACTIVE:
        return

    last_user_activity = state.data.user_last_activity_ttamp or now
    active_uuid = state.data.active_task

    if active_uuid:
        task = next((item for item in plan.tasks if item.uuid == active_uuid), None)
        execution = dict(state.data.tmp.get("execution", {}))
        elapsed = int(execution.get("elapsed_seconds", 0))
        resumed_at = execution.get("resumed_at")
        if resumed_at and not execution.get("paused"):
            elapsed += max(0, now - int(resumed_at))
        expected = _duration_seconds(task.expected_duration if task else None)
        expected = (
            expected + int(execution.get("extra_seconds", 0))
            if expected
            else None
        )
        overrun_key = f"task_overrun:{active_uuid}"
        if (
            expected is not None
            and elapsed >= expected
            and not _was_sent(
                heartbeat,
                overrun_key,
                now,
                COACHING_COOLDOWN_SECONDS,
            )
        ):
            await bot.send_message(
                chat_id=config.OWNER_ID,
                text=(
                    f"Planned time for {task.name if task else 'the active task'} "
                    "has elapsed. Finish it, pause it, or add five minutes."
                ),
                reply_markup=active_task_kb(),
                parse_mode=None,
            )
            _record_intervention(state, heartbeat, overrun_key, now)
            return

        checkin_key = f"active_checkin:{active_uuid}"
        if (
            now - last_user_activity >= ACTIVE_CHECKIN_SECONDS
            and not _was_sent(
                heartbeat,
                checkin_key,
                now,
                COACHING_COOLDOWN_SECONDS,
            )
        ):
            await bot.send_message(
                chat_id=config.OWNER_ID,
                text=(
                    f"{task.name if task else 'Your task'} is still active. "
                    "Update it only if your situation changed."
                ),
                reply_markup=active_task_kb(),
                parse_mode=None,
            )
            _record_intervention(state, heartbeat, checkin_key, now)
        return

    unfinished = [task for task in plan.tasks if not task.completed]
    if local_now.hour >= 20 and unfinished:
        if not _was_sent(heartbeat, "evening_review", now):
            names = ", ".join(task.name for task in unfinished[:3])
            extra = len(unfinished) - 3
            suffix = f" and {extra} more" if extra > 0 else ""
            await bot.send_message(
                chat_id=config.OWNER_ID,
                text=(
                    f"Evening review: {len(unfinished)} unfinished task(s): "
                    f"{names}{suffix}. Decide what to finish or move."
                ),
                parse_mode=None,
            )
            _record_intervention(state, heartbeat, "evening_review", now)
        return

    if not plan.tasks and 7 <= local_now.hour < 12:
        if not _was_sent(heartbeat, "missing_plan", now):
            await bot.send_message(
                chat_id=config.OWNER_ID,
                text="No tasks are planned for today. Open Planning to define the day.",
                parse_mode=None,
            )
            _record_intervention(state, heartbeat, "missing_plan", now)
        return

    next_task = _next_task(plan, current_time)
    if (
        next_task
        and 8 <= local_now.hour < 20
        and now - last_user_activity >= IDLE_PROMPT_SECONDS
    ):
        key = f"next_task:{next_task.uuid}"
        if not _was_sent(
            heartbeat, key, now, COACHING_COOLDOWN_SECONDS
        ):
            await bot.send_message(
                chat_id=config.OWNER_ID,
                text=f"Next useful action: start {next_task.name}.",
                reply_markup=execution_select_task_kb([
                    {"uuid": next_task.uuid, "name": f"Start {next_task.name}"}
                ]),
                parse_mode=None,
            )
            _record_intervention(state, heartbeat, key, now)
