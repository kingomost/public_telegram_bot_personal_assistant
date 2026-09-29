from datetime import timedelta

import config
from aiogram import Bot, F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

from interfaces.plan import PlanModel
from interfaces.state import FullState
from enums import AlarmAction, DayAction, ReportAction
from keyboards import (
    ActualSleepTime,
    AlarmActions,
    DayActions,
    ReportActions,
    actual_sleep_time_kb,
    day_actions_kb,
    reports_kb,
)
from memory.memory import Memory
from menu import MainMenu, get_exit_menu
from utils.datetime import date_for_date, local_datetime
from services.plans import PlanStore
from services.goals import GoalAnalytics, GoalsStore
from services.reports import render_goal_report, render_range_report


router = Router(name=__name__)


def _today_plan() -> Memory[PlanModel]:
    return Memory(
        path=f"./calendar/{date_for_date('today')}.json",
        model=PlanModel,
    )


def _progress_text(plan: PlanModel, active_task: str | None) -> str:
    completed = sum(task.completed for task in plan.tasks)
    total = len(plan.tasks)
    percent = round(completed / total * 100) if total else 0
    active = next(
        (task.name for task in plan.tasks if task.uuid == active_task),
        "none",
    )
    wakeup = plan.meta.real_wakeup_time
    sleep = plan.meta.real_sleep_time
    today = local_datetime().date()
    goal_store = GoalsStore()
    today_goal_stats, unassigned = GoalAnalytics(goal_store).calculate(today, today)
    all_goal_stats = GoalAnalytics(goal_store).calculate()[0]
    goal_lines = []
    for goal in goal_store.list():
        today_hours = today_goal_stats[goal.uuid].hours
        goal_total = all_goal_stats[goal.uuid]
        goal_lines.append(
            f"• {goal.name}: {today_hours:.1f}h today, {goal_total.hours:.1f}h total"
        )
        if goal.time_budget and goal.duration_days:
            goal_lines.append(f"  {GoalAnalytics.pace(goal, goal_total)}")
    if unassigned.hours:
        goal_lines.append(f"• Unassigned goal work: {unassigned.hours:.1f}h today")
    goals = "\n".join(goal_lines) if goal_lines else "No goal work tracked today."
    return (
        f"Today's progress: {completed}/{total} tasks ({percent}%).\n"
        f"Active task: {active}\n"
        f"Habits planned: {len(plan.habits)}\n"
        f"Real wakeup: {wakeup.time if wakeup else 'not logged'}\n"
        f"Real sleep: {sleep.time if sleep else 'not logged'}\n\n"
        f"Goal pace today:\n{goals}"
    )


@router.message(F.text == MainMenu.PROGRESS, default_state)
async def progress(message: types.Message, state: FSMContext, bot: Bot):
    plan = _today_plan().data
    full_state = Memory(path="./state.json", model=FullState).data
    menu_msg = await message.answer(text="PROGRESS", reply_markup=get_exit_menu())
    await menu_msg.reply(
        _progress_text(plan, full_state.active_task),
        reply_markup=day_actions_kb(),
        parse_mode=None,
    )


@router.callback_query(DayActions.filter())
async def log_day_action(
    callback_query: types.CallbackQuery,
    callback_data: DayActions,
    bot: Bot,
):
    plan = PlanStore()
    if callback_data.action == DayAction.WAKEUP:
        value = plan.set_real_wakeup()
        result = f"Wakeup logged at {value.time}."
    else:
        value = plan.set_real_sleep()
        result = f"Sleep logged at {value.time}."
    full_state = Memory("state.json", FullState).data
    if callback_query.message:
        await bot.edit_message_text(
            chat_id=config.OWNER_ID,
            message_id=callback_query.message.message_id,
            text=f"{_progress_text(plan.data, full_state.active_task)}\n\n{result}",
            reply_markup=day_actions_kb(),
        )
    await callback_query.answer(result)


@router.callback_query(AlarmActions.filter())
async def confirm_alarm(
    callback_query: types.CallbackQuery,
    callback_data: AlarmActions,
    bot: Bot,
):
    if callback_data.action != AlarmAction.WOKE_UP:
        await callback_query.answer()
        return
    wakeup = PlanStore().set_real_wakeup()
    if callback_query.message:
        await bot.edit_message_text(
            chat_id=config.OWNER_ID,
            message_id=callback_query.message.message_id,
            text=(
                f"Wakeup logged at {wakeup.time}.\n"
                "What time did you fall asleep last night?"
            ),
            reply_markup=actual_sleep_time_kb(),
            parse_mode=None,
        )
    await callback_query.answer("Wakeup confirmed")


@router.callback_query(ActualSleepTime.filter())
async def record_actual_sleep_time(
    callback_query: types.CallbackQuery,
    callback_data: ActualSleepTime,
    bot: Bot,
):
    if callback_data.offset is not None:
        if callback_query.message:
            await bot.edit_message_reply_markup(
                chat_id=config.OWNER_ID,
                message_id=callback_query.message.message_id,
                reply_markup=actual_sleep_time_kb(callback_data.offset),
            )
        await callback_query.answer()
        return
    if callback_data.value is None:
        await callback_query.answer("Choose a sleep time", show_alert=True)
        return
    plan = PlanStore()
    sleep = plan.set_previous_sleep_time(callback_data.value)
    wakeup = plan.data.meta.real_wakeup_time
    if callback_query.message:
        await bot.edit_message_text(
            chat_id=config.OWNER_ID,
            message_id=callback_query.message.message_id,
            text=(
                f"Sleep logged at {sleep.time}.\n"
                f"Wakeup logged at {wakeup.time if wakeup else 'unknown'}."
            ),
            reply_markup=None,
            parse_mode=None,
        )
    await callback_query.answer("Sleep time saved")


@router.message(F.text == MainMenu.REPORT, default_state)
async def report(message: types.Message, state: FSMContext, bot: Bot):
    menu_msg = await message.answer(text="REPORTS", reply_markup=get_exit_menu())
    await menu_msg.reply(
        "Choose a report:", reply_markup=reports_kb(), parse_mode=None
    )


@router.callback_query(ReportActions.filter())
async def report_actions(
    callback_query: types.CallbackQuery,
    callback_data: ReportActions,
    bot: Bot,
):
    today = local_datetime().date()
    if callback_data.action == ReportAction.TODAY:
        text = render_range_report("Today's Report", today, today)
    elif callback_data.action == ReportAction.YESTERDAY:
        day = today - timedelta(days=1)
        text = render_range_report("Yesterday's Report", day, day)
    elif callback_data.action == ReportAction.LAST_7_DAYS:
        text = render_range_report(
            "Last 7 Days", today - timedelta(days=6), today
        )
    elif callback_data.action == ReportAction.THIS_WEEK:
        text = render_range_report(
            "This Week", today - timedelta(days=today.weekday()), today
        )
    else:
        text = render_goal_report()
    if callback_query.message:
        await bot.edit_message_text(
            chat_id=config.OWNER_ID,
            message_id=callback_query.message.message_id,
            text=text,
            reply_markup=reports_kb(),
        )
    await callback_query.answer()
